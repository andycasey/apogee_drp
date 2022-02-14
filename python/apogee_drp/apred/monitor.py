import sys
import glob
import os
import subprocess
import math
import time
import numpy as np
from pathlib import Path
from astropy.io import fits, ascii
from astropy.table import Table
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import SkyCoord
from numpy.lib.recfunctions import append_fields, merge_arrays
from astroplan import moon_illumination
from astropy.coordinates import SkyCoord, get_moon
from astropy import units as astropyUnits
from scipy.signal import medfilt2d as ScipyMedfilt2D
from apogee_drp.utils import plan,apload,yanny,plugmap,platedata,bitmask
from apogee_drp.apred import wave
from apogee_drp.database import apogeedb
from dlnpyutils import utils as dln
from sdss_access.path import path
import pdb
import matplotlib.pyplot as plt
import matplotlib
from astropy.convolution import convolve, Box1DKernel
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import matplotlib.ticker as ticker
import matplotlib.colors as mplcolors
from matplotlib import cm as cmaps
from mpl_toolkits.axes_grid1.axes_divider import make_axes_locatable
from mpl_toolkits.axes_grid1.colorbar import colorbar
from datetime import date,datetime

# import pdb; pdb.set_trace()

''' MONITOR: Instrument monitoring plots and html '''
def monitor(instrument='apogee-n', apred='daily', clobber=True, makesumfiles=True,
            makeplots=True, makedomeplots=True, makequartzplots=True,
            makecomplots=False, fiberdaysbin=20):

    print("----> monitor starting")

    telescope = 'apo25m'
    if instrument == 'apogee-s': telescope = 'lco25m'

    chips = np.array(['blue','green','red'])
    nchips = len(chips)
    fibers = np.array([10,80,150,220,290])[::-1]
    nfibers = len(fibers)
    nlines = 2
    nquad = 4

    load = apload.ApLoad(apred=apred, telescope=telescope)

    # Establish  directories... hardcode sdss4/apogee2 for now
    specdir4 = '/uufs/chpc.utah.edu/common/home/sdss/apogeework/apogee/spectro/redux/current/'
    sdir4 = '/uufs/chpc.utah.edu/common/home/sdss/apogeework/apogee/spectro/redux/current/monitor/' + instrument + '/'

    specdir5 = os.environ.get('APOGEE_REDUX') + '/' + apred + '/'
    sdir5 = specdir5 + 'monitor/' + instrument + '/'

    # Read in the SDSS-IV/APOGEE2 summary files
    #allcal =  fits.open(specdir4 + instrument + 'Cal.fits')[1].data
    #alldark = fits.open(specdir4 + instrument + 'Cal.fits')[2].data
    #allexp =  fits.open(specdir4 + instrument + 'Exp.fits')[1].data
    #allsci =  fits.open(specdir4 + instrument + 'Sci.fits')[1].data
    #allepsf = fits.open(specdir4 + instrument + 'Trace.fits')[1].data

    allexp4 =  fits.open(specdir4 + instrument + 'Exp.fits')[1].data
    allsci4 =  fits.open(specdir4 + instrument + 'Sci.fits')[1].data

    # Read in the master summary files
    allcal =  fits.open(specdir5 + 'monitor/' + instrument + 'Cal.fits')[1].data
    alldark = fits.open(specdir5 + 'monitor/' + instrument + 'Cal.fits')[2].data
    allexp =  fits.open(specdir5 + 'monitor/' + instrument + 'Exp.fits')[1].data
    allsci =  fits.open(specdir5 + 'monitor/' + instrument + 'Sci.fits')[1].data
    snrfile = specdir5 + 'monitor/' + instrument + 'SNR.fits'
    dometrace = fits.getdata(specdir5 + 'monitor/' + instrument + 'DomeFlatTrace-all.fits')
    quartztrace = fits.getdata(specdir5 + 'monitor/' + instrument + 'QuartzFlatTrace-all.fits')
    #allepsf = fits.open(specdir5 + 'monitor/' + instrument + 'Trace.fits')[1].data

    if makesumfiles is True:
        ###########################################################################################
        # MAKE MASTER apSNRsum FILE
        # Append together S/N arrays and other metadata from apPlateSum files
        outfile = specdir5 + 'monitor/' + instrument + 'SNR.fits'
        print("----> monitor: Making " + os.path.basename(outfile))

        allvpath = '/uufs/chpc.utah.edu/common/home/sdss40/apogeework/apogee/spectro/aspcap/dr17/synspec/allVisit-dr17-synspec.fits'
        allv = fits.getdata(allvpath)

        gd, = np.where(allv['TELESCOPE'] == telescope)
        allv = allv[gd]
        vis = allv['FIELD'] + '/' + allv['PLATE'] + '/' + np.array(allv['MJD']).astype(str) + '/'
        uvis,uind = np.unique(pmf, return_index=True)
        uallv = allv[uind]
        nvis = len(uvis)

        for i in range(nvis):
            plsum = specdir4 + 'visit/' + telescope + '/' + uvis[i] + 'apPlateSum-' + uallv['PLATE'][i] + '-' + str(uallv['MJD'][i]) + '.fits'
            if os.path.exists(plsum):
                plsum1 = fits.open(plsum)[1].data
                plsum2 = fits.open(plsum)[2].data
                pdb.set_trace()



        files = glob.glob(specdir5 + 'visit/' + telescope + '/*/*/*/' + 'apPlateSum*.fits')
        if len(files) < 1:
            print("----> monitor: No apPlateSum files!")
        else:

            print("----> monitor: Making " + os.path.basename(outfile))

            # Make output structure and fill with APOGEE2 summary file values
            outstr = getSciStruct(allsci)

            files.sort()
            files = np.array(files)
            nfiles=len(files)

            # Loop over SDSS-V files and add them to output structure
            for i in range(nfiles):
                data = fits.open(files[i])[1].data
                check, = np.where(data['DATEOBS'][0] == outstr['DATEOBS'])
                if len(check) > 0:
                    #print("---->    monitor: skipping " + os.path.basename(files[i]))
                    continue
                else:
                    print("---->    monitor: adding " + os.path.basename(files[i]) + " to master file")
                    newstr = getSciStruct(data)
                    outstr = np.concatenate([outstr, newstr])

            Table(outstr).write(outfile, overwrite=True)
            print("----> monitor: Finished making " + os.path.basename(outfile))


        ###########################################################################################
        # MAKE MASTER apPlateSum FILE
        # Get zeropoint info from apPlateSum files
        # Append together the individual apPlateSum files

        files = glob.glob(specdir5 + 'visit/' + telescope + '/*/*/*/' + 'apPlateSum*.fits')
        if len(files) < 1:
            print("----> monitor: No apPlateSum files!")
        else:
            outfile = specdir5 + 'monitor/' + instrument + 'Sci.fits'
            print("----> monitor: Making " + os.path.basename(outfile))

            # Make output structure and fill with APOGEE2 summary file values
            outstr = getSciStruct(allsci)

            files.sort()
            files = np.array(files)
            nfiles=len(files)

            # Loop over SDSS-V files and add them to output structure
            for i in range(nfiles):
                data = fits.open(files[i])[1].data
                check, = np.where(data['DATEOBS'][0] == outstr['DATEOBS'])
                if len(check) > 0:
                    #print("---->    monitor: skipping " + os.path.basename(files[i]))
                    continue
                else:
                    print("---->    monitor: adding " + os.path.basename(files[i]) + " to master file")
                    newstr = getSciStruct(data)
                    outstr = np.concatenate([outstr, newstr])

            Table(outstr).write(outfile, overwrite=True)
            print("----> monitor: Finished making " + os.path.basename(outfile))

        ###########################################################################################
        # MAKE MASTER QACAL FILE
        # Append together the individual QAcal files

        files = glob.glob(specdir5 + 'cal/' + instrument + '/qa/*/*QAcal*.fits')
        if len(files) < 1:
            print("----> monitor: No QAcal files!")
        else:
            outfile = specdir5 + 'monitor/' + instrument + 'Cal.fits'
            print("----> monitor: Making " + os.path.basename(outfile))

            # Make output structure and fill with APOGEE2 summary file values
            outstr = getQAcalStruct(allcal)

            files.sort()
            files = np.array(files)
            nfiles = len(files)

            # Loop over SDSS-V files and add them to output structure
            for i in range(nfiles):
                data = fits.open(files[i])[1].data
                check, = np.where(data['NAME'][0] == outstr['NAME'])
                if len(check) > 0:
                    #print("---->    monitor: skipping " + os.path.basename(files[i]))
                    continue
                else:
                    print("---->    monitor: adding " + os.path.basename(files[i]) + " to master file")
                    newstr = getQAcalStruct(data)
                    outstr = np.concatenate([outstr, newstr])

            Table(outstr).write(outfile, overwrite=True)
            print("----> monitor: Finished adding QAcal info to " + os.path.basename(outfile))

        ###########################################################################################
        # APPEND QADARKFLAT INFO TO MASTER QACAL FILE
        # Append together the individual QAdarkflat files

        files = glob.glob(specdir5 + 'cal/' + instrument + '/qa/*/*QAdarkflat*.fits')
        if len(files) < 1:
            print("----> monitor: No QAdarkflat files!")
        else:
            print("----> monitor: Adding QAdarkflat info to " + os.path.basename(outfile))

            # Make output structure and fill with APOGEE2 summary file values
            outstr = getQAdarkflatStruct(alldark)

            files.sort()
            files = np.array(files)
            nfiles = len(files)

            # Loop over SDSS-V files and add them to output structure
            for i in range(nfiles):
                data = fits.open(files[i])[1].data
                check, = np.where(data['NAME'][0] == outstr['NAME'])
                if len(check) > 0:
                    #print("---->    monitor: skipping " + os.path.basename(files[i]))
                    continue
                else:
                    print("---->    monitor: adding " + os.path.basename(files[i]) + " to master file")
                    newstr = getQAdarkflatStruct(data)
                    outstr = np.concatenate([outstr, newstr])
                    
            hdulist = fits.open(outfile)
            hdu1 = fits.table_to_hdu(Table(outstr))
            hdulist.append(hdu1)
            hdulist.writeto(outfile, overwrite=True)
            hdulist.close()
            print("----> monitor: Finished adding QAdarkflat info to " + os.path.basename(outfile))

        ###########################################################################################
        # MAKE MASTER EXP FILE
        # Get long term trends from dome flats
        # Append together the individual exp files

        files = glob.glob(specdir5 + 'exposures/' + instrument + '/*/*exp.fits')
        if len(files) < 1:
            print("----> monitor: No exp files!")
        else:
            outfile = specdir5 + 'monitor/' + instrument + 'Exp.fits'
            print("----> monitor: Making " + os.path.basename(outfile))

            # Make output structure and fill with APOGEE2 summary file values
            outstr = getExpStruct(allexp)

            files.sort()
            files = np.array(files)
            nfiles=len(files)

            # Loop over SDSS-V files and add them to output structure
            for i in range(nfiles):
                data = fits.open(files[i])[1].data
                check, = np.where(data['DATEOBS'][0] == outstr['DATEOBS'])
                if len(check) > 0:
                    #print("---->    monitor: skipping " + os.path.basename(files[i]))
                    continue
                else:
                    print("---->    monitor: adding " + os.path.basename(files[i]) + " to master file")
                    newstr = getExpStruct(data)
                    outstr = np.concatenate([outstr, newstr])

            Table(outstr).write(outfile, overwrite=True)
            print("----> monitor: Finished making " + os.path.basename(outfile))


        ###########################################################################################
        # MAKE MASTER TRACE FILE
        # Append together the individual QAcal files

#        files = glob.glob(specdir5 + '/cal/' + instrument + '/psf/apEPSF-b-*.fits')
#        if len(files) < 1:
#            print("----> monitor: No apEPSF-b files!")
#        else:
#            outfile = specdir5 + 'monitor/' + instrument + 'Trace.fits'
#            print("----> monitor: Making " + os.path.basename(outfile))

            # Make output structure and fill with APOGEE2 summary file values
#            dt = np.dtype([('NUM',      np.int32),
#                           ('MJD',      np.float64),
#                           ('CENT',     np.float64),
#                           ('LN2LEVEL', np.int32)])

#            outstr = np.zeros(len(allepsf['NUM']), dtype=dt)

#            outstr['NUM'] =      allepsf['NUM']
#            outstr['MJD'] =      allepsf['MJD']
#            outstr['CENT'] =     allepsf['CENT']
#            outstr['LN2LEVEL'] = allepsf['LN2LEVEL']

#            files.sort()
#            files = np.array(files)
#            nfiles = len(files)

#            for i in range(nfiles):
#                print("---->    monitor: reading " + os.path.basename(files[i]))
#                data = fits.open(files[i])[1].data
#                import pdb; pdb.set_trace()
#                struct1 = np.zeros(len(data['NUM']), dtype=dt)
#                num = round(int(files[i].split('-b-')[1].split('.')[0]) / 10000)
#                if num > 1000:
#                    hdr = fits.getheader(files[i])
#                    for j in range(147,156):
#                        data = fits.open(files[i])[j].data
#                        if a['FIBER'] == 150:
#                            struct1['NUM'][i] = round(int(files[i].split('-b-')[1].split('.')[0]))
#                            struct1['CENT'][i] = data['CENT'][1000]
#                            struct1['MJD'][i] = hdr['JD-MJD'] - 2400000.5
#                            struct1['LN2LEVEL'][i] = hdr['LN2LEVEL']
#                            break
#                if i == 0: outstr = np.concatenate([outstr, struct1])
#                else:      outstr = np.concatenate([outstr, struct1])

