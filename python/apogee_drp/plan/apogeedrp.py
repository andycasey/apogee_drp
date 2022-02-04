import copy
import numpy as np
import os
import shutil
from glob import glob
import pdb

from dlnpyutils import utils as dln
from ..utils import spectra,yanny,apload,platedata,plan,email,info
from ..apred import mkcal, cal
from ..database import apogeedb
from . import mkplan,runapogee,check
from sdss_access.path import path
from astropy.io import fits
from astropy.table import Table
from collections import OrderedDict
#from astropy.time import Time
from datetime import datetime
import logging
from slurm import queue as pbsqueue
import time


def loadmjd(mjd):
    """ Parse and expand input MJD range/list."""
    if mjd is not None:
        mjds = dln.loadinput(mjd)
        # Expand ranges
        newmjds = []
        for m in mjds:
            if str(m).find('-')>-1:
                parts = str(m).split('-')
                part1 = parts[0]
                part2 = parts[1]
                multimjd = list(np.arange(int(part1),int(part2)+1))
                newmjds += multimjd
            else:
                newmjds.append(m)
        newmjds = list(np.unique(newmjds))
        mjds = newmjds
    else:
        mjds = np.arange(59146,runapogee.lastnightmjd()+1)
    return mjds

def loadsteps(steps):
    """ Parse and expand input steps into a list."""
    # Reduction steps
    # The default is to do all
    allsteps = ['setup','master','3d','check','cals','plans','apred','rv','summary','unified','qa']
    if steps is None:
        steps = allsteps
    else:
        steps = dln.loadinput(steps)
        steps = [str(s).lower() for s in steps]  # lower case
        # expand ranges, i.e. 3d-cals
        newsteps = []
        for s in steps:
            if s.find('-') > -1:
                parts = s.split('-')
                step1 = parts[0]
                ind1, = np.where(np.array(allsteps)==step1)
                if len(ind1)==0:
                    raise ValueError('Step '+step1+' not found in steps: '+','.join(allsteps))
                step2 = parts[1]
                ind2, = np.where(np.array(allsteps)==step2)
                if len(ind2)==0:
                    raise ValueError('Step '+step2+' not found in steps: '+','.join(allsteps))                
                multisteps = list(np.array(allsteps)[ind1[0]:ind2[0]+1])
                newsteps += multisteps
            else:
                newsteps.append(s)
        newsteps = list(np.unique(newsteps))
        steps = newsteps
    return steps

def getexpinfo(load,mjds,logger=None,verbose=True):
    """
    Get all exposure for the MJDs.


    Parameters
    ----------
    load : ApLoad object
       ApLoad object that contains "apred" and "telescope".
    mjds : list
       List of MJDs to process
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.
    verbose : boolean, optional
       Print output to the screen.  Default is True.

    Returns
    -------
    expinfo : numpy structured array
       Exposure information from the raw data headers for the given MJDs.

    Example
    -------

    expinfo = getexpinfo(load,mjds)

    """

    apred = load.apred
    telescope = load.telescope
    observatory = telescope[0:3]

    if logger is None:
        logger = dln.basiclogger()

    nmjds = len(mjds)

    # Maybe get this from the data itself and not the database!!!



    # Get information for all of the exposures
    expinfo = None
    for m in mjds:
        expinfo1 = info.expinfo(observatory=observatory,mjd5=mjd5)
        if expinfo is None:
            expinfo = expinfo1
        else:
            if len(expinfo1)>0:
                expinfo = np.hstack((expinfo,expinfo1))
    nexp = len(expinfo)
    logger.info(str(nexp)+' exposures')


def getplanfiles(load,mjds):
    """
    Get all of the plan files for a list of MJDs.

    Parameters
    ----------
    load : ApLoad object
       ApLoad object that contains "apred" and "telescope".
    mjds : list
       List of MJDs to check for plan files.
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.

    Returns
    -------
    planfiles : list
       The list of plan files.

    Example
    -------

    planfiles = getplanfiles(load,mjds)

    """

    if logger is None:
        logger = dln.basiclogger()
    
    mjdstart = np.min(mjds)
    mjdstop = np.max(mjds)
    
    # Get plan files from the database
    db = apogeedb.DBSession()
    plans = db.query('plan',where="mjd>='%s' and mjd<='%s'" % (mjdstart,mjdstop))
    db.close()
    # No plan files for these MJDs
    if len(ind)==0:
        logger.info('No plan files to process')
        return []
    # Only get plans for the MJDs that we have
    ind = []
    for m in mjds:
        ind1, = np.where(plans['mjd']==m)
        if len(ind1)>0:
            ind += list(ind1)
    ind = np.array(ind)
    # No plan files for these MJDs
    if len(ind)==0:
        logger.info('No plan files to process')
        return []
    plans = plans[ind]
    planfiles = plans['planfile']
    return planfiles


