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
from mpl_toolkits.axes_grid1.axes_divider import make_axes_locatable
from mpl_toolkits.axes_grid1.colorbar import colorbar

# import pdb; pdb.set_trace()

''' MONITOR: Instrument monitoring plots and html '''
def monitor(instrument='apogee-n', apred='daily', clobber=True, makesumfiles=False):

    print("----> monitor starting")

    chips = np.array(['blue','green','red'])
    nchips = len(chips)

    fibers = np.array([10,80,150,220,290])
    nfibers = len(fibers)

    nlines = 2

    nquad = 4

    # Establish  directories... hardcode sdss4/apogee2 for now

    specdir5 = os.environ.get('APOGEE_REDUX') + '/' + apred + '/'
    specdir = '/uufs/chpc.utah.edu/common/home/sdss/apogeework/apogee/spectro/redux/current/'
    sdir5 = specdir5 + 'monitor/' + instrument + '/'
    sdir = '/uufs/chpc.utah.edu/common/home/sdss/apogeework/apogee/spectro/redux/current/monitor/apogee-n/'
    mdir = 'monitor/' + instrument + '/'

    if makesumfiles is False:
        # NOTE: we probably don't want the below files in the redux/daily directory.
        allcal =  fits.open(specdir + instrument + 'Cal.fits')[1].data
        alldark = fits.open(specdir + instrument + 'Cal.fits')[2].data
        allexp =  fits.open(specdir + instrument + 'Exp.fits')[1].data
        allsci =  fits.open(specdir + instrument + 'Sci.fits')[1].data
    else:
        ###########################################################################################
        # MAKE MASTER QACAL FILE
        outfile = specdir5 + 'monitor/' + instrument + '_Cal.fits'
        print("----> monitor: Making " + os.path.basename(outfile))

        # Append together the individual QAcal files
        files = glob.glob(specdir + '/cal/' + instrument + '/*/*QAcal*.fits')
        if len(files) < 1:
            print("----> monitor: No files! do you have correct version set?")
        else:
            files.sort()
            files = np.array(files)
            nfiles = len(files)
            for i in range(nfiles):
                print("---->    monitor: reading " + files[i])
                a = fits.open(files[i])[1].data

                # Make output structure and write to fits file
                dt = np.dtype([('NAME',    np.str,30),
                               ('MJD',     np.str,30),
                               ('JD',      np.float64),
                               ('NFRAMES', np.int32),
                               ('NREAD',   np.int32),
                               ('EXPTIME', np.float64),
                               ('QRTZ',    np.int32),
                               ('UNE',     np.int32),
                               ('THAR',    np.int32),
                               ('FLUX',    np.float64,(300,nchips)),
                               ('GAUSS',   np.float64,(4,nfibers,nchips,nlines)),
                               ('WAVE',    np.float64,(nfibers,nchips,nlines)),
                               ('FIBERS',  np.float64,(nfibers)),
                               ('LINES',   np.float64,(nchips,nlines))])
                struct = np.zeros(len(a['NAME']), dtype=dt)

                struct['NAME'] = a['NAME']
                struct['MJD'] = a['MJD']
                struct['JD'] = a['JD']
                struct['NFRAMES'] = a['NFRAMES']
                struct['NREAD'] = a['NREAD']
                struct['EXPTIME'] = a['EXPTIME']
                struct['QRTZ'] = a['QRTZ']
                struct['UNE'] = a['UNE']
                struct['THAR'] = a['THAR']
                struct['FLUX'] = a['FLUX']
                struct['GAUSS'] = a['GAUSS']
                struct['WAVE'] = a['WAVE']
                struct['FIBERS'] = a['FIBERS']
                struct['LINES'] = a['LINES']

                if i == 0:
                    allcal = struct
                else:
                    allcal = np.concatenate([allcal, struct])

            Table(allcal).write(outfile, overwrite=True)

            print("----> monitor: Finished adding QAcal info to " + os.path.basename(outfile))

        ###########################################################################################
        # APPEND QADARKFLAT INFO TO MASTER QACAL FILE
        print("----> monitor: Adding QAdarkflat info to " + os.path.basename(outfile))

        # Append together the individual QAdarkflat files
        files = glob.glob(specdir + '/cal/' + instrument + '/*/*QAdarkflat*.fits')
        if len(files) < 1:
            print("----> monitor: No files! do you have correct version set?")
        else:
            files.sort()
            files = np.array(files)
            nfiles = len(files)
            for i in range(nfiles):
                print("---->    monitor: reading " + files[i])
                a = fits.open(files[i])[1].data

                # Make output structure.
                dt = np.dtype([('NAME',    np.str, 30),
                               ('MJD',     np.str, 30),
                               ('JD',      np.float64),
                               ('NFRAMES', np.int32),
                               ('NREAD',   np.int32),
                               ('EXPTIME', np.float64),
                               ('QRTZ',    np.int32),
                               ('UNE',     np.int32),
                               ('THAR',    np.int32),
                               ('EXPTYPE', np.str, 30),
                               ('MEAN',    np.float64, (nchips,nquad)),
                               ('SIG',     np.float64, (nchips,nquad))])
                struct = np.zeros(len(a['NAME']), dtype=dt)

                struct['NAME'] = a['NAME']
                struct['MJD'] = a['MJD']
                struct['JD'] = a['JD']
                struct['NFRAMES'] = a['NFRAMES']
                struct['NREAD'] = a['NREAD']
                struct['EXPTIME'] = a['EXPTIME']
                struct['QRTZ'] = a['QRTZ']
                struct['UNE'] = a['UNE']
                struct['THAR'] = a['THAR']
                struct['EXPTYPE'] = a['EXPTYPE']
                struct['MEAN'] = a['MEAN']
                struct['SIG'] = a['SIG']

                if i == 0:
                    alldark = struct
                else:
                    alldark = np.concatenate([alldark, struct])

            hdulist = fits.open(outfile)
            hdu1 = fits.table_to_hdu(Table(struct))
            hdulist.append(hdu1)
            hdulist.writeto(outfile, overwrite=True)
            hdulist.close()

            print("----> monitor: Finished adding QAdarkflat info to " + os.path.basename(outfile))

        ###########################################################################################
        # MAKE MASTER EXP FILE
        outfile = specdir5 + 'monitor/' + instrument + '_Exp.fits'
        print("----> monitor: Making " + os.path.basename(outfile))

        # Get long term trends from dome flats
        # Append together the individual exp files
        files = glob.glob(specdir + '/exposures/' + instrument + '/*/5*exp.fits')
        files.sort()
        files = np.array(files)
        nfiles=len(files)
        for i in range(nfiles):
            print("---->    monitor: reading " + files[i])
            a = fits.open(files[i])[1].data

            # Make output structure.
            dt = np.dtype([('MJD',       np.int32),
                           ('DATEOBS',   np.str, 23),
                           ('JD',        np.float64),
                           ('NUM',       np.int32),
                           ('NFRAMES',   np.int32),
                           ('IMAGETYPE', np.str, 10),
                           ('PLATEID',   np.int32),
                           ('CARTID',    np.int32),
                           ('RA',        np.float64),
                           ('DEC',       np.float64),
                           ('SEEING',    np.float64),
                           ('ALT',       np.float64),
                           ('QRTZ',      np.int32),
                           ('THAR',      np.int32),
                           ('UNE',       np.int32),
                           ('FFS',       np.str, 15),
                           ('LN2LEVEL',  np.float64),
                           ('DITHPIX',   np.float64),
                           ('TRACEDIST', np.float64),
                           ('MED',       np.float64,(300,nchips))])
            struct = np.zeros(len(a['MJD']), dtype=dt)

            struct['MJD'] = a['MJD']
            struct['DATEOBS'] = a['DATEOBS']
            struct['JD'] = a['JD']
            struct['NUM'] = a['NUM']
            struct['NFRAMES'] = a['NFRAMES']
            struct['IMAGETYPE'] = a['IMAGETYPE']
            struct['PLATEID'] = a['PLATEID']
            struct['CARTID'] = a['CARTID']
            struct['RA'] = a['RA']
            struct['DEC'] = a['DEC']
            struct['SEEING'] = a['SEEING']
            struct['ALT'] = a['ALT']
            struct['QRTZ'] = a['QRTZ']
            struct['THAR'] = a['THAR']
            struct['UNE'] = a['UNE']
            struct['FFS'] = a['FFS']
            struct['LN2LEVEL'] = a['LN2LEVEL']
            struct['DITHPIX'] = a['DITHPIX']
            struct['TRACEDIST'] = a['TRACEDIST']
            struct['MED'] = a['MED']

            if i == 0:
                allexp = struct 
            else:
                allexp = np.concatenate([allexp, struct])

        Table(allcal).write(outfile, overwrite=True)
        print("----> monitor: Finished making " + os.path.basename(outfile))

        ###########################################################################################
        # MAKE MASTER apPlateSum FILE
        outfile = specdir5 + 'monitor/' + instrument + '_Sci.fits'
        print("----> monitor: Making " + os.path.basename(outfile))

        # Get zeropoint info from apPlateSum files
        files = glob.glob(specdir + '/visit/' + telescope + '/*/*/*/' + 'apPlateSum*.fits')
        if len(files) < 1:
            print("----> monitor: No files! do you have correct version set?")
        else:
            files.sort()
            files = np.array(files)
            nfiles = len(files)
            for i in range(nfiles):
                print("---->    monitor: reading " + files[i])
                a = fits.open(files[i])[1].data

                # Make output structure.
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
                               ('CART',      np.int32),
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
                struct = np.zeros(len(a['PLATE']), dtype=dt)

                if i == 0:
                    allsci = struct
                else:
                    allsci = np.concatenate([allsci, struct])

            Table(allsci).write(outfile, overwrite=True)
            print("----> monitor: Finished making " + os.path.basename(outfile))

    # MAKE THE MONITOR HTML
    outfile = specdir5 + 'monitor/' + instrument + '-monitor.html'
    print("----> monitor: Making " + os.path.basename(outfile))

    html = open(outfile, 'w')
    tit = 'APOGEE-N Instrument Monitor'
    if instrument != 'apogee-n': tit = 'APOGEE-S Instrument Monitor'
    html.write('<HTML><HEAD><title>' + tit + '</title></head><BODY>\n')
    html.write('<H1>' + tit + '</H1>\n')
    html.write('<HR>\n')
    html.write('<ul>\n')
    html.write('<li> Throughput / lamp monitors\n')
    html.write('<ul>\n')
    html.write('<li> <a href=#quartz> Cal channel quartz</a>\n')
    html.write('<li> <a href=monitor/fiber/fiber.html>Individual fiber throughputs</a>\n')
    html.write('<li> <a href=#tharflux> Cal channel ThAr</a>\n')
    html.write('<li> <a href=#uneflux> Cal channel UNe</a>\n')
    html.write('<li> <a href=#dome>Dome flats</a>\n')
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
    html.write('</ul>\n')
    html.write('<HR>\n')

    # find the different lamp types
    thar, = np.where(allcal['THAR'] == 1)
    une, = np.where(allcal['UNE'] == 1)
    qrtz, = np.where(allcal['QRTZ'] == 1)

    html.write('<h3> <a name=qflux></a> Quartz lamp median brightness (per 10 reads) in extracted frame </h3>\n')
    html.write('<A HREF=' + instrument + '/qflux.png target="_blank"><IMG SRC=' + instrument + '/qflux.png WIDTH=1400></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a href=fiber/fiber.html> Individual fiber throughputs from quartz </H3>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=tharflux></a>ThAr line brightness (per 10 reads) in extracted frame </H3>\n')
    html.write('<A HREF=' + instrument + '/tharflux.png target="_blank"><IMG SRC=' + instrument + '/tharflux.png WIDTH=1400>></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=uneflux></a>UNe line brightness (per 10 reads) in extracted frame </H3>\n')
    html.write('<A HREF=' + instrument + '/uneflux.png target="_blank"><IMG SRC=' + instrument + '/uneflux.png WIDTH=1400>></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=dome></a>Dome flat median brightness</H3>\n')
    html.write('<A HREF=' + instrument + '/dome.png target="_blank"><IMG SRC=' + instrument + '/dome.png WIDTH=1400>></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=zero></a>Science frame zero point</H3>\n')
    html.write('<A HREF=' + instrument + '/zero.png target="_blank"><IMG SRC=' + instrument + '/zero.png WIDTH=1400>></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=tpos></a>ThArNe lamp line position</H3>\n')
    html.write('<A HREF=' + instrument + '/tpos.png target="_blank"><IMG SRC=' + instrument + '/tpos.png WIDTH=1400>></A>\n')
    html.write('<HR>\n')

    for iline in range(2):
        plotfile='tfwhm' + str(iline) + '.png'
        tmp1 = str("%.1f" % round(allcal['LINES'][thar][0][iline][0],1))
        tmp2 = str("%.1f" % round(allcal['LINES'][thar][0][iline][1],1))
        tmp3 = str("%.1f" % round(allcal['LINES'][thar][0][iline][2],1))
        txt = '<a name=tfwhm></a> ThArNe lamp line FWHM, line position (x pixel): '
        html.write('<H3>' + txt + tmp1 + ' ' + tmp2 + ' ' + tmp3 + '</H3>\n')
        html.write('<A HREF=' + instrument + '/' + plotfile + ' target="_blank"><img src=' + instrument + '/' + plotfile + '></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=trace></a> Trace position, fiber 150, column 1000</H3>\n')
    html.write('<A HREF=trace.png target="_blank"><IMG SRC=trace.png WIDTH=1400>></A>\n')
    html.write('<HR>\n')

    html.write('<H3> <a name=detectors></a>Detectors</H3>\n')
    html.write('<H4> Dark Mean </h4>\n')
    html.write('<A HREF=' + instrument + '/biasmean.png target="_blank"><IMG SRC=' + instrument + '/biasmean.png WIDTH=1400>></A>\n')

    html.write('<H4> Dark Sigma </h4>\n')
    html.write('<A HREF=' + instrument + '/biassig.png target="_blank"><IMG SRC=' + instrument + '/biassig.png WIDTH=1400>></A>\n')

    html.write('<H3> <a name=sky></a>Sky Brightness</H3>\n')
    html.write('<A HREF=' + instrument + '/moonsky.png target="_blank"><IMG SRC=' + instrument + '/moonsky.png WIDTH=1400>></A>\n')

    html.close()

    # Set up some basic plotting parameters
    matplotlib.use('agg')
    fontsize = 24;   fsz = fontsize * 0.75
    matplotlib.rcParams.update({'font.size':fontsize, 'font.family':'serif'})
    bboxpar = dict(facecolor='white', edgecolor='none', alpha=1.0)
    axwidth = 1.5
    axmajlen = 7
    axminlen = 3.5
    alpha = 0.6

    # qflux.png
    plotfile = specdir5 + 'monitor/' + instrument + '/qflux.png'
    if (os.path.exists(plotfile) == False) | (clobber == True):
        print("----> monitor: Making " + plotfile)

        fig=plt.figure(figsize=(28,14))
        yr = [-2000,43000]
        if instrument == 'apogee-s': yr = [-1000, 100000]

        qcal = allcal[qrtz]
        qcaljd = qcal['JD']-2.4e6

        for ichip in range(nchips):
            chip = chips[ichip]

            minjd = np.min(qcaljd)
            maxjd = np.max(qcaljd)
            jdspan = maxjd - minjd
            xmin = minjd-jdspan*0.02
            xmax = maxjd+jdspan*0.10

            ax = plt.subplot2grid((nchips,1), (ichip,0))
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(yr[0], yr[1])
            ax.xaxis.set_major_locator(ticker.MultipleLocator(500))
            ax.minorticks_on()
            ax.tick_params(axis='both',which='both',direction='in',bottom=True,top=True,left=True,right=True)
            ax.tick_params(axis='both',which='major',length=axmajlen)
            ax.tick_params(axis='both',which='minor',length=axminlen)
            ax.tick_params(axis='both',which='both',width=axwidth)
            if ichip == nchips-1: ax.set_xlabel(r'JD - 2,400,000')
            ax.set_ylabel(r'Median Flux')
            if ichip < nchips-1: ax.axes.xaxis.set_ticklabels([])

            ax.scatter(qcaljd, qcal['FLUX'][:, ichip, 290] / qcal['NREAD']*10.0, marker='*', s=60, edgecolors='purple', color='white', alpha=alpha, label='Fiber 290')
            ax.scatter(qcaljd, qcal['FLUX'][:, ichip, 150] / qcal['NREAD']*10.0, marker='^', s=30, edgecolors='darkorange', color='white', alpha=alpha, label='Fiber 150')
            ax.scatter(qcaljd, qcal['FLUX'][:, ichip, 10]  / qcal['NREAD']*10.0, marker='o', s=30, edgecolors='green', color='white', alpha=alpha, label='Fiber 10')

            ax.text(0.99,0.92,chip.capitalize() + ' Chip', transform=ax.transAxes, ha='right', va='top')
            ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=2, fontsize=fsz)

        fig.subplots_adjust(left=0.07,right=0.99,bottom=0.06,top=0.98,hspace=0.08,wspace=0.00)
        plt.savefig(plotfile)
        plt.close('all')

    # tharflux.png
    plotfile = specdir5 + 'monitor/' + instrument + '/tharflux.png'
    if (os.path.exists(plotfile) == False) | (clobber == True):
        print("----> monitor: Making " + plotfile)

        fig=plt.figure(figsize=(28,14))
        ymin = np.array([-4000, -3500, -3000])
        ymax = np.array([380000, 320000, 130000]) 

        tcal = allcal[thar]
        tcaljd = tcal['JD']-2.4e6

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

            ax.scatter(tcaljd, tcal['FLUX'][:, ichip, 290] / tcal['NREAD']*10.0, marker='*', s=60, edgecolors='purple', color='white', alpha=alpha, label='Fiber 290')
            ax.scatter(tcaljd, tcal['FLUX'][:, ichip, 150] / tcal['NREAD']*10.0, marker='^', s=30, edgecolors='darkorange', color='white', alpha=alpha, label='Fiber 150')
            ax.scatter(tcaljd, tcal['FLUX'][:, ichip, 10]  / tcal['NREAD']*10.0, marker='o', s=30, edgecolors='green', color='white', alpha=alpha, label='Fiber 10')

            ax.text(0.99,0.92,chip.capitalize() + ' Chip', transform=ax.transAxes, ha='right', va='top')
            ax.legend(loc='lower right', labelspacing=0.5, handletextpad=-0.1, markerscale=2, fontsize=fsz)

        fig.subplots_adjust(left=0.07,right=0.99,bottom=0.06,top=0.98,hspace=0.08,wspace=0.00)
        plt.savefig(plotfile)
        plt.close('all')


    print("----> monitor done")