#            Table(outstr).write(outfile, overwrite=True)
#            print("----> monitor: Finished making " + os.path.basename(outfile))

    ###############################################################################################
    # Read in the SDSS-V summary files
    allcal =  fits.open(specdir5 + 'monitor/' + instrument + 'Cal.fits')[1].data
    alldark = fits.open(specdir5 + 'monitor/' + instrument + 'Cal.fits')[2].data
    allexp =  fits.open(specdir5 + 'monitor/' + instrument + 'Exp.fits')[1].data
    allsci =  fits.open(specdir5 + 'monitor/' + instrument + 'Sci.fits')[1].data
    #allepsf = fits.open(specdir5 + 'monitor/' + instrument + 'Trace.fits')[1].data
    # Read in the APOGEE2 Trace.fits file since the columns don't match between APOGEE2 and SDSS-V
    allepsf = fits.open(specdir4 + instrument + 'Trace.fits')[1].data

    ###############################################################################################
    # Find the different cals
    thar, = np.where(allcal['THAR'] == 1)
    une, =  np.where(allcal['UNE'] == 1)
    qrtz, = np.where(allcal['QRTZ'] == 1)
    dome, = np.where(allexp['IMAGETYP'] == 'DomeFlat')
    qrtzexp, = np.where(allexp['IMAGETYP'] == 'QuartzFlat')
    dark, = np.where(alldark['EXPTYPE'] == 'DARK')

    ###############################################################################################
    # MAKE THE MONITOR HTML
    outfile = specdir5 + 'monitor/' + instrument + '-monitor.html'
    print("----> monitor: Making " + os.path.basename(outfile))

    now = datetime.now()
    today = date.today()
    current_time = now.strftime("%H:%M:%S")
    current_date = today.strftime("%B %d, %Y")
    
    html = open(outfile, 'w')
    tit = 'APOGEE-N Instrument Monitor'
    if instrument != 'apogee-n': tit = 'APOGEE-S Instrument Monitor'
    html.write('<HTML><HEAD><title>' + tit + '</title></head><BODY>\n')
    html.write('<H1>' + tit + '</H1>\n')
    html.write('<P><I>last updated ' + current_date + ', ' + current_time + '</I></P>')
    html.write('<HR>\n')
    html.write('<ul>\n')
    html.write('<li> <a href=#sciobs> Science observation history</a>\n')
    html.write('<li> Throughput / lamp monitors\n')
    html.write('<ul>\n')
    html.write('<li> <a href=#qflux>Quartz lamp median brightness</a>\n')
    html.write('<li> <a href=#qfwhm>Quartz lamp trace FWHM</a>\n')
    html.write('<li> <a href=#dflux>Dome flat median brightness</a>\n')
    html.write('<li> <a href=#dfwhm>Dome flat trace FWHM</a>\n')
    html.write('<li> <a href=' + instrument + '/qfiber/fiber_qrtz.html target="_blank">Fiber throughput from quartz lamp</a>\n')
    html.write('<li> <a href=' + instrument + '/dfiber/fiber.html target="_blank">Fiber throughput from dome flats</a>\n')
    html.write('<li> <a href=#tharflux> Cal channel ThAr</a>\n')
    html.write('<li> <a href=#uneflux> Cal channel UNe</a>\n')
    html.write('<li> <a href=#zero>Plate zeropoints</a>\n')
    html.write('</ul>\n')
    html.write('<li> Positions\n')
    html.write('<ul>\n')
    html.write('<li> <a href=#tpos>ThAr line position</a>\n')
    html.write('</ul>\n')
    html.write('<li> Line widths\n')
    html.write('<ul>\n')
    html.write('<li> <a href=#tfwhm>ThAr line FWHM</a>\n')
    html.write('</ul>\n')
    html.write('<li> <a href=#trace>Trace locations</a>\n')
    html.write('<li> <a href=#detectors> Detectors\n')
    html.write('<li> <a href=#sky> Sky brightness\n')
    html.write('<li> <a href=' + instrument + '/flatflux.html target="_blank">Flat Field Relative Flux Plots</a>\n')
    html.write('</ul>\n')
    html.write('<HR>\n')

    html.write('<h3> <a name=sciobs></a> Science observation history </h3>\n')
    html.write('<A HREF=' + instrument + '/sciobs.png target="_blank"><IMG SRC=' + instrument + '/sciobs.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<h3> <a name=qflux></a> Quartz lamp median brightness (per 10 reads) in extracted frame </h3>\n')
    html.write('<A HREF=' + instrument + '/qflux.png target="_blank"><IMG SRC=' + instrument + '/qflux.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<h3> <a name=qfwhm></a> Quartz lamp trace FWHM </h3>\n')
    html.write('<A HREF=' + instrument + '/qfwhm.png target="_blank"><IMG SRC=' + instrument + '/qfwhm.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=dflux></a> Dome flat median brightness</H3>\n')
    html.write('<P> (Note: horizontal lines are the medians across all fibers) </P>\n')
    html.write('<A HREF=' + instrument + '/dflux.png target="_blank"><IMG SRC=' + instrument + '/dflux.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<h3> <a name=dfwhm></a> Dome flat trace FWHM </h3>\n')
    html.write('<A HREF=' + instrument + '/dfwhm.png target="_blank"><IMG SRC=' + instrument + '/dfwhm.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a href=' + instrument + '/fiber/fiber.html> Individual fiber throughputs from dome flats </A></H3>\n')
    html.write('<HR>\n')

    html.write('<H3> <a href=' + instrument + '/fiber/fiber_qrtz.html> Individual fiber throughputs from quartz lamp</A></H3>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=tharflux></a>ThAr line brightness (per 10 reads) in extracted frame </H3>\n')
    html.write('<A HREF=' + instrument + '/tharflux.png target="_blank"><IMG SRC=' + instrument + '/tharflux.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=uneflux></a>UNe line brightness (per 10 reads) in extracted frame </H3>\n')
    html.write('<A HREF=' + instrument + '/uneflux.png target="_blank"><IMG SRC=' + instrument + '/uneflux.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=zero></a>Science frame zero point</H3>\n')
    html.write('<A HREF=' + instrument + '/zero.png target="_blank"><IMG SRC=' + instrument + '/zero.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=tpos></a>ThArNe lamp line position</H3>\n')
    html.write('<A HREF=' + instrument + '/tpos.png target="_blank"><IMG SRC=' + instrument + '/tpos.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    for iline in range(2):
        plotfile='tfwhm' + str(iline) + '.png'
        tmp1 = str("%.1f" % round(allcal['LINES'][thar][0][iline][0],1))
        tmp2 = str("%.1f" % round(allcal['LINES'][thar][0][iline][1],1))
        tmp3 = str("%.1f" % round(allcal['LINES'][thar][0][iline][2],1))
        txt = '<a name=tfwhm></a> ThArNe lamp line FWHM, line position (x pixel): '
        html.write('<H3>' + txt + tmp1 + ' ' + tmp2 + ' ' + tmp3 + '</H3>\n')
        html.write('<P> (Note: horizontal lines are the median value for each fiber.) </P>\n')
        html.write('<A HREF=' + instrument + '/' + plotfile + ' target="_blank"><img src=' + instrument + '/' + plotfile + ' WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=trace></a> Trace position, fiber 150, column 1000</H3>\n')
    html.write('<A HREF=' + instrument + '/trace.png target="_blank"><IMG SRC=' + instrument + '/trace.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=detectors></a>Detectors</H3>\n')
    html.write('<P> (Note: the four colors indicate the four quadrants in each detector.) </P>\n')
    html.write('<H4> Dark Mean </h4>\n')
    html.write('<A HREF=' + instrument + '/biasmean.png target="_blank"><IMG SRC=' + instrument + '/biasmean.png WIDTH=1000></A>\n')

    html.write('<H4> Dark Sigma </h4>\n')
    html.write('<A HREF=' + instrument + '/biassig.png target="_blank"><IMG SRC=' + instrument + '/biassig.png WIDTH=1000></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=sky></a>Sky Brightness</H3>\n')
    html.write('<A HREF=' + instrument + '/moonsky.png target="_blank"><IMG SRC=' + instrument + '/moonsky.png WIDTH=1300></A>\n')

    html.write('<BR><BR><BR><BR>')
    html.write('</BODY></HTML>\n')

    html.close()

    ###############################################################################################
    # HTML for individual fiber throughput plots (dome flats)
    badfibers = np.array(['015','034','105','111','115','121','122','123','124','125','126','127',
                          '128','129','130','131','132','133','134','135','136','137','138','139',
                          '140','141','142','143','144','145','146','147','148','149','150','151',
                          '182','202','227','245','250','277','278','284','289',])
    deadfibers = np.array(['211','273'])

    badfibersS = np.array(['031','034','039','061','067','069','083','084','091','129','136','140',
                           '145','147','151','165','180','241','269'])
    deadfibersS = None

    if instrument == 'apogee-s':
        badfibers = badfibersS
        deadfibers = deadfibersS

    fibdir = specdir5 + 'monitor/' + instrument + '/fiber/'
    if os.path.exists(fibdir) is False: os.mkdir(fibdir)
    fhtml = open(fibdir + 'fiber.html', 'w')
    tit = 'APOGEE-N Fiber Throughput (Dome Flat)'
    if instrument != 'apogee-n': tit = 'APOGEE-S Fiber Throughput (Dome Flat)'
    fhtml.write('<HTML><HEAD><script src="../../../../sorttable.js"></script><title>' + tit + '</title></head><BODY>\n')
    fhtml.write('<H1>' + tit + '</H1>\n')
    fhtml.write('<HR>\n')
    fhtml.write('<P> The throughput plots show the median dome flat flux in each fiber divided by the maximum ')
    fhtml.write('across all fibers in a given observation.</P>\n')
    fhtml.write('<P><FONT color="#E53935">Red</FONT> highlighting indicates broken fibers.</P>\n')
    fhtml.write('<P><FONT color="#FFA726">Orange</FONT> highlighting indicates fibers with long-term throughput deviations.</P>\n')
    fhtml.write('<TABLE BORDER=2 CLASS="sortable">\n')
    fhtml.write('<TR bgcolor="#DCDCDC"> <TH>Fiber<BR>(MTP #) <TH>Fiber<BR>"Goodness" <TH>Median Dome Flat Flux <TH>Throughput\n')
    for ifiber in range(300):
        cfib = str(ifiber+1).zfill(3)
        cblock = str(np.ceil((ifiber+1)/30).astype(int))
        plotfile1 = 'fiber' + cfib + '.png'
        plotfile2 = 'fiber' + cfib + '_throughput.png'

        fibqual = 'normal'
        bgcolor = '#FFFFFF'

        if deadfibers is not None:
            bd, = np.where(cfib == deadfibers)
            if len(bd) >= 1: 
                fibqual = 'dead'
                bgcolor = '#E53935'
        if badfibers is not None:
            bd, = np.where(cfib == badfibers)
            if len(bd) >= 1:
                fibqual = 'problematic'
                bgcolor = '#FFA726'

        fhtml.write('<TR bgcolor="' + bgcolor + '">')
        fhtml.write('<TD ALIGN=center>' + cfib + '<BR>(' + cblock + ') <TD ALIGN=center>' + fibqual)
        fhtml.write('<TD> <A HREF=' + plotfile1 + ' target="_blank"><IMG SRC=' + plotfile1 + ' WIDTH=700></A>')
        fhtml.write('<TD ALIGN=center><A HREF=' + plotfile2 + ' target="_blank"><IMG SRC=' + plotfile2 + ' WIDTH=700></A>\n')
    fhtml.write('</TABLE></BODY></HTML>\n')
    fhtml.close()

    ###############################################################################################
    # HTML for individual fiber throughput plots (quartz lamp)
    fibdir = specdir5 + 'monitor/' + instrument + '/fiber/'
    if os.path.exists(fibdir) is False: os.mkdir(fibdir)
    fhtml = open(fibdir + 'fiber_qrtz.html', 'w')
    tit = 'APOGEE-N Fiber Throughput (Quartz)'
    if instrument != 'apogee-n': tit = 'APOGEE-S Fiber Throughput (Quartz)'
    fhtml.write('<HTML><HEAD><script src="../../../../sorttable.js"></script><title>' + tit + '</title></head><BODY>\n')
    fhtml.write('<H1>' + tit + '</H1>\n')
    fhtml.write('<HR>\n')
    fhtml.write('<P> The throughput plots show the quartz lamp flux in each fiber divided by the maximum ')
    fhtml.write('across all fibers in a given observation.</P>\n')
    fhtml.write('<TABLE BORDER=2 CLASS="sortable">\n')
    fhtml.write('<TR bgcolor="#DCDCDC"> <TH>Fiber<BR>(MTP #) <TH>Quartz Flux <TH>Throughput\n')
    for ifiber in range(300):
        cfib = str(ifiber+1).zfill(3)
        cblock = str(np.ceil((ifiber+1)/30).astype(int))
        plotfile1 = 'fiber' + cfib + '_qrtz.png'
        plotfile2 = 'fiber' + cfib + '_throughput_qrtz.png'

        fhtml.write('<TR>')
        fhtml.write('<TD ALIGN=center>' + cfib + '<BR>(' + cblock + ')')
        fhtml.write('<TD> <A HREF=' + plotfile1 + ' target="_blank"><IMG SRC=' + plotfile1 + ' WIDTH=700></A>')
        fhtml.write('<TD ALIGN=center><A HREF=' + plotfile2 + ' target="_blank"><IMG SRC=' + plotfile2 + ' WIDTH=700></A>\n')
    fhtml.write('</TABLE></BODY></HTML>\n')
    fhtml.close()

    ###############################################################################################
    # HTML for flat field relative flux plots
#    fhtml = open(specdir5 + 'monitor/' + instrument + '/flatflux.html', 'w')
#    tit = 'APOGEE-N Flat Field Relative Flux plots'
#    if instrument != 'apogee-n': tit = 'APOGEE-S Flat Field Relative Flux plots'
#    fhtml.write('<HTML><HEAD><script src="../../../sorttable.js"></script><title>' + tit + '</title></head><BODY>\n')
#    fhtml.write('<H1>' + tit + '</H1>\n')
#    fhtml.write('<TABLE BORDER=2  CLASS="sortable">\n')
#    fhtml.write('<TR bgcolor="#DCDCDC"> <TH>MJD <TH>DATE <TH>FIELD <TH>PLATE <TH>GREEN CHIP PLOT\n')
#    pfiles0 = np.array(glob.glob(specdir4 + 'visit/' + telescope + '/*/*/585*/plots/apFlux-b-*jpg'))
#    pfiles1 = np.array(glob.glob(specdir4 + 'visit/' + telescope + '/*/*/586*/plots/apFlux-b-*jpg'))
#    pfiles2 = np.array(glob.glob(specdir4 + 'visit/' + telescope + '/*/*/587*/plots/apFlux-b-*jpg'))
#    pfiles3 = np.array(glob.glob(specdir4 + 'visit/' + telescope + '/*/*/588*/plots/apFlux-b-*jpg'))
#    pfiles4 = np.array(glob.glob(specdir4 + 'visit/' + telescope + '/*/*/589*/plots/apFlux-b-*jpg'))
#    pfiles5 = np.array(glob.glob(specdir4 + 'visit/' + telescope + '/*/*/584*/plots/apFlux-b-*jpg'))
#    pfiles = np.concatenate([pfiles0, pfiles1, pfiles2, pfiles3, pfiles4, pfiles5])
#    for i in range(len(pfiles)):
#        tmp = pfiles[i].split(telescope + '/')[1].split('/')
#        gfield = tmp[0]
#        gplate = tmp[1]
#        gmjd = tmp[2]
#        t = Time(float(gmjd), format='mjd')
#        gdate = t.fits
#        gplot = tmp[-1]
#        relpath = 'flatflux/' + gplot
#        fhtml.write('<TR>')
#        fhtml.write('<TD ALIGN=center>' + gmjd + '<TD>' + gdate + '<TD>' + gfield + '<TD>' + gplate + '<TD> <A HREF=' + relpath + ' target="_blank"><IMG SRC=' + relpath + ' WIDTH=300></A>')
#    fhtml.write('</TABLE></BODY></HTML>\n')
#    fhtml.close()

#    for i in range(len(pfiles)):
#        gplot = pfiles[i].split(telescope + '/')[1].split('/')[-1]
#        check = glob.glob('flatflux/' + gplot)
#        if len(check) < 1: subprocess.call(['scp', pfiles[i], sdir5 + 'flatflux/'])

    ###############################################################################################
    # Set up some basic plotting parameters
    matplotlib.use('agg')
    fontsize = 24;   fsz = fontsize * 0.75
    matplotlib.rcParams.update({'font.size':fontsize, 'font.family':'serif'})
    bboxpar = dict(facecolor='white', edgecolor='none', alpha=1.0)
    axwidth = 1.5
    axmajlen = 7
    axminlen = 3.5
    alf = 0.6
    markersz = 7
    colors = np.array(['midnightblue', 'deepskyblue', 'mediumorchid', 'red', 'orange'])[::-1]
    colors1 = np.array(['k', 'b', 'r', 'gold'])
    colors2 = np.array(['dodgerblue', 'seagreen', 'orange'])
    fibers = np.array([10, 80, 150, 220, 290])[::-1]
    nplotfibs = len(fibers)
    #years = np.array([2011, 2012, 2013, 2014

    tmp = allcal[qrtz]
    caljd = tmp['JD'] - 2.4e6
    t = Time(tmp['JD'], format='jd')
    years = np.unique(np.floor(t.byear)) + 1
    cyears = years.astype(int).astype(str)
    nyears = len(years)
    t = Time(years, format='byear')
    yearjd = t.jd - 2.4e6
    minjd = np.min(caljd)
    maxjd = np.max(caljd)
    jdspan = maxjd - minjd
    xmin = minjd - jdspan * 0.01
    xmax = maxjd + jdspan * 0.10
    xspan = xmax-xmin

    if makedomeplots is True:
        ###########################################################################################
        # Individual fiber throughput plots

        #gd, = np.where(allcal['QRTZ'] > 0)                                                       
        #gdcal = allcal[gd]

        for i in range(300):
            gdcal = allexp[dome]
            caljd = gdcal['JD'] - 2.4e6
            ymax1 = 16;   ymin1 = 0 - ymax1 * 0.05;   yspan1 = ymax1 - ymin1
            ymax2 = 1.1; ymin2 = 0;                  yspan2 = ymax2 - ymin2

            plotfile = specdir5 + 'monitor/' + instrument + '/fiber/fiber' + str(i + 1).zfill(3) + '.png'
            if (os.path.exists(plotfile) == False) | (clobber == True):
                print("----> monitor: Making " + os.path.basename(plotfile))

                fig = plt.figure(figsize=(28,7.5))
                ax = plt.subplot2grid((1,1), (0,0))
                ax.set_xlim(xmin, xmax - xspan*0.05)
                ax.set_ylim(ymin1, ymax1)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                ax.set_xlabel(r'JD - 2,400,000')
                ax.text(-0.03, 0.5, r'Median Flux / 1,000', rotation=90, ha='right', va='center', transform=ax.transAxes)
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    ax.text(yearjd[iyear], ymax1+yspan1*0.02, cyears[iyear], ha='center')

                yvals = np.empty((len(caljd), nchips))
                for ichip in range(nchips):
                    yvals[:, ichip] = gdcal['MED'][:, ichip, 299-i] / 1000
                    ax.scatter(caljd, yvals[:, ichip], marker='o', s=markersz, c=colors2[ichip], alpha=alf)
                    ax.text(0.995, 0.75-(0.25*ichip), chips[ichip].capitalize()+'\n'+'Chip', c=colors2[ichip], 
                            fontsize=fsz, va='center', ha='right', transform=ax.transAxes, bbox=bboxpar)
                            
                # Bin up the data points and plot black squares
                meanyvals = np.nanmean(yvals, axis=1)
                tmin = np.min(caljd)
                tmax = np.max(caljd) + fiberdaysbin
                xx = np.arange(tmin, tmax, fiberdaysbin)
                nbins = len(xx)
                binx = []
                biny = []
                for k in range(nbins-1):
                    gd, = np.where((caljd >= xx[k]) & (caljd < xx[k+1]))
                    if len(gd) > 0:
                        binx.append(np.nanmean([xx[k], xx[k+1]]))
                        biny.append(np.nanmean(meanyvals[gd]))
                ax.scatter(binx, biny, marker='D', s=markersz*5, color='k', zorder=10)

                fig.subplots_adjust(left=0.045,right=0.99,bottom=0.115,top=0.94,hspace=0.08,wspace=0.00)
                plt.savefig(plotfile)
                plt.close('all')

            plotfile = specdir5 + 'monitor/' + instrument + '/fiber/fiber' + str(i + 1).zfill(3) + '_throughput.png'
            if (os.path.exists(plotfile) == False) | (clobber == True):
                print("----> monitor: Making " + os.path.basename(plotfile))

                fig = plt.figure(figsize=(28,7.5))
                ax = plt.subplot2grid((1,1), (0,0))
                ax.set_xlim(xmin, xmax - xspan*0.05)
                ax.set_ylim(ymin2, ymax2)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                ax.set_xlabel(r'JD - 2,400,000')
                ax.text(-0.03, 0.5, r'Flux / max(Flux)', rotation=90, ha='right', va='center', transform=ax.transAxes)
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    ax.text(yearjd[iyear], ymax2+yspan2*0.02, cyears[iyear], ha='center')

                yvals = np.empty((len(caljd), nchips))
                for ichip in range(nchips):
                    yvals[:, ichip] = gdcal['MED'][:, ichip, 299-i] / np.nanmax(gdcal['MED'][:, ichip, :], axis=1)
                    ax.scatter(caljd, yvals[:, ichip], marker='o', s=markersz, c=colors2[ichip], alpha=alf)
                    ax.text(0.995, 0.75-(0.25*ichip), chips[ichip].capitalize()+'\n'+'Chip', c=colors2[ichip], 
                            fontsize=fsz, va='center', ha='right', transform=ax.transAxes, bbox=bboxpar)

                # Bin up the data points and plot black squares
                meanyvals = np.nanmean(yvals, axis=1)
                tmin = np.min(caljd)
                tmax = np.max(caljd) + fiberdaysbin
                xx = np.arange(tmin, tmax, fiberdaysbin)
                nbins = len(xx)
                binx = []
                biny = []
                for k in range(nbins-1):
                    gd, = np.where((caljd >= xx[k]) & (caljd < xx[k+1]))
                    if len(gd) > 0:
                        binx.append(np.nanmean([xx[k], xx[k+1]]))
                        biny.append(np.nanmean(meanyvals[gd]))
                ax.scatter(binx, biny, marker='D', s=markersz*5, color='k', zorder=10)

                fig.subplots_adjust(left=0.045,right=0.99,bottom=0.115,top=0.94,hspace=0.08,wspace=0.00)
                plt.savefig(plotfile)
                plt.close('all')

    if makequartzplots is True:
        for i in range(300):
            gd, = np.where(allcal['QRTZ'] > 0)
            gdcal = allcal[gd]
            caljd = gdcal['JD'] - 2.4e6
            ymax1 = 50;   ymin1 = 0 - ymax1 * 0.05;   yspan1 = ymax1 - ymin1
            #ymax2 = 1.1; ymin2 = 0;                  yspan2 = ymax2 - ymin2

            plotfile = specdir5 + 'monitor/' + instrument + '/fiber/fiber' + str(i + 1).zfill(3) + '_qrtz.png'
            if (os.path.exists(plotfile) == False) | (clobber == True):
                print("----> monitor: Making " + os.path.basename(plotfile))

                fig = plt.figure(figsize=(28,7.5))
                ax = plt.subplot2grid((1,1), (0,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin1, ymax1)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                ax.set_xlabel(r'JD - 2,400,000')
                ax.text(-0.03, 0.5, r'Flux / 1,000', rotation=90, ha='right', va='center', transform=ax.transAxes)
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    ax.text(yearjd[iyear], ymax1+yspan1*0.02, cyears[iyear], ha='center')

                for ichip in range(nchips):
                    yvals = gdcal['FLUX'][:, ichip, 299-i] / 1000
                    ax.scatter(caljd, yvals, marker='o', s=markersz, c=colors2[ichip], alpha=alf)
                    ax.text(0.995, 0.75-(0.25*ichip), chips[ichip].capitalize()+'\n'+'Chip', c=colors2[ichip], 
                            fontsize=fsz, va='center', ha='right', transform=ax.transAxes, bbox=bboxpar)

                fig.subplots_adjust(left=0.045,right=0.99,bottom=0.115,top=0.94,hspace=0.08,wspace=0.00)
                plt.savefig(plotfile)
                plt.close('all')

            plotfile = specdir5 + 'monitor/' + instrument + '/fiber/fiber' + str(i + 1).zfill(3) + '_throughput_qrtz.png'
            if (os.path.exists(plotfile) == False) | (clobber == True):
                print("----> monitor: Making " + os.path.basename(plotfile))

                fig = plt.figure(figsize=(28,7.5))
                ax = plt.subplot2grid((1,1), (0,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin2, ymax2)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                ax.set_xlabel(r'JD - 2,400,000')
                ax.text(-0.03, 0.5, r'Flux / max(Flux)', rotation=90, ha='right', va='center', transform=ax.transAxes)
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    ax.text(yearjd[iyear], ymax2+yspan2*0.02, cyears[iyear], ha='center')

                for ichip in range(nchips):
                    yvals = gdcal['FLUX'][:, ichip, 299-i] / np.nanmax(gdcal['FLUX'][:, ichip, :], axis=1)
                    ax.scatter(caljd, yvals, marker='o', s=markersz, c=colors2[ichip], alpha=alf)
                    ax.text(0.995, 0.75-(0.25*ichip), chips[ichip].capitalize()+'\n'+'Chip', c=colors2[ichip], 
                            fontsize=fsz, va='center', ha='right', transform=ax.transAxes, bbox=bboxpar)

                fig.subplots_adjust(left=0.045,right=0.99,bottom=0.115,top=0.94,hspace=0.08,wspace=0.00)
                plt.savefig(plotfile)
                plt.close('all')


    if makecomplots is True:
        ###########################################################################################
        # snhistory2.png
        plotfile = specdir5 + 'monitor/' + instrument + '/snhistory2.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            #gd, = np.where((allsci['SN'][:,1] > 15) & (allsci['MJD'] > 59146))
            gd, = np.where(allsci['MJD'] > 59146)
            gsci = allsci[gd]
            gord = np.argsort(gsci['MJD'])
            gsci = gsci[gord]
            nsci = len(gd)

            #fields = np.array(['18956', '19106', '19092', '19942', '19942', '19942', '18956', '19942', '20950', '20918', '18956', '18956', '18956', '20549', '20549', '20549', '20549', '20002', '20902', '20900', '17031', '20894', '19942', '19852', '19852'])
            #plates = np.array(['1917', '2573', '2649', '3238', '3235', '3233', '3239', '3234', '3258', '3216', '3207', '3206', '3203', '3198', '3199', '3201', '3202', '3167', '3174', '3172', '3122', '3168', '3119', '3120', '3121'])
            #mjds = np.array(['59595', '59601', '59602', '59620', '59620', '59620', '59620', '59620', '59620', '59619', '59619', '59619', '59619', '59619', '59619', '59619', '59619', '59618', '59618', '59618', '59618', '59618', '59616', '59616'])


            fig = plt.figure(figsize=(30,14))

            allv5 = fits.getdata(specdir5 + 'summary/allVisit-daily-apo25m.fits')
            umjd,uind = np.unique(allv5['mjd'], return_index=True)
            nmjd = len(umjd)

            ax = plt.subplot2grid((1,1), (0,0))
            ax.set_xlim(xmin, xmax)
            #ax.set_ylim(ymin, ymax)
            ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
            ax.minorticks_on()
            ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
            ax.tick_params(axis='both',which='major',length=axmajlen)
            ax.tick_params(axis='both',which='minor',length=axminlen)
            ax.tick_params(axis='both',which='both',width=axwidth)
            #if ichip == nchips-1: ax.set_xlabel(r'MJD')
            ax.set_xlabel(r'MJD')
            ax.set_ylabel(r'S/N$^{2}$ per minute')
            #if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
            ax.axvline(x=59146, color='r', linewidth=2)

            for iyear in range(nyears):
                ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                #if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

            maglims = [10.5, 11.5]
            snr = []
            jd = []
            secz = []
            expt = []
            moondist = []
            moonphase = []
            seeing  = []
            for isci in range(nsci):
                print(str(isci+1) + '/' + str(nsci))
                plsum = glob.glob(specdir5 + 'visit/apo25m/*/' + str(gsci['PLATE'][isci]) + '/' + str(gsci['MJD'][isci]) + '/apPlateSum-*fits')
                if len(plsum) < 1: continue
                d1 = fits.open(plsum[0])[1].data
                d2 = fits.open(plsum[0])[2].data
                nexp = len(d1['EXPTIME'])
                for iexp in range(nexp):
                    print('   ' + str(iexp))
                    gd, = np.where((d2['hmag'] >= maglims[0]) & (d2['hmag'] <= maglims[1]) & (d2['SN'][:,iexp,1] > 50))
                    if len(gd) > 2:
                        tt = Time(d1['DATEOBS'][iexp], format='fits')
                        jd.append(tt.jd - 2.4e6)
                        secz.append(d1['SECZ'][iexp])
                        expt.append(d1['EXPTIME'][iexp])
                        moondist.append(d1['MOONDIST'][iexp])
                        moonphase.append(d1['MOONPHASE'][iexp])
                        seeing.append(d1['SEEING'][iexp])

                        sn = d2['SN'][gd, iexp, 1]
                        meansn = np.nanmean(sn)
                        sigsn = np.nanstd(sn)
                        dif = np.absolute(sn - meansn)
                        gd, = np.where(dif < 2*sigsn)
                        sn = sn[gd]
                        snr.append(np.nanmean(sn))

            snr = np.array(snr)
            jd = np.array(jd)
            secz = np.array(secz)
            expt = np.array(expt)
            moondist = np.array(moondist)
            moonphase = np.array(moonphase)
            seeing  = np.array(seeing)

            yvals = (snr**2)  / expt / 60
            ax.scatter(jd, yvals, marker='o', s=markersz)#, c=colors[ifib], alpha=alf)#, label='Fiber ' + str(fibers[ifib]))

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

            pdb.set_trace()

        return

        ###########################################################################################
        # snhistory.png
        plotfile = specdir5 + 'monitor/' + instrument + '/snhistory.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))

            gd, = np.where(allsci['EXPTIME'] > 0)
            gdcal = allsci[gd]
            caljd = gdcal['MJD']# - 2.4e6

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                #ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'MJD')
                ax.set_ylabel(r'S/N$^{2}$ per minute')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                #for iyear in range(nyears):
                #    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                #    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

                yvals = (gdcal['SN'][:, ichip]**2)  / gdcal['EXPTIME'] / 60
                ax.scatter(caljd, yvals, marker='o', s=markersz)#, c=colors[ifib], alpha=alf)#, label='Fiber ' + str(fibers[ifib]))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                #if ichip == 0: 
                #    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                #              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        return


        ###########################################################################################
        # rvparams1.png
        # Plot of residuals of stellar parameters, plate vs. FPS
        allvpath = '/uufs/chpc.utah.edu/common/home/sdss40/apogeework/apogee/spectro/aspcap/dr17/synspec/allStarLite-dr17-synspec.fits'
        allv = fits.getdata(allvpath)

        fields = np.array(['18956', '19106', '19092'])
        plates = np.array(['1917', '2573', '2649'])
        mjds = np.array(['59595', '59601', '59602'])
        ind = 0

        sbs = np.array(['2M08182323+4616076', '2M08174272+4648176', '2M08121440+4634381', '2M08195933+4749123'])

        plotfile = specdir5 + 'monitor/' + instrument + '/rvparams1-' + fields[ind] + '-' + plates[ind] + '-' + mjds[ind] + '.png'
        print("----> monitor: Making " + os.path.basename(plotfile))

        # DB query for this visit
        db = apogeedb.DBSession()
        vcat = db.query('visit_latest', where="plate='" + plates[ind] + "' and mjd='" + mjds[ind] + "'", fmt='table')
        gd, = np.where(vcat['snr'] > 20)
        vcat = vcat[gd]
        nv = len(vcat)

        fig = plt.figure(figsize=(22,18))
        ax1 = plt.subplot2grid((2,2), (0,0))
        ax2 = plt.subplot2grid((2,2), (0,1))
        ax3 = plt.subplot2grid((2,2), (1,0))
        ax4 = plt.subplot2grid((2,2), (1,1))
        axes = [ax1,ax2,ax3,ax4]
        ax1.set_xlim(-140, 140)
        ax1.set_ylim(-10, 10)
        ax2.set_xlim(3.0, 8.5)
        ax2.set_ylim(-0.5, 0.5)
        ax3.set_xlim(0.5, 5.5)
        ax3.set_ylim(-0.5, 0.5)
        ax4.set_xlim(-2.5, 1.0)
        ax4.set_ylim(-0.5, 0.5)
        ax1.set_xlabel(r'DR17 $V_{\rm helio}$ (km$\,$s$^{-1}$)')
        ax1.set_ylabel(r'DR17 $-$ FPS')
        ax2.set_xlabel(r'DR17 RV $T_{\rm eff}$ (kK)')
        ax3.set_xlabel(r'DR17 RV log$\,g$')
        ax3.set_ylabel(r'DR17 $-$ FPS')
        ax4.set_xlabel(r'DR17 RV [Fe/H]')
        ax1.xaxis.set_major_locator(ticker.MultipleLocator(50))
        #ax1.yaxis.set_major_locator(ticker.MultipleLocator(50))
        ax4.xaxis.set_major_locator(ticker.MultipleLocator(1.0))
        #ax4.yaxis.set_major_locator(ticker.MultipleLocator(1.0))
        tmp = 'field: ' + fields[ind] + '    plate: ' + plates[ind] + '    mjd: ' + mjds[ind]
        ax1.text(1.05, 1.03, tmp, transform=ax1.transAxes, ha='center')
        for ax in axes:
            ax.minorticks_on()
            ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
            ax.tick_params(axis='both',which='major',length=axmajlen)
            ax.tick_params(axis='both',which='minor',length=axminlen)
            ax.tick_params(axis='both',which='both',width=axwidth)
            ax.axhline(y=0, linestyle='dashed', color='k', zorder=1)
            #ax.plot([-100,100000], [-100,100000], linestyle='dashed', color='k')

        vh17 = np.zeros(nv)
        teff17 = np.zeros(nv)
        logg17 = np.zeros(nv)
        feh17 = np.zeros(nv)
        for i in range(nv):
            gd,=np.where(vcat['apogee_id'][i] == allv['APOGEE_ID'])
            if len(gd) > 0:
                vh17[i] = allv['VHELIO_AVG'][gd][0]
                teff17[i] = allv['RV_TEFF'][gd][0]
                logg17[i] = allv['RV_LOGG'][gd][0]
                feh17[i] = allv['RV_FEH'][gd][0]

        gd, = np.where(teff17 > 0)
        vh17 = vh17[gd]
        teff17 = teff17[gd]
        logg17 = logg17[gd]
        feh17 = feh17[gd]
        vcat = vcat[gd]

        symbol = 'o'
        symsz = 70

        ax1.scatter(vh17, vh17-vcat['vheliobary'], marker=symbol, c=vcat['hmag'], cmap='gnuplot', s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        ax2.scatter(teff17/1000, teff17/1000-vcat['rv_teff']/1000, marker=symbol, c=vcat['hmag'], cmap='gnuplot', s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        ax3.scatter(logg17, logg17-vcat['rv_logg'], marker=symbol, c=vcat['hmag'], cmap='gnuplot', s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        ax4.scatter(feh17, feh17-vcat['rv_feh'], marker=symbol, c=vcat['hmag'], cmap='gnuplot', s=symsz, edgecolors='k', alpha=0.75, zorder=10)

        #for i in range(nv):
        #    gd,=np.where(vcat['apogee_id'][i] == allv['APOGEE_ID'])
        #    if len(gd) > 0:
        #        dif = allv['VHELIO_AVG'][gd][0] - vcat['vheliobary'][i]
        #        if np.absolute(dif) > 5: print(vcat['apogee_id'][i] + str("%.3f" % round(dif, 3)).rjust(10))
        #        symbol = 'o'
        #        symsz = 70
        #        symc = 'cyan'
        #        sb, = np.where(vcat['apogee_id'][i] == sbs)
        #        if len(sb) > 0:
        #            symbol = '*'
        #            symsz = 140
        #            symc = 'orange'
        #        ax1.scatter(allv['VHELIO_AVG'][gd][0], vcat['vheliobary'][i], marker=symbol, c=symc, s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        #        ax2.scatter(allv['RV_TEFF'][gd][0]/1000, vcat['rv_teff'][i]/1000, marker=symbol, c=symc, s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        #        ax3.scatter(allv['RV_LOGG'][gd][0], vcat['rv_logg'][i], marker=symbol, c=symc, s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        #        ax4.scatter(allv['RV_FEH'][gd][0], vcat['rv_feh'][i], marker=symbol, c=symc, s=symsz, edgecolors='k', alpha=0.75, zorder=10)


        fig.subplots_adjust(left=0.08,right=0.93,bottom=0.055,top=0.96,hspace=0.2,wspace=0.1)
        plt.savefig(plotfile)
        plt.close('all')

        return

        ###########################################################################################
        # rvparams.png
        # Plot of stellar parameters, plate vs. FPS
        allvpath = '/uufs/chpc.utah.edu/common/home/sdss40/apogeework/apogee/spectro/aspcap/dr17/synspec/allStarLite-dr17-synspec.fits'
        allv = fits.getdata(allvpath)

        fields = np.array(['18956', '19106', '19092'])
        plates = np.array(['1917', '2573', '2649'])
        mjds = np.array(['59595', '59601', '59602'])
        ind = 2

        sbs = np.array(['2M08182323+4616076', '2M08174272+4648176', '2M08121440+4634381', '2M08195933+4749123'])

        plotfile = specdir5 + 'monitor/' + instrument + '/rvparams-' + fields[ind] + '-' + plates[ind] + '-' + mjds[ind] + '.png'
        print("----> monitor: Making " + os.path.basename(plotfile))

        # DB query for this visit
        db = apogeedb.DBSession()
        vcat = db.query('visit_latest', where="plate='" + plates[ind] + "' and mjd='" + mjds[ind] + "'", fmt='table')
        gd, = np.where(vcat['snr'] > 20)
        vcat = vcat[gd]
        nv = len(vcat)

        fig = plt.figure(figsize=(22,18))
        ax1 = plt.subplot2grid((2,2), (0,0))
        ax2 = plt.subplot2grid((2,2), (0,1))
        ax3 = plt.subplot2grid((2,2), (1,0))
        ax4 = plt.subplot2grid((2,2), (1,1))
        axes = [ax1,ax2,ax3,ax4]
        ax1.set_xlim(-140, 140)
        ax1.set_ylim(-140, 140)
        ax2.set_xlim(3.0, 9.5)
        ax2.set_ylim(3.0, 9.5)
        ax3.set_xlim(0.5, 5.5)
        ax3.set_ylim(0.5, 5.5)
        ax4.set_xlim(-2.5, 1.0)
        ax4.set_ylim(-2.5, 1.0)
        ax1.set_xlabel(r'DR17 $V_{\rm helio}$ (km$\,$s$^{-1}$)')
        ax1.set_ylabel(r'FPS $V_{\rm helio}$ (km$\,$s$^{-1}$)')
        ax2.set_xlabel(r'DR17 RV $T_{\rm eff}$ (kK)')
        ax2.set_ylabel(r'FPS RV $T_{\rm eff}$ (kK)')
        ax3.set_xlabel(r'DR17 RV log$\,g$')
        ax3.set_ylabel(r'FPS RV log$\,g$')
        ax4.set_xlabel(r'DR17 RV [Fe/H]')
        ax4.set_ylabel(r'FPS RV [Fe/H]')
        ax1.plot([-140,140], [-140,140], linestyle='dashed', color='k', zorder=1)
        ax2.plot([3.0,9.5], [3.0,9.5], linestyle='dashed', color='k', zorder=1)
        ax3.plot([0.5,5.5], [0.5,5.5], linestyle='dashed', color='k', zorder=1)
        ax4.plot([-2.5,1.0], [-2.5,1.0], linestyle='dashed', color='k', zorder=1)
        ax1.xaxis.set_major_locator(ticker.MultipleLocator(50))
        ax1.yaxis.set_major_locator(ticker.MultipleLocator(50))
        ax4.xaxis.set_major_locator(ticker.MultipleLocator(1.0))
        ax4.yaxis.set_major_locator(ticker.MultipleLocator(1.0))
        tmp = 'field: ' + fields[ind] + '    plate: ' + plates[ind] + '    mjd: ' + mjds[ind]
        ax1.text(1.05, 1.03, tmp, transform=ax1.transAxes, ha='center')
        for ax in axes:
            ax.minorticks_on()
            ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
            ax.tick_params(axis='both',which='major',length=axmajlen)
            ax.tick_params(axis='both',which='minor',length=axminlen)
            ax.tick_params(axis='both',which='both',width=axwidth)
            #ax.plot([-100,100000], [-100,100000], linestyle='dashed', color='k')

        vh17 = np.zeros(nv)
        teff17 = np.zeros(nv)
        logg17 = np.zeros(nv)
        feh17 = np.zeros(nv)
        for i in range(nv):
            gd,=np.where(vcat['apogee_id'][i] == allv['APOGEE_ID'])
            if len(gd) > 0:
                vh17[i] = allv['VHELIO_AVG'][gd][0]
                teff17[i] = allv['RV_TEFF'][gd][0]
                logg17[i] = allv['RV_LOGG'][gd][0]
                feh17[i] = allv['RV_FEH'][gd][0]

        gd, = np.where(teff17 > 0)
        vh17 = vh17[gd]
        teff17 = teff17[gd]
        logg17 = logg17[gd]
        feh17 = feh17[gd]
        vcat = vcat[gd]

        symbol = 'o'
        symsz = 70

        ax1.scatter(vh17, vcat['vheliobary'], marker=symbol, c=vcat['hmag'], cmap='gnuplot', s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        ax2.scatter(teff17/1000, vcat['rv_teff']/1000, marker=symbol, c=vcat['hmag'], cmap='gnuplot', s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        ax3.scatter(logg17, vcat['rv_logg'], marker=symbol, c=vcat['hmag'], cmap='gnuplot', s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        ax4.scatter(feh17, vcat['rv_feh'], marker=symbol, c=vcat['hmag'], cmap='gnuplot', s=symsz, edgecolors='k', alpha=0.75, zorder=10)

        #for i in range(nv):
        #    gd,=np.where(vcat['apogee_id'][i] == allv['APOGEE_ID'])
        #    if len(gd) > 0:
        #        dif = allv['VHELIO_AVG'][gd][0] - vcat['vheliobary'][i]
        #        if np.absolute(dif) > 5: print(vcat['apogee_id'][i] + str("%.3f" % round(dif, 3)).rjust(10))
        #        symbol = 'o'
        #        symsz = 70
        #        symc = 'cyan'
        #        sb, = np.where(vcat['apogee_id'][i] == sbs)
        #        if len(sb) > 0:
        #            symbol = '*'
        #            symsz = 140
        #            symc = 'orange'
        #        ax1.scatter(allv['VHELIO_AVG'][gd][0], vcat['vheliobary'][i], marker=symbol, c=symc, s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        #        ax2.scatter(allv['RV_TEFF'][gd][0]/1000, vcat['rv_teff'][i]/1000, marker=symbol, c=symc, s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        #        ax3.scatter(allv['RV_LOGG'][gd][0], vcat['rv_logg'][i], marker=symbol, c=symc, s=symsz, edgecolors='k', alpha=0.75, zorder=10)
        #        ax4.scatter(allv['RV_FEH'][gd][0], vcat['rv_feh'][i], marker=symbol, c=symc, s=symsz, edgecolors='k', alpha=0.75, zorder=10)


        fig.subplots_adjust(left=0.08,right=0.93,bottom=0.055,top=0.96,hspace=0.2,wspace=0.2)
        plt.savefig(plotfile)
        plt.close('all')

        return

        ###########################################################################################
        # snhistory.png
        plotfile = specdir5 + 'monitor/' + instrument + '/snhistory.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))

            gd, = np.where(allsci['EXPTIME'] > 0)
            gdcal = allsci[gd]
            caljd = gdcal['MJD']# - 2.4e6

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                #ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'MJD')
                ax.set_ylabel(r'S/N per minute')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                #for iyear in range(nyears):
                #    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                #    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

                yvals = (gdcal['SN'][:, ichip]**2)  / gdcal['EXPTIME'] / 60
                ax.scatter(caljd, yvals, marker='o', s=markersz)#, c=colors[ifib], alpha=alf)#, label='Fiber ' + str(fibers[ifib]))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                #if ichip == 0: 
                #    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                #              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        return

        ###########################################################################################
        # snrFPS.png
        plotfile = specdir5 + 'monitor/' + instrument + '/snrFPS.png'
        print("----> monitor: Making " + os.path.basename(plotfile))

        ssdir = specdir5 + 'visit/apo25m/'
        fields = np.array(['18956', '19106', '19092', '20914', '20916', '20918'])
        plates = np.array(['1917', '2573', '2649', '3211', '3213', '3216'])
        mjds = np.array(['59595', '59601', '59602', '59619', '59619', '59619'])
        nfps = len(mjds)
        compfield = 'RM_XMM-LSS'
        compplate = '15002'
        compdir = ssdir + compfield + '/' + compplate + '/'
        compsumfiles = glob.glob(compdir + '59*/apPlateSum-*fits')
        compsumfiles.sort()
        compsumfiles = np.array(compsumfiles)
        ncomp = len(compsumfiles)

        xarr = np.arange(0, 300, 1) + 1

        fig = plt.figure(figsize=(30,16))

        ax = plt.subplot2grid((1,1), (0,0))
        ax.set_xlim(6,14)
        #ax.set_ylim(-1.1, 1.1)
        ax.minorticks_on()
        ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.5))
        #ax.yaxis.set_major_locator(ticker.MultipleLocator(0.5))
        #ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.1))
        ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
        ax.tick_params(axis='both',which='major',length=axmajlen)
        ax.tick_params(axis='both',which='minor',length=axminlen)
        ax.tick_params(axis='both',which='both',width=axwidth)
        ax.set_xlabel(r'H mag')
        ax.set_ylabel(r'S/N$^{2}$ per minute')
        #ax.axes.xaxis.set_ticklabels([])

        for icomp in range(ncomp):
            d1 = fits.open(compsumfiles[icomp])[1].data
            d2 = fits.open(compsumfiles[icomp])[2].data
            sci, = np.where(d2['objtype'] != 'SKY')
            d2 = d2[sci]
            exptimes = d1['exptime']
            nexp = len(exptimes)
            for iexp in range(nexp):
                sn2perMinute = d2['sn'][:, iexp, 1]**2 / exptimes[iexp] / 60
                sn2perMinute = d2['sn'][:, iexp, 1] / exptimes[iexp] / 60# / 60
                #ax.scatter(d2['hmag'], sn2perMinute, marker='o', s=80, color='cyan', edgecolors='k')
                ax.semilogy(d2['hmag'], sn2perMinute, marker='o', ms=9, mec='k', alpha=0.7, mfc='dodgerblue', linestyle='')
                #ax.plot(d2['hmag'], sn2perMinute)#, marker='o', s=80, color='cyan', edgecolors='k')

        for ifps in range(nfps):
            dfile = ssdir + fields[ifps] + '/' + plates[ifps] + '/' + mjds[ifps] + '/apPlateSum-' + plates[ifps] + '-' + mjds[ifps] + '.fits'
            d1 = fits.open(dfile)[1].data
            d2 = fits.open(dfile)[2].data
            sci, = np.where(d2['objtype'] != 'SKY')
            d2 = d2[sci]
            exptimes = d1['exptime']
            nexp = len(exptimes)
            for iexp in range(nexp):
                sn2perMinute = d2['sn'][:, iexp, 1]**2 / exptimes[iexp] / 60
                sn2perMinute = d2['sn'][:, iexp, 1] / exptimes[iexp] / 60# / 60
                #ax.scatter(d2['hmag'], sn2perMinute, marker='o', s=80, color='cyan', edgecolors='k')
                ax.semilogy(d2['hmag'], sn2perMinute, marker='o', ms=9, mec='k', alpha=0.7, mfc='r', linestyle='')
                #ax.plot(d2['hmag'], sn2perMinute)#, marker='o', s=80, color='cyan', edgecolors='k')


        fig.subplots_adjust(left=0.05,right=0.95,bottom=0.06,top=0.955,hspace=0.08,wspace=0.00)
        plt.savefig(plotfile)
        plt.close('all')

        return

        ###########################################################################################
        # wavelengths.png
        # Plot of starting/ending wavelength of each detector
        plate = '2620'
        field = '16196'
        mjd = '59602'
        plate = '3130'
        field = '20906'
        mjd = '59616'
        plotfile = specdir5 + 'monitor/' + instrument + '/wavelengths-' + field + '-' + plate + '-' + mjd + '.png'
        print("----> monitor: Making " + os.path.basename(plotfile))
        sdir = specdir5 + 'visit/apo25m/' + field + '/' + plate + '/' + mjd + '/'
        plfiles = glob.glob(sdir + 'apPlate-*fits')
        plfiles.sort()
        plfiles = np.array(plfiles)[::-1]
        xarr = np.arange(0, 300, 1) + 1

        fig = plt.figure(figsize=(30,14))

        for ichip in range(nchips):
            chip = chips[ichip]
            ax = plt.subplot2grid((nchips,1), (ichip,0))
            ax.set_xlim(0, 300)
            ax1 = ax.twinx()
            ax.set_ylim(-1.1, 1.1)
            ax1.set_ylim(-1.1, 1.1)
            ax.minorticks_on()
            ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
            ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
            ax1.xaxis.set_major_locator(ticker.MultipleLocator(20))
            ax1.xaxis.set_minor_locator(ticker.MultipleLocator(1))
            ax.yaxis.set_major_locator(ticker.MultipleLocator(0.5))
            ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.1))
            ax1.yaxis.set_major_locator(ticker.MultipleLocator(0.5))
            ax1.yaxis.set_minor_locator(ticker.MultipleLocator(0.1))
            ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
            ax.tick_params(axis='both',which='major',length=axmajlen)
            ax.tick_params(axis='both',which='minor',length=axminlen)
            ax.tick_params(axis='both',which='both',width=axwidth)
            if ichip == nchips-1: ax.set_xlabel(r'Fiber ID')
            if ichip < nchips-1: 
                ax.axes.xaxis.set_ticklabels([])
                ax1.axes.xaxis.set_ticklabels([])

            data = fits.open(plfiles[ichip])[4].data
            minwave = np.nanmin(data, axis=1)
            maxwave = np.nanmax(data, axis=1)
            gdmn, = np.where(minwave > 0)
            gdmx, = np.where(maxwave > 0)
            meanminwave = np.nanmean(minwave[gdmn])
            meanmaxwave = np.nanmean(maxwave[gdmx])
            minminwave = np.nanmin(minwave[gdmn])
            maxminwave = np.nanmax(minwave[gdmn])
            minmaxwave = np.nanmin(maxwave[gdmx])
            maxmaxwave = np.nanmax(maxwave[gdmx])
            ax.axhline(y=0, linestyle='dashed', color='k')
            ax.scatter(xarr[gdmn], minwave[gdmn]-meanminwave, marker='>', s=markersz*3, c='k', alpha=alf)
            ax1.scatter(xarr[gdmx], maxwave[gdmx]-meanmaxwave, marker='<', s=markersz*3, c='r', alpha=alf)

            ax.set_ylabel(r'$\lambda-$mean $\lambda$ ($\rm \AA$)')
            ax1.set_ylabel(r'$\lambda-$mean $\lambda$ ($\rm \AA$)')

            p1 = str("%.3f" % round(meanminwave, 3))
            p2 = str("%.3f" % round(minminwave, 3))
            p3 = str("%.3f" % round(maxminwave, 3))
            p4 = str("%.3f" % round(maxminwave-minminwave, 3))
            lab1 = r'Start $\lambda$ (mean = ' + p1 + r', min = ' + p2 + r', max = ' + p3 + r', max$-$min = ' + p4 + ')'
            p1 = str("%.3f" % round(meanmaxwave, 3))
            p2 = str("%.3f" % round(minmaxwave, 3))
            p3 = str("%.3f" % round(maxmaxwave, 3))
            p4 = str("%.3f" % round(maxmaxwave-minmaxwave, 3))
            lab2 = r'Stop $\lambda$  (mean = ' + p1 + r', min = ' + p2 + r', max = ' + p3 + r', max$-$min = ' + p4 + ')'
            ax.scatter(xarr[gdmn][0]-500, minwave[gdmn][0]-meanminwave, marker='>', s=markersz*3, c='k', label=lab1)
            ax.scatter(xarr[gdmx][0]-500, maxwave[gdmx][0]+meanmaxwave, marker='<', s=markersz*3, c='r', label=lab2)
            ax.text(0.97,0.08,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                    ha='center', va='bottom', color=chip, bbox=bboxpar)
            ax.legend(loc='upper left', labelspacing=0.5, handletextpad=-0.1, markerscale=3, 
                      edgecolor='k', framealpha=1, fontsize=fsz*1.1)

            if ichip == 0:
                tmp = 'field: ' + field + '    plate: ' + plate + '    mjd: ' + mjd
                ax.text(0.5, 1.03, tmp, transform=ax.transAxes, ha='center')

        fig.subplots_adjust(left=0.05,right=0.95,bottom=0.06,top=0.955,hspace=0.08,wspace=0.00)
        plt.savefig(plotfile)
        plt.close('all')

        return

        ###########################################################################################
        # qtrace.png
        # Time series plot of median dome flat flux from cross sections across fibers
        plotfile = specdir5 + 'monitor/' + instrument + '/qtrace.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            gfibers = np.array([10, 45, 80, 115, 150, 185, 220, 255, 290])[::-1]
            gcolors = np.array(['midnightblue', 'deepskyblue', 'mediumorchid', 'red', 'orange', 'magenta', 'darkgreen', 'limegreen', 'maroon'])[::-1]
            #gfibers = np.array([0, 49, 99, 149, 199, 249, 299])[::-1]
            ngplotfibs = len(gfibers)

            fig = plt.figure(figsize=(30,14))
            ymax = 2.8
            ymin = -2.8
            yspan = ymax - ymin
            dtrace = fits.getdata(specdir5 + 'monitor/' + instrument + 'QuartzFlatTrace-all.fits')
            gd, = np.where((dtrace['MJD'] > 1000) & (dtrace['GAUSS_NPEAKS'][:,1] > 280))
            gdtrace = dtrace[gd]
            gcent = gdtrace['GAUSS_CENT'][:,:,gfibers]
            xvals = gdtrace['MJD']

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                if ichip == 1: ax.set_ylabel(r'Quartz Lamp Trace Position Residuals (pixels)')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)
                ax.axhline(y=0, color='k', linestyle='dashed', alpha=alf)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

                for ifib in range(ngplotfibs):
                    medcent = np.nanmedian(gcent[:, ichip, ifib])
                    yvals = gcent[:, ichip, ifib] - medcent
                    ax.scatter(xvals, yvals, marker='o', s=markersz, c=gcolors[ifib], alpha=alf, 
                               label='fib ' + str(gfibers[ifib]))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz*0.8, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.04,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # dflattrace.png
        # Time series plot of median dome flat flux from cross sections across fibers
        plotfile = specdir5 + 'monitor/' + instrument + '/dflattrace.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))
            ymax = 2.8
            ymin = -2.8
            yspan = ymax - ymin
            dtrace = fits.getdata(specdir5 + 'monitor/' + instrument + 'DomeFlatTrace-all.fits')
            gd, = np.where((dtrace['MJD'] > 1000) & (dtrace['GAUSS_NPEAKS'][:,1] > 280))
            gdtrace = dtrace[gd]
            gcent = gdtrace['GAUSS_CENT'][:,:,gfibers]
            xvals = gdtrace['MJD']

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                if ichip == 1: ax.set_ylabel(r'Dome Flat Trace Position Residuals (pixels)')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)
                ax.axhline(y=0, color='k', linestyle='dashed', alpha=alf)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

                for ifib in range(ngplotfibs):
                    medcent = np.nanmedian(gcent[:, ichip, ifib])
                    yvals = gcent[:, ichip, ifib] - medcent
                    ax.scatter(xvals, yvals, marker='o', s=markersz, c=gcolors[ifib], alpha=alf, 
                               label='fib ' + str(gfibers[ifib]))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz*0.8, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.04,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        #pdb.set_trace()
        return 

        ###########################################################################################
        # dillum_FPSonly.png
        # Time series plot of median dome flat flux from cross sections across fibers
        plotfile = specdir5 + 'monitor/' + instrument + '/dillum_FPSonly.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,22))
            xarr = np.arange(0, 300, 1) + 1

            mjdstart = 59599
            coltickval = 5
            if mjdstart> 59590: coltickval = 2
            gd, = np.where((allexp[dome]['MJD'] >= mjdstart) & (allexp[dome]['MJD'] != 59557) & (allexp[dome]['MJD'] != 59566))
            gdcal = allexp[dome][gd]
            umjd = gdcal['MJD']
            ndome = len(gdcal)

            mycmap = 'inferno_r'
            mycmap = 'brg_r'
            cmap = cmaps.get_cmap(mycmap, ndome)
            sm = cmaps.ScalarMappable(cmap=mycmap, norm=plt.Normalize(vmin=np.min(umjd), vmax=np.max(umjd)))

            for ichip in range(nchips):
                chip = chips[ichip]
                ax = plt.subplot2grid((nchips, 1), (ichip, 0))
                ax.set_xlim(0, 301)
                #ax.set_ylim(0, 27000)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
                ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'Fiber Index')
                ax.set_ylabel(r'Median Flux')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                if ichip == 0:
                    ax_divider = make_axes_locatable(ax)
                    cax = ax_divider.append_axes("top", size="7%", pad="2%")
                    cb = plt.colorbar(sm, cax=cax, orientation="horizontal")
                    cax.xaxis.set_ticks_position("top")
                    #cax.minorticks_on()
                    cax.xaxis.set_major_locator(ticker.MultipleLocator(coltickval))
                    #cax.xaxis.set_minor_locator(ticker.MultipleLocator(10))
                    cax.xaxis.set_label_position('top') 
                    cax.set_xlabel('MJD')

                for idome in range(ndome):
                    chp = 'c'
                    if ichip == 1: chp = 'b'
                    if ichip == 2: chp = 'a'
                    file1d = load.filename('1D', mjd=str(umjd[idome]), num=gdcal['NUM'][idome], chips='c')
                    file1d = file1d.replace('1D-', '1D-' + chp + '-')
                    if os.path.exists(file1d):
                        hdr = fits.getheader(file1d)
                        oned = fits.getdata(file1d)
                        onedflux = np.nanmedian(oned, axis=1)[::-1]
                        print(str(umjd[idome])+'   '+str(gdcal['NUM'][idome])+'   '+str(int(round(np.max(onedflux))))+'  expt='+str(int(round(hdr['exptime'])))+'  nread='+str(hdr['nread']))
                        if (umjd[idome] == 59557) | (umjd[idome] == 59566): continue
                        mycolor = cmap(idome)
                        #gd, = np.where(onedflux > 100)
                        ax.plot(xarr, onedflux, color=mycolor)
                        #if (chp == 'c') & (np.nanmax(onedflux) > 30000): pdb.set_trace()
                        #ax.hist(onedflux, 300, color=mycolor, fill=False)

                ax.text(0.97,0.94,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)

            fig.subplots_adjust(left=0.06,right=0.985,bottom=0.045,top=0.955,hspace=0.08,wspace=0.1)
            plt.savefig(plotfile)
            plt.close('all')

        #pdb.set_trace()
        #return 

        ###########################################################################################
        # apflux_chipsmean.png
        # Time series plot of median apFlux flux
        plotfile = specdir5 + 'monitor/' + instrument + '/apflux_chipsmean.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,16))
            xarr = np.arange(0, 300, 1) + 1

            flxfiles = glob.glob(specdir5 + 'cal/apogee-n/flux/apFlux-c*fits')
            flxfiles.sort()
            flxfiles = np.array(flxfiles)
            flxfiles = flxfiles[1:]
            nflx = len(flxfiles)

            expstart = int(flxfiles[0].split('-c-')[1].split('.')[0])
            mjdstart = int((expstart - expstart % 10000 ) / 10000) + 55562
            expstop  = int(flxfiles[-1:][0].split('-c-')[1].split('.')[0])
            mjdstop  = int((expstop - expstop % 10000 ) / 10000) + 55562

            mycmap = 'gist_stern_r'
            cmap = cmaps.get_cmap(mycmap, nflx)
            sm = cmaps.ScalarMappable(cmap=mycmap, norm=plt.Normalize(vmin=mjdstart, vmax=mjdstop))

            ax = plt.subplot2grid((1, 1), (0, 0))
            ax.set_xlim(0, 301)
            #ax.set_ylim(0, 1.4)
            ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
            ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
            ax.minorticks_on()
            ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
            ax.tick_params(axis='both',which='major',length=axmajlen)
            ax.tick_params(axis='both',which='minor',length=axminlen)
            ax.tick_params(axis='both',which='both',width=axwidth)
            ax.set_xlabel(r'Fiber Index')
            ax.set_ylabel(r'apFlux Median Flux (mean across chips)')
            ax_divider = make_axes_locatable(ax)
            cax = ax_divider.append_axes("top", size="7%", pad="2%")
            cb = plt.colorbar(sm, cax=cax, orientation="horizontal")
            cax.xaxis.set_ticks_position("top")
            cax.minorticks_on()
            cax.xaxis.set_major_locator(ticker.MultipleLocator(50))
            cax.xaxis.set_minor_locator(ticker.MultipleLocator(10))
            cax.xaxis.set_label_position('top') 
            cax.set_xlabel('MJD')

            for iflx in range(nflx):
                print(iflx)
                expnum = int(flxfiles[iflx].split('-c-')[1].split('.')[0])
                d0 = load.apFlux(expnum)
                y1 = np.nanmedian(d0['a'][1].data[:, 824:1224], axis=1)[::-1]
                y2 = np.nanmedian(d0['b'][1].data[:, 824:1224], axis=1)[::-1]
                y3 = np.nanmedian(d0['c'][1].data[:, 824:1224], axis=1)[::-1]
                yall = np.nanmean(np.array([y1,y2,y3]), axis=0)
                if np.nanmax(np.nanmedian(d0['a'][1].data, axis=1)[::-1]) > 2: continue
                mycolor = cmap(iflx)
                ax.plot(xarr, yall, color=mycolor)

            fig.subplots_adjust(left=0.06,right=0.985,bottom=0.065,top=0.935,hspace=0.08,wspace=0.1)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # apflux_chipsmean_FPSonly.png
        # Time series plot of median apFlux flux
        plotfile = specdir5 + 'monitor/' + instrument + '/apflux_chipsmean_FPSonly.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,16))
            xarr = np.arange(0, 300, 1) + 1

            flxfiles = glob.glob(specdir5 + 'cal/apogee-n/flux/apFlux-c*fits')
            flxfiles.sort()
            flxfiles = np.array(flxfiles)
            flxfiles = flxfiles[1257:]
            nflx = len(flxfiles)

            expstart = int(flxfiles[0].split('-c-')[1].split('.')[0])
            mjdstart = int((expstart - expstart % 10000 ) / 10000) + 55562
            expstop  = int(flxfiles[-1:][0].split('-c-')[1].split('.')[0])
            mjdstop  = int((expstop - expstop % 10000 ) / 10000) + 55562

            mycmap = 'brg_r'
            cmap = cmaps.get_cmap(mycmap, nflx)
            sm = cmaps.ScalarMappable(cmap=mycmap, norm=plt.Normalize(vmin=mjdstart, vmax=mjdstop))

            ax = plt.subplot2grid((1, 1), (0, 0))
            ax.set_xlim(0, 301)
            #ax.set_ylim(0, 1.4)
            ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
            ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
            ax.minorticks_on()
            ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
            ax.tick_params(axis='both',which='major',length=axmajlen)
            ax.tick_params(axis='both',which='minor',length=axminlen)
            ax.tick_params(axis='both',which='both',width=axwidth)
            ax.set_xlabel(r'Fiber Index')
            ax.set_ylabel(r'apFlux Median Flux (mean across chips)')
            ax_divider = make_axes_locatable(ax)
            cax = ax_divider.append_axes("top", size="7%", pad="2%")
            cb = plt.colorbar(sm, cax=cax, orientation="horizontal")
            cax.xaxis.set_ticks_position("top")
            cax.minorticks_on()
            cax.xaxis.set_major_locator(ticker.MultipleLocator(5))
            cax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
            cax.xaxis.set_label_position('top') 
            cax.set_xlabel('MJD')

            for iflx in range(nflx):
                print(iflx)
                expnum = int(flxfiles[iflx].split('-c-')[1].split('.')[0])
                d0 = load.apFlux(expnum)
                y1 = np.nanmedian(d0['a'][1].data[:, 824:1224], axis=1)[::-1]
                y2 = np.nanmedian(d0['b'][1].data[:, 824:1224], axis=1)[::-1]
                y3 = np.nanmedian(d0['c'][1].data[:, 824:1224], axis=1)[::-1]
                yall = np.nanmean(np.array([y1,y2,y3]), axis=0)
                if np.nanmax(np.nanmedian(d0['a'][1].data, axis=1)[::-1]) > 2: continue
                mycolor = cmap(iflx)
                ax.plot(xarr, yall, color=mycolor)

            fig.subplots_adjust(left=0.06,right=0.985,bottom=0.065,top=0.935,hspace=0.08,wspace=0.1)
            plt.savefig(plotfile)
            plt.close('all')

        return

        ###########################################################################################
        # apflux_FPSonly.png
        # Time series plot of median apFlux flux
        plotfile = specdir5 + 'monitor/' + instrument + '/apflux_FPSonly.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,22))
            xarr = np.arange(0, 300, 1) + 1

            flxfiles = glob.glob(specdir5 + 'cal/apogee-n/flux/apFlux-c*fits')
            flxfiles.sort()
            flxfiles = np.array(flxfiles)
            flxfiles = flxfiles[1257:]
            nflx = len(flxfiles)

            expstart = int(flxfiles[0].split('-c-')[1].split('.')[0])
            mjdstart = int((expstart - expstart % 10000 ) / 10000) + 55562
            expstop  = int(flxfiles[-1:][0].split('-c-')[1].split('.')[0])
            mjdstop  = int((expstop - expstop % 10000 ) / 10000) + 55562

            mycmap = 'brg_r'
            cmap = cmaps.get_cmap(mycmap, nflx)
            sm = cmaps.ScalarMappable(cmap=mycmap, norm=plt.Normalize(vmin=mjdstart, vmax=mjdstop))

            ax1 = plt.subplot2grid((nchips, 1), (0, 0))
            ax2 = plt.subplot2grid((nchips, 1), (1, 0))
            ax3 = plt.subplot2grid((nchips, 1), (2, 0))
            axes = [ax1,ax2,ax3]
            ichip = 0
            for ax in axes:
                chip = chips[ichip]
                ax.set_xlim(0, 301)
                ax.set_ylim(0, 1.4)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
                ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'Fiber Index')
                ax.set_ylabel(r'apFlux Median Flux')
                ax.text(0.97,0.94,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                if ichip == 0:
                    ax_divider = make_axes_locatable(ax)
                    cax = ax_divider.append_axes("top", size="7%", pad="2%")
                    cb = plt.colorbar(sm, cax=cax, orientation="horizontal")
                    cax.xaxis.set_ticks_position("top")
                    cax.minorticks_on()
                    cax.xaxis.set_major_locator(ticker.MultipleLocator(5))
                    cax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
                    cax.xaxis.set_label_position('top') 
                    cax.set_xlabel('MJD')
                ichip += 1

            for iflx in range(nflx):
                expnum = int(flxfiles[iflx].split('-c-')[1].split('.')[0])
                d0 = load.apFlux(expnum)
                print(iflx)
                if np.nanmax(np.nanmedian(d0['a'][1].data, axis=1)[::-1]) > 4: continue
                ichip = 0
                for ax in axes:
                    chp = 'c'
                    if ichip == 1: chp = 'b'
                    if ichip == 2: chp = 'a'
                    mycolor = cmap(iflx)
                    yarr = np.nanmedian(d0[chp][1].data, axis=1)[::-1]
                    ax.plot(xarr, yarr, color=mycolor)
                    ichip += 1

            fig.subplots_adjust(left=0.06,right=0.985,bottom=0.045,top=0.955,hspace=0.08,wspace=0.1)
            plt.savefig(plotfile)
            plt.close('all')

        #return

        ###########################################################################################
        # apflux.png
        # Time series plot of median apFlux flux
        plotfile = specdir5 + 'monitor/' + instrument + '/apflux.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,22))
            xarr = np.arange(0, 300, 1) + 1

            flxfiles = glob.glob(specdir5 + 'cal/apogee-n/flux/apFlux-c*fits')
            flxfiles.sort()
            flxfiles = np.array(flxfiles)
            flxfiles = flxfiles[1:]
            nflx = len(flxfiles)

            expstart = int(flxfiles[0].split('-c-')[1].split('.')[0])
            mjdstart = int((expstart - expstart % 10000 ) / 10000) + 55562
            expstop  = int(flxfiles[-1:][0].split('-c-')[1].split('.')[0])
            mjdstop  = int((expstop - expstop % 10000 ) / 10000) + 55562

            mycmap = 'gist_stern_r'
            cmap = cmaps.get_cmap(mycmap, nflx)
            sm = cmaps.ScalarMappable(cmap=mycmap, norm=plt.Normalize(vmin=mjdstart, vmax=mjdstop))

            ax1 = plt.subplot2grid((nchips, 1), (0, 0))
            ax2 = plt.subplot2grid((nchips, 1), (1, 0))
            ax3 = plt.subplot2grid((nchips, 1), (2, 0))
            axes = [ax1,ax2,ax3]
            ichip = 0
            for ax in axes:
                chip = chips[ichip]
                ax.set_xlim(0, 301)
                ax.set_ylim(0, 4)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
                ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'Fiber Index')
                ax.set_ylabel(r'apFlux Median Flux')
                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                if ichip == 0:
                    ax_divider = make_axes_locatable(ax)
                    cax = ax_divider.append_axes("top", size="7%", pad="2%")
                    cb = plt.colorbar(sm, cax=cax, orientation="horizontal")
                    cax.xaxis.set_ticks_position("top")
                    cax.minorticks_on()
                    cax.xaxis.set_major_locator(ticker.MultipleLocator(50))
                    cax.xaxis.set_minor_locator(ticker.MultipleLocator(10))
                    cax.xaxis.set_label_position('top') 
                    cax.set_xlabel('MJD')
                ichip += 1

            for iflx in range(nflx):
                expnum = int(flxfiles[iflx].split('-c-')[1].split('.')[0])
                d0 = load.apFlux(expnum)
                print(iflx)
                if np.nanmax(np.nanmedian(d0['a'][1].data, axis=1)[::-1]) > 4: continue
                ichip = 0
                for ax in axes:
                    chp = 'c'
                    if ichip == 1: chp = 'b'
                    if ichip == 2: chp = 'a'
                    mycolor = cmap(iflx)
                    yarr = np.nanmedian(d0[chp][1].data, axis=1)[::-1]
                    ax.plot(xarr, yarr, color=mycolor)
                    ichip += 1

            fig.subplots_adjust(left=0.06,right=0.985,bottom=0.045,top=0.955,hspace=0.08,wspace=0.1)
            plt.savefig(plotfile)
            plt.close('all')

        return



        ###########################################################################################
        # dillum1.png
        # Time series plot of median dome flat flux from cross sections across fibers
        plotfile = specdir5 + 'monitor/' + instrument + '/dillum1.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,22))
            xarr = np.arange(0, 300, 1) + 1

            #umjd, uind = np.unique(allexp[dome]['MJD'], return_index=True)
            #gdcal = allexp[dome][uind]
            gd, = np.where(allexp[dome]['MJD'] >= 59247)
            gdcal = allexp[dome][gd]
            umjd = gdcal['MJD']
            ndome = len(gdcal)

            mycmap = 'inferno_r'
            cmap = cmaps.get_cmap(mycmap, ndome)
            sm = cmaps.ScalarMappable(cmap=mycmap, norm=plt.Normalize(vmin=np.min(umjd), vmax=np.max(umjd)))

            for ichip in range(nchips):
                chip = chips[ichip]
                ax = plt.subplot2grid((nchips, 1), (ichip, 0))
                ax.set_xlim(0, 301)
                #ax.set_ylim(0, 27000)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
                ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'Fiber Index')
                ax.set_ylabel(r'Median Flux')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                if ichip == 0:
                    ax_divider = make_axes_locatable(ax)
                    cax = ax_divider.append_axes("top", size="7%", pad="2%")
                    cb = plt.colorbar(sm, cax=cax, orientation="horizontal")
                    cax.xaxis.set_ticks_position("top")
                    cax.minorticks_on()
                    cax.xaxis.set_major_locator(ticker.MultipleLocator(50))
                    cax.xaxis.set_minor_locator(ticker.MultipleLocator(10))
                    cax.xaxis.set_label_position('top') 
                    cax.set_xlabel('MJD')

                for idome in range(ndome):
                    chp = 'c'
                    if ichip == 1: chp = 'b'
                    if ichip == 2: chp = 'a'
                    file1d = load.filename('1D', mjd=str(umjd[idome]), num=gdcal['NUM'][idome], chips='c')
                    file1d = file1d.replace('1D-', '1D-' + chp + '-')
                    if os.path.exists(file1d):
                        hdr = fits.getheader(file1d)
                        oned = fits.getdata(file1d)
                        onedflux = np.nanmedian(oned, axis=1)[::-1]
                        print(str(umjd[idome])+'   '+str(int(round(np.max(onedflux))))+'  expt='+str(hdr['exptime'])+'  nread='+str(hdr['nread']))
                        if (umjd[idome] == 59557) | (umjd[idome] == 59566): continue
                        mycolor = cmap(idome)
                        gd, = np.where(onedflux > 100)
                        ax.plot(xarr[gd], onedflux[gd], color=mycolor)
                        #if (chp == 'c') & (np.nanmax(onedflux) > 30000): pdb.set_trace()
                        #ax.hist(onedflux, 300, color=mycolor, fill=False)

                ax.text(0.97,0.94,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)

            fig.subplots_adjust(left=0.06,right=0.985,bottom=0.045,top=0.955,hspace=0.08,wspace=0.1)
            plt.savefig(plotfile)
            plt.close('all')

        return

        ###########################################################################################
        # qillum59567.png
        # Time series plot of median dome flat flux from cross sections across fibers from series of 59557 flats
        #plotfile = specdir5 + 'monitor/' + instrument + '/qillum59567.png'
        #if (os.path.exists(plotfile) == False) | (clobber == True):
        #    print("----> monitor: Making " + os.path.basename(plotfile))

        #    fig = plt.figure(figsize=(30,22))
        #    xarr = np.arange(0, 300, 1) + 1

        #    gd, = np.where(allexp['MJD'][qrtzexp] == 59567)
        #    gdcal = allexp[qrtzexp][gd]
        #    nqtz = len(gdcal)
        #    #pdb.set_trace()

        #    mycmap = 'viridis_r'
        #    cmap = cmaps.get_cmap(mycmap, nqtz)
        #    sm = cmaps.ScalarMappable(cmap=mycmap, norm=plt.Normalize(vmin=1, vmax=nqtz))

        #    for ichip in range(nchips):
        #        chip = chips[ichip]
        #        ax = plt.subplot2grid((nchips, 1), (ichip, 0))
        #        ax.set_xlim(0, 301)
        #        ax.set_ylim(0, 55000)
        #        ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
        #        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
        #        ax.minorticks_on()
        #        ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
        #        ax.tick_params(axis='both',which='major',length=axmajlen)
        #        ax.tick_params(axis='both',which='minor',length=axminlen)
        #        ax.tick_params(axis='both',which='both',width=axwidth)
        #        if ichip == nchips-1: ax.set_xlabel(r'Fiber Index')
        #        ax.set_ylabel(r'Median Flux')
        #        if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
        #        if ichip == 0:
        #            ax_divider = make_axes_locatable(ax)
        #            cax = ax_divider.append_axes("top", size="7%", pad="2%")
        #            cb = plt.colorbar(sm, cax=cax, orientation="horizontal")
        #            cax.xaxis.set_ticks_position("top")
        #            #cax.minorticks_on()
        #            cax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        #            #cax.xaxis.set_minor_locator(ticker.MultipleLocator(10))
        #            cax.xaxis.set_label_position('top') 
        #            cax.set_xlabel('Exposure')

        #        for iqtz in range(nqtz):
        #            chp = 'c'
        #            if ichip == 1: chp = 'b'
        #            if ichip == 2: chp = 'a'
        #            file1d = load.filename('1D', mjd='59567', num=gdcal['NUM'][iqtz], chips='c')
        #            file1d = file1d.replace('1D-', '1D-' + chp + '-')
        #            if os.path.exists(file1d):
        #                oned = fits.getdata(file1d)
        #                onedflux = np.nanmedian(oned, axis=1)[::-1]
        #                mycolor = cmap(iqtz)
        #                gd, = np.where(onedflux > 100)
        #                ax.plot(xarr[gd], onedflux[gd], color=mycolor)
        #                #ax.hist(onedflux, 300, color=mycolor, fill=False)

        #        ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
        #                ha='center', va='top', color=chip, bbox=bboxpar)

        #    fig.subplots_adjust(left=0.06,right=0.985,bottom=0.045,top=0.955,hspace=0.08,wspace=0.1)
        #    plt.savefig(plotfile)
        #    plt.close('all')

        ###########################################################################################
        ## dillum59557.png
        ## Time series plot of median dome flat flux from cross sections across fibers from series of 59557 flats
        #plotfile = specdir5 + 'monitor/' + instrument + '/dillum59557.png'
        #if (os.path.exists(plotfile) == False) | (clobber == True):
        #    print("----> monitor: Making " + os.path.basename(plotfile))

        #    fig = plt.figure(figsize=(30,22))
        #    xarr = np.arange(0, 300, 1) + 1

        #    gd, = np.where(allexp['MJD'][dome] == 59557)
        #    gdcal = allexp[dome][gd]
        #    ndome = len(gdcal)

        #    mycmap = 'viridis_r'
        #    cmap = cmaps.get_cmap(mycmap, ndome)
        #    sm = cmaps.ScalarMappable(cmap=mycmap, norm=plt.Normalize(vmin=1, vmax=ndome))

        #    #pdb.set_trace()

        #    for ichip in range(nchips):
        #        chip = chips[ichip]
        #        ax = plt.subplot2grid((nchips, 1), (ichip, 0))
        #        ax.set_xlim(0, 301)
        #        #ax.set_ylim(0, 27000)
        #        ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
        #        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
        #        ax.minorticks_on()
        #        ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
        #        ax.tick_params(axis='both',which='major',length=axmajlen)
        #        ax.tick_params(axis='both',which='minor',length=axminlen)
        #        ax.tick_params(axis='both',which='both',width=axwidth)
        #        if ichip == nchips-1: ax.set_xlabel(r'Fiber Index')
        #        ax.set_ylabel(r'Median Flux')
        #        if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
        #        if ichip == 0:
        #            ax_divider = make_axes_locatable(ax)
        #            cax = ax_divider.append_axes("top", size="7%", pad="2%")
        #            cb = plt.colorbar(sm, cax=cax, orientation="horizontal")
        #            cax.xaxis.set_ticks_position("top")
        #            #cax.minorticks_on()
        #            cax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        #            #cax.xaxis.set_minor_locator(ticker.MultipleLocator(10))
        #            cax.xaxis.set_label_position('top') 
        #            cax.set_xlabel('Exposure')

        #        for idome in range(ndome):
        #            chp = 'c'
        #            if ichip == 1: chp = 'b'
        #            if ichip == 2: chp = 'a'
        #            file1d = load.filename('1D', mjd='59557', num=gdcal['NUM'][idome], chips='c')
        #            file1d = file1d.replace('1D-', '1D-' + chp + '-')
        #            #pdb.set_trace()
        #            if os.path.exists(file1d):
        #                oned = fits.getdata(file1d)
        #                onedflux = np.nanmedian(oned, axis=1)[::-1]
        #                mycolor = cmap(idome)
        #                gd, = np.where(onedflux > 100)
        #                ax.plot(xarr[gd], onedflux[gd], color=mycolor)
        #                #ax.hist(onedflux, 300, color=mycolor, fill=False)

        #        ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
        #                ha='center', va='top', color=chip, bbox=bboxpar)

        #    fig.subplots_adjust(left=0.06,right=0.985,bottom=0.045,top=0.955,hspace=0.08,wspace=0.1)
        #    plt.savefig(plotfile)
        #    plt.close('all')



    if makeplots is True:
        ###########################################################################################
        # sciobs.png
        plotfile = specdir5 + 'monitor/' + instrument + '/sciobs.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,12))
            ymax = 100
            ymin = 0
            yspan = ymax - ymin

            ax = plt.subplot2grid((1,1), (0,0))
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymin, ymax)
            ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
            ax.minorticks_on()
            ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
            ax.tick_params(axis='both',which='major',length=axmajlen)
            ax.tick_params(axis='both',which='minor',length=axminlen)
            ax.tick_params(axis='both',which='both',width=axwidth)
            ax.set_xlabel(r'JD - 2,400,000')
            ax.set_ylabel(r'$N_{\rm obs}$')
            ax.axvline(x=59146, color='r', linewidth=2)

            for iyear in range(nyears):
                ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                ax.text(yearjd[iyear], ymax+yspan*0.02, cyears[iyear], ha='center')

            umjd = np.unique(allsci['MJD'])
            nmjd = len(umjd)
            nexp = np.zeros(nmjd)
            nvis = np.zeros(nmjd)
            for i in range(nmjd):
                gd, = np.where(umjd[i] == allsci['MJD'])
                nexp[i] = len(gd)
                uplate = np.unique(allsci['PLATE'][gd])
                nvis[i] = len(uplate)
                if i < nmjd-1:
                    ax.plot([umjd[i],umjd[i]], [0,nexp[i]], c='k')#, label='exposures')
                    ax.plot([umjd[i],umjd[i]], [0,nvis[i]], c='dodgerblue')#, label='visits')
                else:
                    ax.plot([umjd[i],umjd[i]], [0,nexp[i]], c='k', label='exposures')
                    ax.plot([umjd[i],umjd[i]], [0,nvis[i]], c='dodgerblue', label='visits')

            #ax.scatter(umjd, nexp, marker='o', s=markersz, c='grey', alpha=alf, label='exposures')
            #ax.scatter(umjd, nvis, marker='o', s=markersz, c='teal', alpha=alf, label='visits')

            ax.legend(loc='lower right', labelspacing=0.5, handletextpad=0.3, markerscale=1, 
                      fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.04,right=0.99,bottom=0.08,top=0.94,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # qflux.png
        plotfile = specdir5 + 'monitor/' + instrument + '/qflux.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))
            ymax = 44000
            if instrument == 'apogee-s': 
                ymax = 125000
            ymin = 0 - ymax * 0.05
            yspan = ymax - ymin

            gdcal = allcal[qrtz]
            caljd = gdcal['JD'] - 2.4e6

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                ax.set_ylabel(r'Median Flux')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

                for ifib in range(nplotfibs):
                    yvals = gdcal['FLUX'][:, ichip, fibers[ifib]]  / gdcal['NREAD']*10.0
                    ax.scatter(caljd, yvals, marker='o', s=markersz, c=colors[ifib], alpha=alf, 
                               label='Fiber ' + str(fibers[ifib]))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # qfwhm.png
        plotfile = specdir5 + 'monitor/' + instrument + '/qfwhm.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))
            ymax = 3.0
            if instrument == 'apogee-s': 
                ymax = 3.0
            ymin = 0.8
            yspan = ymax - ymin

            gd, = np.where(quartztrace['MJD'] > 50000)
            qtz = quartztrace[gd]
            qmjd = qtz['MJD']
            qfwhm = qtz['GAUSS_SIGMA']*2.355

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                ax.set_ylabel(r'FWHM (pixels)')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

                for ifib in range(nplotfibs):
                    yvals = qfwhm[:, ichip, ifib]
                    ax.scatter(qmjd, yvals, marker='o', s=markersz, c=colors[ifib], alpha=alf, 
                               label='Fiber ' + str(fibers[ifib]))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # tharflux.png
        plotfile = specdir5 + 'monitor/' + instrument + '/tharflux.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))
            ymax = np.array([510000, 58000, 11000]) 
            if instrument == 'apogee-s': ymax = np.array([110000, 30000, 3000])
            ymin = 0 - ymax * 0.05
            yspan = ymax - ymin

            gdcal = allcal[thar]
            caljd = gdcal['JD']-2.4e6
            flux = gdcal['GAUSS'][:,:,:,:,0] * gdcal['GAUSS'][:,:,:,:,2]**2

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin[ichip], ymax[ichip])
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                ax.set_ylabel(r'Line Flux')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax[ichip]+yspan[ichip]*0.025, cyears[iyear], ha='center')

                for ifib in range(nplotfibs):
                    yvals = flux[:, 0, ichip, ifib] / gdcal['NREAD']*10.0
                    ax.scatter(caljd, yvals, marker='o', s=markersz, c=colors[ifib], alpha=alf, 
                               label='Fiber ' + str(fibers[ifib]))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # uneflux.png
        plotfile = specdir5 + 'monitor/' + instrument + '/uneflux.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))
            ymax = np.array([40000, 3000, 7700])
            if instrument == 'apogee-s': ymax = np.array([6000, 1500, 3000])
            ymin = 0 - ymax*0.05
            yspan = ymax - ymin

            gdcal = allcal[une]
            caljd = gdcal['JD'] - 2.4e6
            flux = gdcal['GAUSS'][:,:,:,:,0] * gdcal['GAUSS'][:,:,:,:,2]**2

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin[ichip], ymax[ichip])
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                ax.set_ylabel(r'Line Flux')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax[ichip]+yspan[ichip]*0.025, cyears[iyear], ha='center')

                for ifib in range(nplotfibs):
                    yvals = flux[:, 0, ichip, ifib] / gdcal['NREAD']*10.0
                    ax.scatter(caljd, yvals, marker='o', s=markersz, c=colors[ifib], alpha=alf, 
                               label='Fiber ' + str(fibers[ifib]))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # dflux.png
        plotfile = specdir5 + 'monitor/' + instrument + '/dflux.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))
            ymax = 35000
            ymin = 0 - ymax*0.05
            yspan = ymax - ymin

            gdcal = allexp[dome]
            caljd = gdcal['JD'] - 2.4e6

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                ax.set_ylabel(r'Median Flux')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

                w = np.nanmedian(gdcal['MED'][:, ichip, :])
                ax.axhline(y=w, color='k', linewidth=3, zorder=1)

                for ifib in range(nplotfibs):
                    yvals = gdcal['MED'][:, ichip, fibers[ifib]]
                    ax.scatter(caljd, yvals, marker='o', s=markersz, c=colors[ifib], alpha=alf, 
                               label='Fiber ' + str(fibers[ifib]), zorder=3)

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # dfwhm.png
        plotfile = specdir5 + 'monitor/' + instrument + '/dfwhm.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))
            ymax = 3.0
            if instrument == 'apogee-s': 
                ymax = 3.0
            ymin = 0.8
            yspan = ymax - ymin

            gd, = np.where(dometrace['MJD'] > 50000)
            df = dometrace[gd]
            dmjd = df['MJD']
            dfwhm = df['GAUSS_SIGMA']*2.355

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                ax.set_ylabel(r'FWHM (pixels)')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

                for ifib in range(nplotfibs):
                    yvals = dfwhm[:, ichip, ifib]
                    ax.scatter(dmjd, yvals, marker='o', s=markersz, c=colors[ifib], alpha=alf, 
                               label='Fiber ' + str(fibers[ifib]))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # zero.png
        plotfile = specdir5 + 'monitor/' + instrument + '/zero.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,8))
            ymax = 21
            ymin = 10
            yspan = ymax - ymin

            ax = plt.subplot2grid((1,1), (0,0))
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymin, ymax)
            ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
            ax.minorticks_on()
            ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
            ax.tick_params(axis='both',which='major',length=axmajlen)
            ax.tick_params(axis='both',which='minor',length=axminlen)
            ax.tick_params(axis='both',which='both',width=axwidth)
            ax.set_xlabel(r'JD - 2,400,000')
            ax.set_ylabel(r'Zeropoint (mag.)')
            ax.axes.xaxis.set_ticklabels([])
            ax.axvline(x=59146, color='r', linewidth=2)

            for iyear in range(nyears):
                ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                ax.text(yearjd[iyear], ymax+yspan*0.02, cyears[iyear], ha='center')

            t = Time(allsci['DATEOBS'], format='fits')
            jd = t.jd - 2.4e6
            ax.scatter(jd, allsci['ZERO'], marker='o', s=markersz, c='teal', alpha=alf)

            fig.subplots_adjust(left=0.04,right=0.99,bottom=0.115,top=0.94,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # tpos.png
        plotfile = specdir5 + 'monitor/' + instrument + '/tpos.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))

            gdcal = allcal[thar]
            caljd = gdcal['JD']-2.4e6

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                ax.set_ylabel(r'Position (pixel)')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                w = np.nanmedian(gdcal['GAUSS'][:, 1, ichip, :, 1])
                ymin = w - 40
                ymax = w + 40
                yspan = ymax - ymin
                ax.set_ylim(ymin, ymax)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

                for ifib in range(nplotfibs):
                    yvals = gdcal['GAUSS'][:, 1, ichip, ifib, 1] 
                    ax.scatter(caljd, yvals, marker='o', s=markersz, c=colors[ifib], alpha=alf, label='Fiber ' + str(fibers[ifib]))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)
                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # ThArNe lamp line FWHM
            for iline in range(2):
                plotfile = specdir5 + 'monitor/' + instrument + '/tfwhm' + str(iline) + '.png'
                if (os.path.exists(plotfile) == False) | (clobber == True):
                    print("----> monitor: Making " + os.path.basename(plotfile))

                    fig = plt.figure(figsize=(30,14))

                    gdcal = allcal[thar]
                    caljd = gdcal['JD']-2.4e6

                    for ichip in range(nchips):
                        chip = chips[ichip]

                        ax = plt.subplot2grid((nchips,1), (ichip,0))
                        ax.set_xlim(xmin, xmax)
                        ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                        ax.minorticks_on()
                        ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                        ax.tick_params(axis='both',which='major',length=axmajlen)
                        ax.tick_params(axis='both',which='minor',length=axminlen)
                        ax.tick_params(axis='both',which='both',width=axwidth)
                        if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                        ax.set_ylabel(r'FWHM ($\rm \AA$)')
                        if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                        ax.axvline(x=59146, color='r', linewidth=2)

                        w = np.nanmedian(2.0 * np.sqrt(2 * np.log(2)) * gdcal['GAUSS'][:, iline, ichip, :, 2])
                        ymin = w * 0.8
                        ymax = w * 1.25
                        yspan = ymax - ymin
                        ax.set_ylim(ymin, ymax)

                        for iyear in range(nyears):
                            ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                            if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

                        for ifib in range(nplotfibs):
                            w = np.nanmedian(2.0 * np.sqrt(2 * np.log(2)) * gdcal['GAUSS'][:, iline, ichip, ifib, 2])
                            ax.axhline(y=w, color=colors[ifib], linewidth=2, zorder=2)
                            ax.axhline(y=w, color='k', linewidth=3, zorder=1)
                            yvals = 2.0 * np.sqrt(2 * np.log(2)) * gdcal['GAUSS'][:, iline, ichip, ifib, 2]
                            ax.scatter(caljd, yvals, marker='o', s=markersz, c=colors[ifib], alpha=alf, 
                                       label='Fiber ' + str(fibers[ifib]), zorder=3)

                        ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                                ha='center', va='top', color=chip, bbox=bboxpar)
                        if ichip == 0: 
                            ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                                      fontsize=fsz, edgecolor='k', framealpha=1)

                    fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
                    plt.savefig(plotfile)
                    plt.close('all')

        ###########################################################################################
        # trace.png
        plotfile = specdir5 + 'monitor/' + instrument + '/trace.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,12))
            ymax = np.nanmedian(allepsf['CENT']) + 1
            ymin = np.nanmedian(allepsf['CENT']) - 1
            yspan = ymax - ymin

            caljd = Time(allepsf['MJD'], format='mjd').jd - 2.4e6

            ax1 = plt.subplot2grid((2,1), (0,0))
            ax2 = plt.subplot2grid((2,1), (1,0))
            axes = [ax1, ax2]

            ax1.xaxis.set_major_locator(ticker.MultipleLocator(500))
            ax1.set_xlim(xmin, xmax)
            ax1.set_xlabel(r'JD - 2,400,000')
            ax2.set_xlabel(r'LN2 Level')
            ax1.axvline(x=59146, color='r', linewidth=2)
            for ax in axes:
                ax.set_ylim(ymin, ymax)
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                ax.set_ylabel(r'Trace Center')

            for iyear in range(nyears):
                ax1.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                ax1.text(yearjd[iyear], ymax+yspan*0.025, cyears[iyear], ha='center')

            ax1.scatter(caljd, allepsf['CENT'], marker='o', s=markersz*4, c='cyan', edgecolors='k', alpha=alf)
            ax2.scatter(allepsf['LN2LEVEL'], allepsf['CENT'], marker='o', s=markersz*4, c='cyan', edgecolors='k', alpha=alf)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.07,top=0.96,hspace=0.17,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # biasmean.png
        plotfile = specdir5 + 'monitor/' + instrument + '/biasmean.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))
            ymax = 1000.0
            ymin = 0.1
            yspan = ymax - ymin

            gdcal = alldark[dark]
            caljd = gdcal['JD'] - 2.4e6

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                if ichip == 1: ax.set_ylabel(r'Mean (column median)')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.25, cyears[iyear], ha='center')

                for ibias in range(4):
                    ax.semilogy(caljd, gdcal['MEAN'][:, ibias, ichip], marker='o', ms=3, alpha=alf, 
                                mec=colors1[ibias], mfc=colors1[ibias], linestyle='', label='quad '+str(ibias+1))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)

                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # biassig.png
        plotfile = specdir5 + 'monitor/' + instrument + '/biassig.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(30,14))
            ymax = 1000.0
            ymin = 0.1
            yspan = ymax - ymin

            gdcal = alldark[dark]
            caljd = gdcal['JD'] - 2.4e6

            for ichip in range(nchips):
                chip = chips[ichip]

                ax = plt.subplot2grid((nchips,1), (ichip,0))
                ax.set_xlim(xmin, xmax)
                ax.set_ylim(ymin, ymax)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
                if ichip == 1: ax.set_ylabel(r'$\sigma$ (column median)')
                if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])
                ax.axvline(x=59146, color='r', linewidth=2)

                for iyear in range(nyears):
                    ax.axvline(x=yearjd[iyear], color='k', linestyle='dashed', alpha=alf)
                    if ichip == 0: ax.text(yearjd[iyear], ymax+yspan*0.25, cyears[iyear], ha='center')

                for ibias in range(4):
                    ax.semilogy(caljd, gdcal['SIG'][:, ibias, ichip], marker='o', ms=3, alpha=alf, 
                                mec=colors1[ibias], mfc=colors1[ibias], linestyle='', label='quad '+str(ibias+1))

                ax.text(0.97,0.92,chip.capitalize() + '\n' + 'Chip', transform=ax.transAxes, 
                        ha='center', va='top', color=chip, bbox=bboxpar)

                if ichip == 0: 
                    ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=4, 
                              fontsize=fsz, edgecolor='k', framealpha=1)

            fig.subplots_adjust(left=0.06,right=0.995,bottom=0.06,top=0.96,hspace=0.08,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

        ###########################################################################################
        # moonsky.png
        plotfile = specdir5 + 'monitor/' + instrument + '/moonsky.png'
        if (os.path.exists(plotfile) == False) | (clobber == True):
            print("----> monitor: Making " + os.path.basename(plotfile))

            fig = plt.figure(figsize=(31,12))
            ymax = 11
            ymin = 16.8
            if instrument == 'apogee-s': 
                ymax = 12
                ymin = 19
            yspan = ymax - ymin

            ax1 = plt.subplot2grid((2,1), (0,0))
            ax2 = plt.subplot2grid((2,1), (1,0))
            axes = [ax1, ax2]

            ax1.axes.xaxis.set_ticklabels([])
            ax2.set_xlabel(r'Moon Phase')

            for ax in axes:
                ax.set_xlim(0, 1)
                ax.set_ylim(ymin, ymax)
                ax.minorticks_on()
                ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
                ax.tick_params(axis='both',which='major',length=axmajlen)
                ax.tick_params(axis='both',which='minor',length=axminlen)
                ax.tick_params(axis='both',which='both',width=axwidth)
                ax.text(-0.03, 0.5, 'Sky Brightness', ha='right', va='center', rotation=90, transform=ax.transAxes)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(0.1))

            sc1 = ax1.scatter(allsci['MOONPHASE'], allsci['SKY'][:, 1], marker='o', s=markersz, c=allsci['MOONDIST'], 
                              cmap='rainbow', alpha=0.8, vmin=0, vmax=90.01)

            gd, = np.where((allsci['ZERO'] != -np.inf) & (allsci['ZERO'] < 20) & (allsci['ZERO'] > 0))
            sc2 = ax2.scatter(allsci['MOONPHASE'][gd], allsci['SKY'][gd][:, 1], marker='o', s=markersz, c=allsci['ZERO'][gd], 
                              cmap='rainbow', alpha=0.8, vmin=17, vmax=19)

            ax_divider = make_axes_locatable(ax1)
            cax = ax_divider.append_axes("right", size="2%", pad="1%")
            cb1 = colorbar(sc1, cax=cax, orientation="vertical")
            cax.minorticks_on()
            cax.yaxis.set_major_locator(ticker.MultipleLocator(15))
            ax1.text(1.06, 0.5, r'Moon Distance (deg.)',ha='left', va='center', rotation=-90, transform=ax1.transAxes)

            ax_divider = make_axes_locatable(ax2)
            cax = ax_divider.append_axes("right", size="2%", pad="1%")
            cb1 = colorbar(sc2, cax=cax, orientation="vertical")
            cax.minorticks_on()
            cax.yaxis.set_major_locator(ticker.MultipleLocator(0.5))
            ax2.text(1.066, 0.5, r'Zeropoint (cloudiness)',ha='left', va='center', rotation=-90, transform=ax2.transAxes)

            fig.subplots_adjust(left=0.045,right=0.945,bottom=0.07,top=0.96,hspace=0.17,wspace=0.00)
            plt.savefig(plotfile)
            plt.close('all')

    print("----> monitor done")