def mkvers(apred,fresh=False,logger=None):
    """
    Setup APOGEE DRP directory structure.
   
    Parameters
    ----------
    apred : str
       Reduction version name.
    fresh : boolean, optional
       Start the reduction directory fresh.  The default is continue with what is
         already there.
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.
    
    Returns
    -------
    It makes the directory structure for a new DRP reduction version.

    Example
    -------

    mkvers('v1.0.0')

    """

    if logger is None:
        logger = dln.basiclogger()
    
    apogee_redux = os.environ['APOGEE_REDUX']+'/'
    apogee_drp_dir = os.environ['APOGEE_DRP_DIR']+'/'

    logger.info('Setting up directory structure for APOGEE DRP version = ',vers)

    # Start fresh
    if args.fresh:
        logger.info('Starting fresh')
        if os.path.exists(apogee_redux+vers):
            shutil.rmtree(apogee_redux+vers)

    # Main directory
    if os.path.exists(apogee_redux+vers)==False:
        logger.info('Creating ',apogee_redux+vers)
        os.makedirs(apogee_redux+vers)
    else:
        logger.info(apogee_redux+vers,' already exists')
    # First level
    for d in ['cal','exposures','stars','fields','visit','qa','plates','monitor','summary','log']:
        if os.path.exists(apogee_redux+vers+'/'+d)==False:
            logger.info('Creating ',apogee_redux+vers+'/'+d)
            os.makedirs(apogee_redux+vers+'/'+d)
        else:
            logger.info(apogee_redux+vers+'/'+d,' already exists')
    # North/south subdirectories
    for d in ['cal','exposures','monitor']:
        for obs in ['apogee-n','apogee-s']:
            if os.path.exists(apogee_redux+vers+'/'+d+'/'+obs)==False:
                logger.info('Creating ',apogee_redux+vers+'/'+d+'/'+obs)
                os.makedirs(apogee_redux+vers+'/'+d+'/'+obs)
            else:
                logger.info(apogee_redux+vers+'/'+d+'/'+obs,' already exists')
    for d in ['visit','stars','fields']:
        for obs in ['apo25m','lco25m']:
            if os.path.exists(apogee_redux+vers+'/'+d+'/'+obs)==False:
                logger.info('Creating ',apogee_redux+vers+'/'+d+'/'+obs)
                os.makedirs(apogee_redux+vers+'/'+d+'/'+obs)
            else:
                logger.info(apogee_redux+vers+'/'+d+'/'+obs,' already exists')
    for d in ['log']:
        for obs in ['apo','lco']:
            if os.path.exists(apogee_redux+vers+'/'+d+'/'+obs)==False:
                logger.info('Creating ',apogee_redux+vers+'/'+d+'/'+obs)
                os.makedirs(apogee_redux+vers+'/'+d+'/'+obs)
            else:
                logger.info(apogee_redux+vers+'/'+d+'/'+obs,' already exists')
    # Cal subdirectories
    for d in ['bpm','darkcorr','detector','flatcorr','flux','fpi','html','littrow','lsf','persist','plans','psf','qa','telluric','trace','wave']:
        for obs in ['apogee-n','apogee-s']:
            if os.path.exists(apogee_redux+vers+'/cal/'+obs+'/'+d)==False:
                logger.info('Creating ',apogee_redux+vers+'/cal/'+obs+'/'+d)
                os.makedirs(apogee_redux+vers+'/cal/'+obs+'/'+d)
            else:
                logger.info(apogee_redux+vers+'/cal/'+obs+'/'+d,' already exists')

    # Webpage files
    #if os.path.exists(apogee_drp_dir+'etc/htaccess'):
    #    os.copy(apogee_drp_dir+'etc/htaccess',apogee_redux+vers+'qa/.htaccess'
    if os.path.exists(apogee_drp_dir+'etc/sorttable.js') and os.path.exists(apogee_redux+vers+'/qa/sorttable.js')==False:
        logger.info('Copying sorttable.js')
        shutil.copyfile(apogee_drp_dir+'etc/sorttable.js',apogee_redux+vers+'/qa/sorttable.js')


