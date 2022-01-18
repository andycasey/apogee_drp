import copy
import numpy as np
import os
import shutil
from glob import glob
import pdb

from dlnpyutils import utils as dln
from . import apload
from astropy.io import fits


def expinfo(observatory=None,mjd5=None,files=None,expnum=None,apred='daily'):
    """
    Get header information about raw APOGEE files.
    This program can be run with observatory+mjd5 or
    by giving a list of files.

    Parameters
    ----------
    observatory : str, optional
        APOGEE observatory (apo or lco).
    mjd5 : int, optional
        The MJD5 night to get exposure information for.
    files : list of str, optional
        List of APOGEE apz filenames.
    expnum : list, optional
        List of exposure numbers.

    Returns
    -------
    cat : numpy structured array
        Table with information for each file grabbed from the header.

    Examples
    --------
    info = expinfo(files)

    By D.Nidever,  Oct 2020
    """

    # Types of inputs:
    #  files, observatory+mjd5, observatory+expnum
    if (files is None and observatory is None) or (files is None and mjd5 is None and expnum is None):
        raise ValueError('Either files or observatory+mjd5 or observatory+expnum must be input')
    if (mjd5 is not None and expnum is not None):
        raise ValueError('Input either observatory+mjd5 or observatory+expnum')

    load = apload.ApLoad(apred=apred,telescope='apo25m')

    # Get the exposures info for this MJD5        
    if files is None and expnum is None:
        if observatory not in ['apo','lco']:
            raise ValueError('observatory must be apo or lco')
        datadir = {'apo':os.environ['APOGEE_DATA_N'],'lco':os.environ['APOGEE_DATA_S']}[observatory]
        files = glob(datadir+'/'+str(mjd5)+'/a?R-c*.apz')
        files = np.array(files)
        nfiles = len(files)
        if nfiles==0:
            return []
        files = files[np.argsort(files)]  # sort        
    # Exposure numbers input
    if files is None and expnum is not None:
        if observatory not in ['apo','lco']:
            raise ValueError('observatory must be apo or lco')
        datadir = {'apo':os.environ['APOGEE_DATA_N'],'lco':os.environ['APOGEE_DATA_S']}[observatory]
        if type(expnum) is not list and type(expnum) is not np.ndarray:
            expnum = [expnum]
        nfiles = len(expnum)
        files = []
        for i in range(nfiles):
            file1 = load.filename('R',num=expnum[i],chips=True).replace('R-','R-c-')
            files.append(file1)
        files = np.array(files)
        files = files[np.argsort(files)]  # sort        

    nfiles = len(files)
    dtype = np.dtype([('num',int),('nread',int),('exptype',np.str,20),('arctype',np.str,20),('plateid',np.str,20),
                      ('configid',np.str,50),('designid',np.str,50),('fieldid',np.str,50),('exptime',float),
                      ('dateobs',np.str,50),('gangstate',np.str,20),('shutter',np.str,20),('calshutter',np.str,20),
                      ('mjd',int),('observatory',(np.str,10)),('dithpix',float)])
    info = np.zeros(nfiles,dtype=dtype)
    # Loop over the files
    for i in range(nfiles):
        if os.path.exists(files[i]):
            head = fits.getheader(files[i],1)
            base,ext = os.path.splitext(os.path.basename(files[i]))
            # apR-c-12345678.apz
            num = base.split('-')[2]
            info['num'][i] = num
            info['nread'][i] = head['nread']
            info['exptype'][i] = head['exptype']
            info['plateid'][i] = head['plateid']
            info['configid'][i] = head.get('configid')
            info['designid'][i] = head.get('designid')
            info['fieldid'][i] = head.get('fieldid')
            info['exptime'][i] = head['exptime']
            info['dateobs'][i] = head['date-obs']
            mjd = int(load.cmjd(int(num)))
            info['mjd'] = mjd
            #    info['mjd'] = utils.getmjd5(head['date-obs'])
            if observatory is not None:
                info['observatory'] = observatory
            else:
                info['observatory'] = {'p':'apo','s':'lco'}[base[1]]
            # arc types
            if info['exptype'][i]=='ARCLAMP':
                if head['lampune']==1:
                    info['arctype'][i] = 'UNE'
                elif head['lampthar']==1:
                    info['arctype'][i] = 'THAR'
                else:
                    info['arctype'][i] = 'None'
            # FPI
            if info['exptype'][i]=='ARCLAMP' and info['arctype'][i]=='None' and head.get('OBSCMNT')=='FPI':
                info['exptype'][i] = 'FPI'

            # Dither position
            info['dithpix'][i] = head['dithpix']
            # Gang state
            #  gangstat wasn't working properly until MJD=59592
            if mjd>=59592:
                info['gangstate'][i] = head.get('gangstat')
            # APOGEE Shutter state
            #  shutter wasn't working perly until MJD=59592
            if mjd>=59592:
                info['shutter'][i] = head.get('shutter')
            # CalBox shutter status
            lampshtr = head.get('lampshtr')
            if lampshtr is not None:
                if lampshtr:
                    info['calshutter'][i] = 'Open'
                else:
                    info['calshutter'][i] = 'Closed'

    return info