''' GETQACALSTRUCT: put SDSS-IV and SDSS-V QAcal files in structure '''
def getQAcalStruct(data=None):

    chips = np.array(['blue','green','red'])
    nchips = len(chips)
    fibers = np.array([10,80,150,220,290])
    nfibers = len(fibers)
    nlines = 2
    nquad = 4

    dt = np.dtype([('NAME',    np.str,30),
                   ('MJD',     np.str,30),
                   ('JD',      np.float64),
                   ('NFRAMES', np.int16),
                   ('NREAD',   np.int16),
                   ('EXPTIME', np.float32),
                   ('QRTZ',    np.int16),
                   ('UNE',     np.int16),
                   ('THAR',    np.int16),
                   ('FLUX',    np.float32,(nchips,300)),
                   ('GAUSS',   np.float32,(nlines,nchips,nfibers,4)),
                   ('WAVE',    np.float64,(nlines,nchips,nfibers)),
                   ('FIBERS',  np.int16,(nfibers)),
                   ('LINES',   np.float32,(nlines,nchips))])

    outstr = np.zeros(len(data['NAME']), dtype=dt)

    outstr['NAME'] =    data['NAME']
    outstr['MJD'] =     data['MJD']
    outstr['JD'] =      data['JD']
    outstr['NFRAMES'] = data['NFRAMES']
    outstr['NREAD'] =   data['NREAD']
    outstr['EXPTIME'] = data['EXPTIME']
    outstr['QRTZ'] =    data['QRTZ']
    outstr['UNE'] =     data['UNE']
    outstr['THAR'] =    data['THAR']
    outstr['FLUX'] =    data['FLUX']
    outstr['GAUSS'] =   data['GAUSS']
    outstr['WAVE'] =    data['WAVE']
    outstr['FIBERS'] =  data['FIBERS']
    outstr['LINES'] =   data['LINES']

    return outstr