def mkmastercals(load,mjds,slurm,clobber=False,links=None,logger=None):
    """
    Make the master calibration products for a reduction version and MJD range.

    Parameters
    ----------
    load : ApLoad object
       ApLoad object that contains "apred" and "telescope".
    mjds : list
       List of MJDs to process
    slurm : dictionary
       Dictionary of slurm settings.
    clobber : boolean, optional
       Overwrite any existing files.  Default is False.
    links : str, optional
       Name of reduction version to use for symlinks for the calibration files.    
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.

    Returns
    -------
    All the master calibration products are made for a reduction version.

    Example
    -------

    mkmastercals('v1.0.0','telescope')

    """

    if logger is None:
        logger = dln.basiclogger()

    apred = load.apred
    telescope = load.telescope
    observatory = telescope[0:3]
    logtime = datetime.now().strftime("%Y%m%d%H%M%S") 

    apogee_redux = os.environ['APOGEE_REDUX']+'/'
    apogee_drp_dir = os.environ['APOGEE_DRP_DIR']+'/'
    

    # Symbolic links to another version
    if links is not None:
        linkvers = links
        logger.info('Creating calibration product symlinks to version >>'+linkvers+'<<')
        cwd = os.path.abspath(os.curdir)
        for d in ['bpm','darkcorr','detector','flatcorr','fpi','littrow','lsf','persist','telluric','wave']:
            for obs in ['apogee-n','apogee-s']:    
                logger.info('Creating symlinks for '+apogee_redux+vers+'/cal/'+obs+'/'+d)
                os.chdir(apogee_redux+vers+'/cal/'+obs+'/'+d)
                subprocess.run(['ln -s '+apogee_redux+linkvers+'/cal/'+obs+'/'+d+'/*fits .'],shell=True)
        return


    # Read in the master calibration index
    caldir = os.environ['APOGEE_DRP_DIR']+'/data/cal/'
    calfile = caldir+load.instrument+'.par'
    allcaldict = mkcal.readcal(calfile)

    # Make calibration frames: darks, waves, LSFs
    
    #set host = `hostname -s`
    #if ( $?UUFSCELL ) then
    #   setenv APOGEE_LOCALDIR /scratch/local/$USER/$SLURM_JOB_ID 
    #else
    #   rm $APOGEE_LOCALDIR/*
    #endif


    # -- Master calibration products made every year or so --
    # Detector
    # Dark, sequence of long darks
    # Flat, sequence of internal flats
    # BPM, use dark+flat sequence
    # Sparse, sequence of sparse quartz flats
    # multiwave, set of arclamp exposures
    # LSF, sky flat + multiwave
    # fiber?
    # -- Other master calibration products made only once ---
    # Littrow
    # Persist, PersistModel
    # telluric, need LSF

    # -- Daily calibration products ---
    # PSF/EPSF/Trace, from domeflat or quartzflat
    # Flux, from domeflat or quartzflat
    # Wave, from arclamps

    # Maybe have an option to copy/symlink them from a previous apred version
    

    # Make darks sequentially
    #-------------------------
    # they take too much memory to run in parallel
    #idl -e "makecal,dark=1,vers='$vers',telescope='$telescope'" >& log/mkdark-$telescope.$host.log
    #darkplot --apred $vers --telescope $telescope
    darkdict = allcaldict['dark']
    logger.info('')
    logger.info('--------------------------------')
    logger.info('Making master darks sequentially')
    logger.info('================================')
    logger.info(str(len(darkdict))+' Darks to make: '+','.join(darkdict['name']))
    logger.info('')
    queue = pbsqueue(verbose=True)
    queue.create(label='mkdark', **slurm)
    for i in range(len(darkdict)):
        outfile1 = os.environ['APOGEE_REDUX']+'/'+apred+'/log/mkdark-'+str(darkdict['name'][i])+telescope+'.'+logtime+'.log'
        errfile1 = mkvoutfile.replace('.log','.err')
        if os.path.exists(os.path.dirname(outfile1))==False:
            os.makedirs(os.path.dirname(outfile1))
        cmd = 'makecal --vers {0} --telescope {1}'.format(apred,telescope)
        cmd += ' --dark '+str(darkdict['name'][i])+' --unlock'
        queue.append(cmd,outfile=outfile1, errfile=errfile1)
    queue.commit(hard=True,submit=True)
    queue_wait(queue,sleeptime=120,verbose=True,logger=logger)  # wait for jobs to complete
    del queue    
    # Make the dark plots
    cal.darkplot(apred=apred,telescope=telescope)

    # Make flats sequentially
    #-------------------------
    #idl -e "makecal,flat=1,vers='$vers',telescope='$telescope'" >& log/mkflat-$telescope.$host.log
    #flatplot --apred $vers --telescope $telescope
    flatdict = allcaldict['flat']
    logger.info('')
    logger.info('--------------------------------')
    logger.info('Making master flats sequentially')
    logger.info('================================')
    logger.info(str(len(flatdict))+' Flats to make: '+','.join(flatdict['name']))
    logger.info('')
    queue = pbsqueue(verbose=True)
    slurm1 = slurm.copy()
    slurm1['nodes'] = 1
    slurm1['cpus'] = 1    
    queue.create(label='mkflat', **slurm1)
    for i in range(len(flatdict)):
        outfile1 = os.environ['APOGEE_REDUX']+'/'+apred+'/log/mkflat-'+str(flatdict['name'][i])+telescope+'.'+logtime+'.log'
        errfile1 = mkvoutfile.replace('.log','.err')
        if os.path.exists(os.path.dirname(outfile1))==False:
            os.makedirs(os.path.dirname(outfile1))
        cmd = 'makecal --vers {0} --telescope {1}'.format(apred,telescope)
        cmd += ' --flat '+str(flatdict['name'][i])+' --unlock'
        queue.append(cmd,outfile=outfile1, errfile=errfile1)
    queue.commit(hard=True,submit=True)
    queue_wait(queue,sleeptime=120,verbose=True,logger=logger)  # wait for jobs to complete
    del queue    
    # Make the flat plots
    cal.flatplot(apred=apred,telescope=telescope)

    # Make BPM sequentially
    #----------------------
    #idl -e "makecal,bpm=1,vers='$vers',telescope='$telescope'" >& log/mkbpm-$telescope.$host.log
    bpmdict = allcaldict['bpm']
    logger.info('')
    logger.info('--------------------------------')
    logger.info('Making master BPMs sequentially')
    logger.info('================================')
    logger.info(str(len(bpmdict))+' BPMs to make: '+','.join(bpmdict['name']))
    logger.info('')
    queue = pbsqueue(verbose=True)
    queue.create(label='mkbpm', **slurm1)
    for i in range(len(bpmdict)):
        outfile1 = os.environ['APOGEE_REDUX']+'/'+apred+'/log/mkbpm-'+str(bpmdict['name'][i])+telescope+'.'+logtime+'.log'
        errfile1 = mkvoutfile.replace('.log','.err')
        if os.path.exists(os.path.dirname(outfile1))==False:
            os.makedirs(os.path.dirname(outfile1))
        cmd = 'makecal --vers {0} --telescope {1}'.format(apred,telescope)
        cmd += ' --bpm '+str(bpmdict['name'][i])+' --unlock'
        queue.append(cmd,outfile=outfile1, errfile=errfile1)
    queue.commit(hard=True,submit=True)
    queue_wait(queue,sleeptime=120,verbose=True,logger=logger)  # wait for jobs to complete
    del queue    

    # Make Littrow sequentially
    #--------------------------
    #idl -e "makecal,littrow=1,vers='$vers',telescope='$telescope'" >& log/mklittrow-$telescope.$host.log
    littdict = allcaldict['littrow']
    logger.info('')
    logger.info('-----------------------------------')
    logger.info('Making master Littrows sequentially')
    logger.info('===================================')
    logger.info(str(len(littdict))+' Littrows to make: '+','.join(littdict['name']))
    logger.info('')
    queue = pbsqueue(verbose=True)
    queue.create(label='mklittrow', **slurm1)
    for i in range(len(littdict)):
        outfile1 = os.environ['APOGEE_REDUX']+'/'+apred+'/log/mklittrow-'+str(littdict['name'][i])+telescope+'.'+logtime+'.log'
        errfile1 = mkvoutfile.replace('.log','.err')
        if os.path.exists(os.path.dirname(outfile1))==False:
            os.makedirs(os.path.dirname(outfile1))
        cmd = 'makecal --vers {0} --telescope {1}'.format(apred,telescope)
        cmd += ' --littrow '+str(littdict['name'][i])+' --unlock'
        queue.append(cmd,outfile=outfile1, errfile=errfile1)
    queue.commit(hard=True,submit=True)
    queue_wait(queue,sleeptime=120,verbose=True,logger=logger)  # wait for jobs to complete
    del queue    

    # Make Response sequentially
    #--------------------------
    responsedict = allcaldict['response']
    logger.info('')
    logger.info('------------------------------------')
    logger.info('Making master responses sequentially')
    logger.info('====================================')
    logger.info(str(len(responsedict))+' Responses to make: '+','.join(responsedict['name']))
    logger.info('')
    queue = pbsqueue(verbose=True)
    queue.create(label='mkresponse', **slurm1)
    for i in range(len(responsedict)):
        outfile1 = os.environ['APOGEE_REDUX']+'/'+apred+'/log/mkresponse-'+str(responsedict['name'][i])+telescope+'.'+logtime+'.log'
        errfile1 = mkvoutfile.replace('.log','.err')
        if os.path.exists(os.path.dirname(outfile1))==False:
            os.makedirs(os.path.dirname(outfile1))
        cmd = 'makecal --vers {0} --telescope {1}'.format(apred,telescope)
        cmd += ' --response '+str(responsedict['name'][i])+' --unlock'
        queue.append(cmd,outfile=outfile1, errfile=errfile1)
    queue.commit(hard=True,submit=True)
    queue_wait(queue,sleeptime=120,verbose=True,logger=logger)  # wait for jobs to complete
    del queue    


    # Make multiwave cals in parallel
    #--------------------------------
    #set n = 0
    #while ( $n < 5 ) 
    #   idl -e "makecal,multiwave=1,vers='$vers',telescope='$telescope'" >& log/mkwave-$telescope"$n".$host.log &
    #   sleep 20
    #   @ n = $n + 1
    #end
    #wait

    multiwavedict = allcaldict['multiwave']
    logger.info('')
    logger.info('-----------------------------------')
    logger.info('Making master multiwave in parallel')
    logger.info('===================================')
    logger.info(str(len(multiwavedict))+' multiwave to make: '+','.join(multiwavedict['name']))
    logger.info('')
    slurm1['nodes'] = 1
    slurm1['cpus'] = 5
    queue = pbsqueue(verbose=True)
    queue.create(label='mkmultiwave', **slurm1)
    for i in range(len(multiwavedict)):
        outfile1 = os.environ['APOGEE_REDUX']+'/'+apred+'/log/mkmultiwave-'+str(multiwavedict['name'][i])+telescope+'.'+logtime+'.log'
        errfile1 = mkvoutfile.replace('.log','.err')
        if os.path.exists(os.path.dirname(outfile1))==False:
            os.makedirs(os.path.dirname(outfile1))
        cmd = 'makecal --vers {0} --telescope {1}'.format(apred,telescope)
        cmd += ' --multiwave '+str(multiwavedict['name'][i])+' --unlock'
        queue.append(cmd,outfile=outfile1, errfile=errfile1)
    queue.commit(hard=True,submit=True)
    queue_wait(queue,sleeptime=120,verbose=True,logger=logger)  # wait for jobs to complete
    del queue    


    # Make LSFs in parallel
    #-----------------------
    #set n = 0
    #while ( $n < 5 ) 
    #   idl -e "makecal,lsf=1,/full,/pl,vers='$vers',telescope='$telescope'" >& log/mklsf-$telescope"$n".$host.log &
    #   sleep 20
    #   @ n = $n + 1
    #end
    #wait

    lsfdict = allcaldict['lst']
    logger.info('')
    logger.info('--------------------------------')
    logger.info('Making master LSFs in parallel')
    logger.info('================================')
    logger.info(str(len(lsfdict))+' LSFs to make: '+','.join(lsfdict['name']))
    logger.info('')
    slurm1['nodes'] = 1
    slurm1['cpus'] = 5
    queue = pbsqueue(verbose=True)
    queue.create(label='mklsf', **slurm1)
    for i in range(len(littdict)):
        outfile1 = os.environ['APOGEE_REDUX']+'/'+apred+'/log/mklsf-'+str(lsfdict['name'][i])+telescope+'.'+logtime+'.log'
        errfile1 = mkvoutfile.replace('.log','.err')
        if os.path.exists(os.path.dirname(outfile1))==False:
            os.makedirs(os.path.dirname(outfile1))
        cmd = 'makecal --vers {0} --telescope {1}'.format(apred,telescope)
        cmd += ' --lsf '+str(lsfdict['name'][i])+' --full --pl --unlock'
        queue.append(cmd,outfile=outfile1, errfile=errfile1)
    queue.commit(hard=True,submit=True)
    queue_wait(queue,sleeptime=120,verbose=True,logger=logger)  # wait for jobs to complete
    del queue    

def run3d(load,mjds,slurm,clobber=False,logger=None):
    """
    Run AP3D on all exposures for a list of MJDs.

    Parameters
    ----------
    load : ApLoad object
       ApLoad object that contains "apred" and "telescope".
    mjds : list
       List of MJDs to process
    slurm : dictionary
       Dictionary of slurm settings.
    clobber : boolean, optional
       Overwrite existing files.  Default is False.
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.

    Returns
    -------
    chk3d : numpy structured array
       Table of summary and QA information about the exposure processing.

    Example
    -------

    run3d(load,mjds)

    """

    if logger is None:
        logger = dln.basiclogger()
    
    apred = load.apred
    telescope = load.telescope
    observatory = telescope[0:3]
    logtime = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Get exposures
    expinfo = getexpinfo(observatory,mjds,logger=logger)

    # Process the files
    if len(expinfo)>0:
        slurm1 = slurm.copy()
        slurm1['cpus'] = np.minimum(slurm['cpus'],len(expinfo))
        slurm1['numpy_num_threads'] = 2
        queue = pbsqueue(verbose=True)
        queue.create(label='ap3d', **slurm1)
        do3d = np.zeros(len(expinfo),bool)
        for i,num in enumerate(expinfo['num']):
            mjd = int(load.cmjd(num))
            logfile1 = load.filename('2D',num=num,mjd=mjd,chips=True).replace('2D','3D')
            logfile1 = os.path.dirname(logfile1)+'/logs/'+os.path.basename(logfile1)
            logfile1 = logfile1.replace('.fits','_pbs.'+logtime+'.log')
            if os.path.dirname(logfile1)==False:
                os.makedirs(os.path.dirname(logfile1))
            # Check if files exist already
            do3d[i] = True
            if clobber is not True:
                outfile = load.filename('2D',num=num,mjd=mjd,chips=True)
                if load.exists('2D',num=num):
                    logger.info(os.path.basename(outfile)+' already exists and clobber==False')
                    do3d[i] = False
            if do3d[i]:
                queue.append('ap3d --num {0} --vers {1} --telescope {2} --unlock'.format(num,apred,telescope),
                             outfile=logfile1,errfile=logfile1.replace('.log','.err'))
        if np.sum(do3d)>0:
            queue.commit(hard=True,submit=True)
                logger.info('PBS key is '+queue.key)
            runapogee.queue_wait(queue,sleeptime=60,verbose=True,logger=rootLogger)  # wait for jobs to complete
            chk3d = runapogee.check_ap3d(expinfo,queue.key,apred,telescope,verbose=True,logger=rootLogger)
        else:
            logger.info('No exposures need AP3D processing')
        del queue
    else:  # no exposures
        logger.info('No exposures to process with AP3D')
        chk3d = None

    return chk3d