''' GETQADARKflatSTRUCT: put SDSS-IV and SDSS-V QAdarkflat files in structure '''
def getQAdarkflatStruct(data=None):

    chips = np.array(['blue','green','red'])
    nchips = len(chips)
    nquad = 4

    dt = np.dtype([('NAME',    np.str, 30),
                   ('MJD',     np.str, 30),
                   ('JD',      np.float64),
                   ('NFRAMES', np.int16),
                   ('NREAD',   np.int16),
                   ('EXPTIME', np.float32),
                   ('QRTZ',    np.int16),
                   ('UNE',     np.int16),
                   ('THAR',    np.int16),
                   ('EXPTYPE', np.str, 30),
                   ('MEAN',    np.float32, (nquad,nchips)),
                   ('SIG',     np.float32, (nquad,nchips))])

    outstr = np.zeros(len(data['NAME']), dtype=dt)

    outstr['NAME'] =    data['NAME']
    outstr['MJD'] =     data['MJD']
    outstr['JD'] =      data['JD']
    outstr['NFRAMES'] = data['NFRAMES']
    outstr['NREAD'] =   data['NREAD']
    outstr['EXPTIME'] = data['EXPTIME']
    outstr['QRTZ'] =    data['QRTZ']
    outstr['UNE'] =     data['UNE']
    outstr['THAR'] =    data['THAR']
    outstr['EXPTYPE'] = data['EXPTYPE']
    outstr['MEAN'] =    data['MEAN']
    outstr['SIG'] =     data['SIG']

    return outstr