def rundailycals(load,mjds,slurm,clobber=False,logger=None):
    """
    Run daily calibration frames for a list of MJDs.

    Parameters
    ----------
    load : ApLoad object
       ApLoad object that contains "apred" and "telescope".
    mjds : list
       List of MJDs to process
    slurm : dictionary
       Dictionary of slurm settings.
    clobber : boolean, optional
       Overwrite existing files.  Default is False.
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.

    Returns
    -------
    chkcal : numpy structured array
       Table of summary and QA information about the calibration exposure processing.

    Example
    -------

    chkcal = rundailycals(load,mjds)

    """

    if logger is None:
        logger = dln.basiclogger()
        
    apred = load.apred
    telescope = load.telescope
    observatory = telescope[0:3]
    logtime = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Get exposures
    expinfo = getexpinfo(observatory,mjds,logger=logger,verbose=False)

    # First we need to run domeflats and quartzflats so there are apPSF files
    # Then the arclamps
    # apFlux files?
    # Then the FPI exposures last (needs apPSF and apWave files)
    calind, = np.where((expinfo['exptype']=='DOMEFLAT') | (expinfo['exptype']=='QUARTZFLAT') | 
                       (expinfo['exptype']=='ARCLAMP') | (expinfo['exptype']=='FPI'))
    if len(calind)>0:
        expinfo = expinfo[calind]
    else:
        logger.info('No calibration files to run')
        return None

    # Run QA check on the files
    logger.info(' ')
    logger.info('Doing quality checks on all calibration exposures')
    qachk = check.check(expinfo['num'],apred,telescope,verbose=True,logger=logger)
    logger.info(' ')
    okay, = np.where(qachk['okay']==True)
    if len(okay)>0:
        expinfo = expinfo[okay]
    else:
        logger.info('No good calibration files to run')
        return None        

    # 1: psf, 2: flux, 4: arcs, 8: fpi
    calcodedict = {'DOMEFLAT':3, 'QUARTZFLAT':1, 'ARCLAMP':4, 'FPI':8}
    calcode = [calcodedict[etype] for etype in expinfo['exptype']]
    calnames = ['DOMEFLAT/QUARTZFLAT','FLUX','ARCLAMP','FPI']
    shcalnames = ['psf','flux','arcs','fpi']
    filecodes = ['PSF','Flux','Wave','WaveFPI']
    chkcal = []
    for j,ccode in enumerate([1,2,4,8]):
        logger.info('')
        logger.info('----------------------------------------------')
        logger.info('Running Calibration Files: '+str(calnames[j]))
        logger.info('==============================================')
        logger.info('')
        cind, = np.where((np.array(calcode) & ccode) > 0)
        if len(cind)>0:
            logger.info(str(len(cind))+' file(s)')
            slurm1 = slurm.copy()
            slurm1['cpus'] = np.minimum(slurm['cpus'],len(cind))
            slurm1['numpy_num_threads'] = 2
            queue = pbsqueue(verbose=True)
            queue.create(label='makecal-'+shcalnames[j], **slurm1)
            logfiles = []
            docal = np.zeros(len(cind),bool)
            for k in range(len(cind)):
                num1 = expinfo['num'][cind[k]]
                mjd1 = int(load.cmjd(num1))
                calplandir = os.path.dirname(load.filename('CalPlan',num=0,mjd=mjd1))
                exptype1 = expinfo['exptype'][cind[k]]
                arctype1 = expinfo['arctype'][cind[k]]                    
                if ccode==1:   # psfs
                    cmd1 = 'makecal --psf '+str(num1)+' --unlock'
                    if clobber: cmd1 += ' --clobber'
                    logfile1 = calplandir+'/apPSF-'+str(num1)+'_pbs.'+logtime+'.log'
                elif ccode==2:   # flux
                    cmd1 = 'makecal --psf '+str(num1)+' --flux '+str(num1)+' --unlock'
                    if clobber: cmd1 += ' --clobber'
                    logfile1 = calplandir+'/apFlux-'+str(num1)+'_pbs.'+logtime+'.log'
                elif ccode==4:  # and exptype1=='ARCLAMP' and (arctype1=='UNE' or arctype1=='THARNE'):  # arcs                       
                    cmd1 = 'makecal --wave '+str(num1)+' --unlock'
                    if clobber: cmd1 += ' --clobber'
                    logfile1 = calplandir+'/apWave-'+str(num1)+'_pbs.'+logtime+'.log' 
                elif ccode==8:  # and exptype1=='ARCLAMP' and arctype1=='None':    # fpi                       
                    cmd1 = 'makecal --fpi '+str(num1)+' --unlock'
                    if clobber: cmd1 += ' --clobber'
                logfile1 = calplandir+'/apFPI-'+str(num1)+'_pbs.'+logtime+'.log'
                logger.info(logfile1)
                # Check if files exist already
                docal[k] = True
                if clobber is not True:
                    outfile = load.filename(filecodes[j],num=num1,mjd=mjd1,chips=True)
                    if load.exists(filecodes[j],num=num1,mjd=mjd1):
                        rootLogger.info(os.path.basename(outfile)+' already exists and clobber==False')
                        docal[k] = False
                if docal[k]:
                    rootLogger.info('Calibration file %d : %s %d' % (k+1,exptype1,num1))
                    rootLogger.info(logfile1)
                    queue.append(cmd1, outfile=logfile1,errfile=logfile1.replace('.log','.err'))
            if np.sum(docal)>0:
                queue.commit(hard=True,submit=True)
                logger.info('PBS key is '+queue.key)
                runapogee.queue_wait(queue,sleeptime=60,verbose=True,logger=logger)  # wait for jobs to complete
            else:
                logger.info('No '+str(calnames[j])+' calibration files need to be run')
            chkcal1 = runapogee.check_calib(expinfo,logfiles,queue.key,apred,verbose=True,logger=logger)
            if len(chkcal)==0:
                chkcal = chkcal1
            else:
                chkcal = np.hstack((chkcal,chkcal1))
            del queue
        else:
            logger.info('No '+str(calnames[j])+' calibration files to run')

    return chkcal

def makeplanfiles(load,mjds,slurm,clobber=False,logger=None):
    """
    Make plan files for a list of MJDs.

    Parameters
    ----------
    load : ApLoad object
       ApLoad object that contains "apred" and "telescope".
    mjds : list
       List of MJDs to process
    slurm : dictionary
       Dictionary of slurm settings.
    clobber : boolean, optional
       Overwrite existing files.  Default is False.
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.

    Returns
    -------
    planfiles : list
       List of plan files that were created.

    Example
    -------

    planfiles = makeplanfiles(load,mjds)

    """

    if logger is None:
        logger = dln.basiclogger()
    
    apred = load.apred
    telescope = load.telescope
    observatory = telescope[0:3]
    mjdstart = np.min(mjds)
    mjdstop = np.max(mjds)
    logtime = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Reduction logs directory
    logdir = os.environ['APOGEE_REDUX']+'/'+apred+'/log/'+observatory+'/'
    if os.path.exists(logdir)==False:
        os.makedirs(logdir)

    # Loop over MJDs
    planfiles = []
    for m in mjds:
        logger.info(' ')
        logger.info('Making plan files for MJD='+str(m))
        plandicts,planfiles = mkplan.make_mjd5_yaml(m,apred,telescope,clobber=clobber,logger=ogger)
        dailyplanfile = os.environ['APOGEEREDUCEPLAN_DIR']+'/yaml/'+telescope+'/'+telescope+'_'+str(m)+'.yaml'
        planfiles1 = mkplan.run_mjd5_yaml(dailyplanfile,logger=logger)
        nplanfiles1 = len(planfiles1)
        if nplanfiles1>0:
            runapogee.dbload_plans(planfiles1)  # load plans into db
            # Write planfiles to MJD5.plans
            dln.writelines(logdir+str(m)+'.plans',[os.path.basename(pf) for pf in planfiles])
            planfiles += planfiles1
        else:
            dln.writelines(logdir+str(m)+'.plans','')   # write blank file

        # Start entry in daily_status table
        #daycat = np.zeros(1,dtype=np.dtype([('mjd',int),('telescope',(np.str,10)),('nplanfiles',int),
        #                                    ('nexposures',int),('begtime',(np.str,50)),('success',bool)]))
        #daycat['mjd'] = m
        #daycat['telescope'] = telescope
        #daycat['nplanfiles'] = len(planfiles1)
        #daycat['nexposures'] = len(expinfo1)
        #daycat['begtime'] = begtime
        #daycat['success'] = False
        #db.ingest('daily_status',daycat)


    return planfiles

def runapred(load,mjds,slurm,clobber=False,logger=None):
    """
    Run APRED on all plan files for a list of MJDs.

    Parameters
    ----------
    load : ApLoad object
       ApLoad object that contains "apred" and "telescope".
    mjds : list
       List of MJDs to process
    slurm : dictionary
       Dictionary of slurm settings.
    clobber : boolean, optional
       Overwrite existing files.  Default is False.
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.

    Returns
    -------
    chkexp : numpy structured array
       Table of summary and QA information about the exposure APRED processing.
    chkvisit : numpy structured array
       Table of summary and QA information about the visit APRED processing.

    Example
    -------

    chkexp,chkvisit = runapred(load,mjds)

    """

    if logger is None:
        logger = dln.basiclogger()
    
    apred = load.apred
    telescope = load.telescope
    observatory = telescope[0:3]
    mjdstart = np.min(mjds)
    mjdstop = np.max(mjds)
    logtime = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Get plan files from the database
    planfiles = getplanfiles(load,mjds,logger=logger)
    # No plan files for these MJDs
    if len(planfiles)==0:
        return
        
    slurm1 = slurm.copy()
    slurm1['cpus'] = np.minimum(slurm['cpus'],len(planfiles))
    slurm1['numpy_num_threads'] = 2
    queue = pbsqueue(verbose=True)
    queue.create(label='apred', **slurm1)
    for pf in planfiles:
        queue.append('apred {0}'.format(pf), outfile=pf.replace('.yaml','_pbs.'+logtime+'.log'),
                     errfile=pf.replace('.yaml','_pbs.'+logtime+'.err'))
    queue.commit(hard=True,submit=True)
    logger.info('PBS key is '+queue.key)
    runapogee.queue_wait(queue,sleeptime=120,verbose=True,logger=logger)  # wait for jobs to complete
    chkexp,chkvisit = runapogee.check_apred(expinfo,planfiles,queue.key,verbose=True,logger=logger)
    del queue

    return chkexp,chkvisit

def runrv(load,mjds,slurm,clobber=False,logger=None):
    """
    Run RV on all the stars observed from a list of MJDs.

    Parameters
    ----------
    load : ApLoad object
       ApLoad object that contains "apred" and "telescope".
    mjds : list
       List of MJDs to process
    slurm : dictionary
       Dictionary of slurm settings.
    clobber : boolean, optional
       Overwrite existing files.  Default is False.
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.

    Returns
    -------
    The unified directory structure software is run on the MJDs and relevant symlinks are generated.

    Example
    -------

    runrv(load,mjds)

    """

    if logger is None:
        logger = dln.basiclogger()
    
    apred = load.apred
    telescope = load.telescope
    observatory = telescope[0:3]
    mjdstart = np.min(mjds)
    mjdstop = np.max(mjds)
    logtime = datetime.now().strftime("%Y%m%d%H%M%S")
    
    vcat = db.query('visit',cols='*',where="apred_vers='%s' and mjd>=%d and mjd<=%d and telescope='%s'" % (apred,mjdstart,mjdstop,telescope))
    if len(vcat)==0:
        logger.info('No visits found for MJDs')
        return None
    # Pick on the MJDs we want
    ind = []
    for m in mjds:
        gd, = np.where(vcat['mjd']==m)
        if len(gd)>0: ind += list(gd)
    ind = np.array(ind)
    if len(ind)==0:
        logger.info('No visits found for MJDs')
        return None    
    vcat = vcat[ind]
    # Get unique stars
    objects,ui = np.unique(vcat['apogee_id'],return_index=True)
    vcat = vcat[ui]
    # remove ones with missing or blank apogee_ids
    bd, = np.where((vcat['apogee_id']=='') | (vcat['apogee_id']=='None') | (vcat['apogee_id']=='2MNone'))
    if len(bd)>0:
        vcat = np.delete(vcat,bd)
    logger.info(str(len(vcat))+' stars to run')

    slurm1 = slurm.copy()
    slurm1['cpus'] = np.minimum(slurm['cpus'],len(vcat))
    slurm1['numpy_num_threads'] = 2
    queue = pbsqueue(verbose=True)
    queue.create(label='rv', **slurm1)
    for obj in vcat['apogee_id']:
        apstarfile = load.filename('Star',obj=obj)
        outdir = os.path.dirname(apstarfile)  # make sure the output directories exist
        if os.path.exists(outdir)==False:
            os.makedirs(outdir)
        # Run with --verbose and --clobber set
        queue.append('rv %s %s %s -c -v' % (obj,apred,telescope),outfile=apstarfile.replace('.fits','-'+'_pbs.'+logtime+'.log'),
                     errfile=apstarfile.replace('.fits','-'+'_pbs.'+logtime+'.err'))
    queue.commit(hard=True,submit=True)
    logger.info('PBS key is '+queue.key)        
    runapogee.queue_wait(queue,sleeptime=120,verbose=True,logger=logger)  # wait for jobs to complete
    import pdb; pdb.set_trace()
    chkrv = runapogee.check_rv(vcat,queue.key)
    del queue

    return chkrv


def rununified(load,mjds,slurm,clobber=False,logger=None):
    """
    Create the unified MWM directory structure for the relevant MJDs.

    Parameters
    ----------
    load : ApLoad object
       ApLoad object that contains "apred" and "telescope".
    mjds : list
       List of MJDs to process
    slurm : dictionary
       Dictionary of slurm settings.
    clobber : boolean, optional
       Overwrite existing files.  Default is False.
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.

    Returns
    -------
    The unified directory structure software is run on the MJDs and relevant symlinks are generated.

    Example
    -------

    rununified(load,mjds)

    """

    if logger is None:
        logger = dln.basiclogger()
    
    apred = load.apred
    telescope = load.telescope
    observatory = telescope[0:3]
    mjdstart = np.min(mjds)
    mjdstop = np.max(mjds)
    logtime = datetime.now().strftime("%Y%m%d%H%M%S")
    
    slurm1 = slurm.copy()
    slurm1['cpus'] = np.minimum(slurm['cpus'],len(mjds))
    slurm1['numpy_num_threads'] = 2    
    queue = pbsqueue(verbose=True)
    queue.create(label='unidir', **slurm1)
    # Loop over all MJDs
    for m in mjds:
        outfile = os.environ['APOGEE_REDUX']+'/'+apred+'/log/'+observatory+'/'+str(mjd5)+'-unidir.'+logtime+'.log'
        errfile = outfile.replace('.log','.err')
        if os.path.exists(os.path.dirname(outfile))==False:
            os.makedirs(os.path.dirname(outfile))
        queue.append('sas_mwm_healpix --spectro apogee --mjd {0} --telescope {1} --drpver {2} -v'.format(mjd5,telescope,apred),
                     outfile=outfile, errfile=errfile)
    queue.commit(hard=True,submit=True)
    rootLogger.info('PBS key is '+queue.key)        
    runapogee.queue_wait(queue,sleeptime=60,verbose=True,logg=rootLogger)  # wait for jobs to complete
    del queue    
    #  sas_mwm_healpix --spectro apogee --mjd 59219 --telescope apo25m --drpver daily -v