''' GETEXPSTRUCT: put SDSS-IV and SDSS-V MJDexp files in structure '''
def getExpStruct(data=None):

    chips = np.array(['blue','green','red'])
    nchips = len(chips)

    dt = np.dtype([('MJD',       np.int32),
                   ('DATEOBS',   np.str, 30),
                   ('JD',        np.float64),
                   ('NUM',       np.int32),
                   ('NFRAMES',   np.int16),
                   ('IMAGETYP',  np.str, 30),
                   ('PLATEID',   np.int16),
                   ('CARTID',    np.str, 5),
                   ('RA',        np.float64),
                   ('DEC',       np.float64),
                   ('SEEING',    np.float32),
                   ('ALT',       np.float32),
                   ('QRTZ',      np.int16),
                   ('THAR',      np.int16),
                   ('UNE',       np.int16),
                   ('FFS',       np.str, 30),
                   ('LN2LEVEL',  np.float32),
                   ('DITHPIX',   np.float32),
                   ('TRACEDIST', np.float32),
                   ('MED',       np.float32, (nchips,300))])

    outstr = np.zeros(len(data['MJD']), dtype=dt)

    outstr['MJD'] =       data['MJD']
    outstr['DATEOBS'] =   data['DATEOBS']
    outstr['JD'] =        data['JD']
    outstr['NUM'] =       data['NUM']
    outstr['NFRAMES'] =   data['NFRAMES']
    outstr['IMAGETYP'] =  data['IMAGETYP']
    outstr['PLATEID'] =   data['PLATEID']
    outstr['CARTID'] =    str(data['CARTID'])
    outstr['RA'] =        data['RA']
    outstr['DEC'] =       data['DEC']
    outstr['SEEING'] =    data['SEEING']
    outstr['ALT'] =       data['ALT']
    outstr['QRTZ'] =      data['QRTZ']
    outstr['THAR'] =      data['THAR']
    outstr['UNE'] =       data['UNE']
    outstr['FFS'] =       data['FFS']
    outstr['LN2LEVEL'] =  data['LN2LEVEL']
    outstr['DITHPIX'] =   data['DITHPIX']
    outstr['TRACEDIST'] = data['TRACEDIST']
    outstr['MED'] =       data['MED']

    return outstr