def runqa(load,mjds,slurm,clobber=False,logger=None):
    """
    Run QA on a list of MJDs.

    Parameters
    ----------
    load : ApLoad object
       ApLoad object that contains "apred" and "telescope".
    mjds : list
       List of MJDs to process
    clobber : boolean, optional
       Overwrite existing files.  Default is False.
    logger : logger, optional
       Logging object.  If not is input, then a default one will be created.

    Returns
    -------
    The QA code is run on the MJDs and relevant plots and HTML pages are created.

    Example
    -------

    runqa(load,mjds)

    """

    apred = load.apred
    telescope = load.telescope
    observatory = telescope[0:3]
    mjdstart = np.min(mjds)
    mjdstop = np.max(mjds)
    logtime = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Get plan files for these MJDs
    planfiles = getplanfiles(load,mjds,logger=logger)
    
    # Run apqa on each plate visit
    slurm1 = slurm.copy()
    slurm1['cpus'] = np.minimum(slurm['cpus'],len(planfiles))
    slurm1['numpy_num_threads'] = 2    
    queue = pbsqueue(verbose=True)
    queue.create(label='apqa', **slurm1)
    for pf in planfiles:
        fdir = os.path.dirname(pf)
        base = os.path.basename(pf)
        dum = base.split('-')
        plate = dum[1]
        mjd = dum[2]
        logfile = fdir+'/apqa-'+plate+'-'+mjd+'_pbs.'+logtime+'.log'
        errfile = logfile.erplace('.log','.err')
        cmd = 'apqa {0} apo --plate {1} --telescope apo25m --masterqa False'.format(mjd,plate)
        cmd += '--starhtml False --starplots False --nightqa False --monitor False'
        queue.append(cmd, outfile=logfile, errfile=errfile)
    queue.commit(hard=True,submit=True)
    print('PBS key is '+queue.key)
    runapogee.queue_wait(queue,sleeptime=60,verbose=True)  # wait for jobs to complete 
    queue = pbsqueue(verbose=True)

    # Run nightly QA/summary

    queue = pbsqueue(verbose=True)
    queue.create(label='qa', **slurm1)
    for i in enumerate(plates):
        qaoutfile = os.environ['APOGEE_REDUX']+'/'+apred+'/log/'+observatory+'/'+str(mjd5)+'-qa.'+logtime+'.log'
        qaerrfile = qaoutfile.replace('-qa.log','-qa.'+logtime+'.err')
        if os.path.exists(os.path.dirname(qaoutfile))==False:
            os.makedirs(os.path.dirname(qaoutfile))
        queue.append('apqa {0} {1}'.format(mjd5,observatory),outfile=qaoutfile, errfile=qaerrfile)
    queue.commit(hard=True,submit=True)
    runapogee.queue_wait(queue)  # wait for jobs to complete
    del queue
    
    # Run final mjd/fields pate

    # Run monitor page

    

def run(observatory,apred,mjd=None,steps=None,qos='sdss',clobber=False,fresh=False,links=None,
        nodes=1,cpus=32):
    """
    Perform APOGEE Data Release Processing

    Parameters
    ----------
    observatory : str
       The observatory: "apo" or "lco".
    apred : str
       Reduction version name.
    mjd : str, list, optional
       Set of MJDs to run.  This can be (a) a string with a date range (e.g., '59610-59650'), or
         (b) a string with a comma-separated list (e.g. '59610,59610,59650'), (c) a python list of
         MJDs, or (d) a combination of all of the above.
         By default, all SDSS-V MJDs are run.
    qos : str, optional
       The pbs queue to use.  Default is "sdss".
    clobber : boolean, optional
       Overwrite any existing data.  Default is False.
    fresh : boolean, optional
       Start the reduction directory fresh.  The default is continue with what is
         already there.
    links : str, optional
       Name of reduction version to use for symlinks for the calibration files.

    Returns
    -------
    Nothing is returned.  The APOGEE data are reduced on disk.

    Example
    -------

    run('apo','v1.1',mjd=[54566,56666])

    """

    begtime = str(datetime.now())

    telescope = observatory+'25m'
    instrument = {'apo':'apogee-n','lco':'apogee-s'}[observatory]

    # MJDs to process
    mjds = loadmjd(mjd)
    mjds = np.sort(np.array(mjds).astype(int))
    nmjd = len(mjds)
    mjdstart = np.min(mjds)
    mjdstop = np.max(mjds)

    # Reduction steps
    # The default is to do all
    allsteps = ['setup','master','3d','check','cals','plans','apred','rv','summary','unified','qa']
    steps = loadsteps(steps)
    nsteps = len(steps)

    # Slurm settings
    alloc = 'sdss-np'
    shared = True
    ppn = 64
    walltime = '10-00:00:00'
    slurm = {'nodes':nodes, 'alloc':alloc, 'shared':shared, 'ppn':ppn, 'cpus':cpus,
             'walltime':walltime, 'notifications':False}
    
    # Get software version (git hash)
    gitvers = plan.getgitvers()

    load = apload.ApLoad(apred=apred,telescope=telescope)

    # Reduction logs directory
    logdir = os.environ['APOGEE_REDUX']+'/'+apred+'/log/'+observatory+'/'
    if os.path.exists(logdir)==False:
        os.makedirs(logdir)

    # Data directory 
    datadir = {'apo':os.environ['APOGEE_DATA_N'],'lco':os.environ['APOGEE_DATA_S']}[observatory]

    # Set up logging to screen and logfile
    logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
    rootLogger = logging.getLogger() 
    while rootLogger.hasHandlers(): # some existing loggers, remove them   
        rootLogger.removeHandler(rootLogger.handlers[0]) 
    rootLogger = logging.getLogger()
    logfile = logdir+str(mjdstart)+'-'+str(mjdstop)+'.log'
    if os.path.exists(logfile): os.remove(logfile)
    fileHandler = logging.FileHandler(logfile)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)
    rootLogger.setLevel(logging.NOTSET)
    logtime = datetime.now().strftime("%Y%m%d%H%M%S") 

    rootLogger.info('Running APOGEE DRP for '+str(observatory).upper()+' apred='+apred)
    rootLogger.info(str(nmjd)+' MJDs: '+','.join(np.char.array(mjds).astype(str)))
    rootLogger.info(str(nsteps)+' steps: '+','.join(steps))
    rootLogger.info('Clobber is '+str(clobber))


    # 1) Setup the directory structure
    #----------------------------------
    if 'setup' in steps:
        rootLogger.info('')
        rootLogger.info('-------------------------------------')
        rootLogger.info('1) Setting up the directory structure')
        rootLogger.info('=====================================')
        rootLogger.info('')
        queue = pbsqueue(verbose=True)
        queue.create(label='mkvers', nodes=1, alloc=alloc, ppn=ppn, qos=qos, cpus=1, shared=shared, walltime=walltime, notification=False)
        mkvoutfile = os.environ['APOGEE_REDUX']+'/'+apred+'/log/mkvers.'+logtime+'.log'
        mkverrfile = mkvoutfile.replace('-mkvers.log','-mkvers.'+logtime+'.err')
        if os.path.exists(os.path.dirname(mkvoutfile))==False:
            os.makedirs(os.path.dirname(mkvoutfile))
        cmd = 'mkvers {0}'.format(apred)
        if fresh:
            cmd += ' --fresh'
        if links is not None:
            cmd += ' --links '+str(links)
        queue.append(cmd,outfile=mkvoutfile, errfile=mkverrfile)
        queue.commit(hard=True,submit=True)
        runapogee.queue_wait(queue)  # wait for jobs to complete
        del queue    

    # 2) Master calibration products, make sure to do them in the right order
    #------------------------------------------------------------------------
    if 'master' in steps:
        rootLogger.info('')
        rootLogger.info('-----------------------------------------')
        rootLogger.info('2) Generating master calibration products')
        rootLogger.info('=========================================')
        rootLogger.info('')
        chk = mkmastercals(load,slurm=slurm,clobber=clobber,links=links,logger=rootLogger)

    # 3) Process all exposures through ap3d
    #---------------------------------------
    if '3d' in steps:
        rootLogger.info('')
        rootLogger.info('--------------------------------')
        rootLogger.info('3) Running AP3D on all exposures')
        rootLogger.info('================================')
        rootLogger.info('')
        chk3d = run3d(load,mjds,slurm=slurm,clobber=clobber,logger=rootLogger)

    # 4) Perform initial quality check on all exposures
    #--------------------------------------------------
    # Do QA check of the files
    if 'check' in steps:
        rootLogger.info(' ')
        rootLogger.info('Doing quality checks on all exposures')
        qachk = check.check(expinfo['num'],apred,telescope,verbose=True,logger=rootLogger)

    # 5) Make all daily cals (domeflats, quartzflats, arclamps, FPI)
    #----------------------------------------------------------------
    if 'cals' in steps:
        rootLogger.info('')
        rootLogger.info('----------------------------------------')
        rootLogger.info('5) Generating daily calibration products')
        rootLogger.info('========================================')
        rootLogger.info('')
        chkcal = rundailycals(load,mjds,slurm=slurm,clobber=clobber,logger=rootLogger)

    # 6) Make plan files
    #-------------------
    if 'plans' in steps:
        rootLogger.info('')
        rootLogger.info('--------------------')
        rootLogger.info('6) Making plan files')
        rootLogger.info('====================')
        rootLogger.info('')
        planfiles = makeplanfiles(load,mjds,slurm=slurm,logger=rootLogger)

    # 7) Run APRED on all of the plan files (ap3d-ap1dvisit), go through each MJD chronologically
    #--------------------------------------------------------------------------------------------
    if 'apred' in steps:
        rootLogger.info('')
        rootLogger.info('----------------')
        rootLogger.info('7) Running APRED')
        rootLogger.info('================')
        rootLogger.info('')
        chkapred = runapred(load,mjds,slurm=slurm,clobber=clobber,logger=rootLogger)
        
    # 8) Run "rv" on all unique stars
    #--------------------------------
    if 'rv' in steps:
        rootLogger.info('')
        rootLogger.info('--------------------------------')
        rootLogger.info('8) Running RV+Visit Combination')
        rootLogger.info('================================')
        rootLogger.info('')
        chkrv = runrv(load,mjds,slurm=slurm,clobber=clobber,logger=rootLogger)

    # 9) Create full allVisit/allStar files
    if 'summary' in steps:
        rootLogger.info('')
        rootLogger.info('-----------------------')
        rootLogger.info('9) Create summary files')
        rootLogger.info('=======================')
        rootLogger.info('')
        runapogee.create_sumfiles(apred,telescope)
    
    # 10) Unified directory structure
    #---------------------------------
    if 'unified' in steps:
        rootLogger.info('')
        rootLogger.info('---------------------------------------------')
        rootLogger.info('10) Generating unified MWM directory structure')
        rootLogger.info('=============================================')
        rootLogger.info('')
        rununified(load,mjds,slurm=slurm,logger=rootLogger)

    # 11) Run QA script
    #------------------
    if 'qa' in steps:
        rootLogger.info('')
        rootLogger.info('--------------')
        rootLogger.info('11) Running QA')
        rootLogger.info('==============')
        rootLogger.info('')
        runqa(load,mjds,slurm=slurm,logger=rootLogger)


    # Update daily_status table
    #daycat = np.zeros(1,dtype=np.dtype([('pk',int),('mjd',int),('telescope',(np.str,10)),('nplanfiles',int),
    #                                    ('nexposures',int),('begtime',(np.str,50)),('endtime',(np.str,50)),('success',bool)]))
    #daycat['mjd'] = mjd5
    #daycat['telescope'] = telescope
    #daycat['nplanfiles'] = len(planfiles)
    #daycat['nexposures'] = len(expinfo)
    #daycat['begtime'] = begtime
    #daycat['endtime'] = str(datetime.now())
    #daysuccess = True
    #if chkvisit is not None:
    #    daysuccess &= (np.sum(chkvisit['success']==False)==0)
    #if chkrv is not None:
    #    daysuccess &= (np.sum(chkrv['success']==False)==0)
    #daycat['success'] = daysuccess
    #dayout = db.query('daily_status',where="mjd="+str(mjd5)+" and telescope='"+telescope+"' and begtime='"+begtime+"'")
    #daycat['pk'] = dayout['pk'][0]
    #db.update('daily_status',daycat)

    rootLogger.info('Daily APOGEE reduction finished for MJD=%d to MJD=%d and observatory=%s' % (mjdstart,mjdstop,observatory))


    # Summary email
    # send to apogee_reduction email list
    # include basic information
    # give link to QA page
    # attach full run_daily() log (as attachment)
    # don't see it if using --debug mode
    #runapogee.summary_email(observatory,mjdstart,chkexp,chkvisit,chkrv,logfile)