''' GETSCISTRUCT: put SDSS-IV and SDSS-V apPlateSum files in structure '''
def getSciStruct(data=None):
    cols = data.columns.names

    dt = np.dtype([('TELESCOPE', np.str, 6),
                   ('PLATE',     np.int32),
                   ('NREADS',    np.int32),
                   ('DATEOBS',   np.str, 30),
                   ('EXPTIME',   np.int32),
                   ('SECZ',      np.float64),
                   ('HA',        np.float64),
                   ('DESIGN_HA', np.float64, 3),
                   ('SEEING',    np.float64),
                   ('FWHM',      np.float64),
                   ('GDRMS',     np.float64),
                   ('CART',      np.str, 5),
                   ('PLUGID',    np.str, 30),
                   ('DITHER',    np.float64),
                   ('MJD',       np.int32),
                   ('IM',        np.int32),
                   ('ZERO',      np.float64),
                   ('ZERORMS',   np.float64),
                   ('ZERONORM',  np.float64),
                   ('SKY',       np.float64, 3),
                   ('SN',        np.float64, 3),
                   ('SNC',       np.float64, 3),
                   #('SNT',       np.float64, 3),
                   ('ALTSN',     np.float64, 3),
                   ('NSN',       np.int32),
                   ('SNRATIO',   np.float64),
                   ('MOONDIST',  np.float64),
                   ('MOONPHASE', np.float64),
                   ('TELLFIT',   np.float64, (3,6))])

    outstr = np.zeros(len(data['PLATE']), dtype=dt)

    outstr['TELESCOPE'] = data['TELESCOPE']
    outstr['PLATE'] =     data['PLATE']
    outstr['NREADS'] =    data['NREADS']
    outstr['DATEOBS'] =   data['DATEOBS']
    if 'EXPTIME' in cols: outstr['EXPTIME'] =   data['EXPTIME']
    outstr['SECZ'] =      data['SECZ']
    outstr['HA'] =        data['HA']
    outstr['DESIGN_HA'] = data['DESIGN_HA']
    outstr['SEEING'] =    data['SEEING']
    outstr['FWHM'] =      data['FWHM']
    outstr['GDRMS'] =     data['GDRMS']
    outstr['CART'] =      str(data['CART'])
    outstr['PLUGID'] =    data['PLUGID']
    outstr['DITHER'] =    data['DITHER']
    outstr['MJD'] =       data['MJD']
    outstr['IM'] =        data['IM']
    outstr['ZERO'] =      data['ZERO']
    outstr['ZERORMS'] =   data['ZERORMS']
    outstr['ZERONORM'] =  data['ZERONORM']
    outstr['SKY'] =       data['SKY']
    outstr['SN'] =        data['SN']
    outstr['SNC'] =       data['SNC']
    outstr['ALTSN'] =     data['ALTSN']
    outstr['NSN'] =       data['NSN']
    outstr['SNRATIO'] =   data['SNRATIO']
    outstr['MOONDIST'] =  data['MOONDIST']
    outstr['MOONPHASE'] = data['MOONPHASE']
    outstr['TELLFIT'] =   data['TELLFIT']

    return outstr



