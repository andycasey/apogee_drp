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
from astropy import units as astropyUnits
from scipy.signal import medfilt2d as ScipyMedfilt2D
from apogee_drp.utils import plan,apload,yanny,plugmap,platedata,bitmask,peakfit
from apogee_drp.apred import wave
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
from scipy.signal import medfilt, convolve, boxcar, argrelextrema, find_peaks


###################################################################################################
# Program for matching a sequence of exposures to the dome flat lookup table.
# Calls "findBestFlatExposure" to do the matching.
#
# Inputs can be:
#     (1) an array of exposure numbers
#     (2) a planfile
#     (3) a plate + MJD
#
# Output can be:
#     (1) an array of dome flat exposure numbers, one per input exposure number (default)
#     (2) a single dome flat exposure number (if the "single" keyword is set)
#
###################################################################################################
def findBestFlatSequence(ims=None, planfile=None, plate='15000', mjd='59146', telescope='apo25m', 
                         apred='daily', single=False, highfluxfrac=None, minflux=None, silent=True):

    start_time = time.time()
    print("Finding best dome flats for plate " + plate + ", MJD " + mjd)

    if ims is None:
        # Use telescope, plate, mjd, and apred to load planfile into structure.
        load = apload.ApLoad(apred=apred, telescope=telescope)
        if planfile is None: planfile = load.filename('Plan', plate=int(plate), mjd=mjd)
        planstr = plan.load(planfile, np=True)
        instrument = planstr['instrument']

        # Get field name
        tmp = planfile.split(telescope+'/')
        field = tmp[1].split('/')[0]

        # Establish directories.
        datadir = {'apo25m':os.environ['APOGEE_DATA_N'], 'apo1m':os.environ['APOGEE_DATA_N'],
                   'lco25m':os.environ['APOGEE_DATA_S']}[telescope]
        apodir = os.environ.get('APOGEE_REDUX') + '/' + apred + '/'
        mdir = apodir + 'monitor/'

        # Read in the dome flat lookup table and master exposure table
        dome = fits.getdata(mdir + instrument + 'DomeFlatTrace-all.fits')
        exp = fits.getdata(mdir + instrument + 'Exp.fits')

        # Get array of object exposures and find out how many are objects.
        all_ims = planstr['APEXP']['name']
        flavor = planstr['APEXP']['flavor']

        gd,= np.where(flavor == 'object')
        n_ims = len(gd)

        if n_ims > 0:
            ims = all_ims[gd]
            # Make an array indicating which exposures made it to apCframe
            # 0 = not reduced, 1 = reduced
            imsReduced = np.zeros(n_ims)
            for i in range(n_ims):
                cframe = load.filename('Cframe', field=field, plate=int(plate), mjd=mjd, num=ims[i], chips=True)
                if os.path.exists(cframe.replace('Cframe-','Cframe-a-')): imsReduced[i] = 1
            good, = np.where(imsReduced == 1)
            if len(good) > 0:
                ims = ims[good]
            else:
                print("PROBLEM!!! 1D files not found for plate " + plate + ", MJD " + mjd + ". Skipping.\n")
                return
        else:
            print("PROBLEM!!! no object images found for plate " + plate + ", MJD " + mjd + ". Skipping.\n")
            return

    n_ims = len(ims)
    print(str(int(round(n_ims))) + " exposures\n")

    dflatnums = np.empty(n_ims)
    dflatmjds = np.empty(n_ims)
    rms = np.empty(n_ims)
    for i in range(n_ims):
        # Run findBestFlatExposure on this exposure
        dflatnums[i], dflatmjds[i], rms[i] = findBestFlatExposure(apred=apred, telescope=telescope, expnum=ims[i],
                                                                  minflux=minflux, highfluxfrac=highfluxfrac, silent=silent)
        # Get info about exposure and matching dome flat
        pflat, = np.where(dflatnums[i] == dome['PSFID'])
        psci, = np.where(ims[i] == exp['NUM'])
        p1 = '(' + str(i+1).rjust(2) + ') sci exposure ' + str(ims[i]) + ' ----> dflat ' + str(int(round(dflatnums[i]))) + ' (MJD ' + str(int(round(dflatmjds[i]))) + '),  '
        p2 = 'alt [' + str("%.3f" % round(exp['ALT'][psci][0],3)) + ', ' + str("%.3f" % round(dome['ALT'][pflat][0],3)) + '],  '
        p3 = 'ln2level [' + str("%.3f" % round(exp['LN2LEVEL'][psci][0],3)) + ', ' + str("%.3f" % round(dome['LN2LEVEL'][pflat][0],3)) + '],   '
        p4 = 'rms = ' + str("%.4f" % round(rms[i],4))
        print(p1 + p2 + p3 + p4)

    uniqdflatnums = np.unique(dflatnums)
    nflats = len(uniqdflatnums)
    print('\n' + str(int(round(nflats))) + ' dome flats:')

    nrepeats = np.empty(nflats)
    for i in range(nflats):
        tmp, = np.where(uniqdflatnums[i] == dflatnums)
        nrepeats[i] = len(tmp)
        print(str(int(round(uniqdflatnums[i]))) + ':  ' + str(int(round(nrepeats[i]))).rjust(2) + ' matches')

    runtime = str("%.2f" % (time.time() - start_time))
    print("\nDone with plate " + plate + ", MJD " + mjd + " in " + runtime + " seconds.\n")

    return dflatnums


###################################################################################################
# Program for matching an exposure to the dome flat lookup table
# Calls "gaussFitAll" to do the Gaussian fitting
#
# Input is an exposure number.
#
# Output is the matched dome flat exposure number, MJD, and the r.m.s. of the match.
#
###################################################################################################
def findBestFlatExposure(apred='daily', telescope='apo25m', medianrad=100, expnum=36760022, 
                         minflux=None, highfluxfrac=None, silent=True):

    start_time = time.time()

    chips = np.array(['a','b','c'])
    nchips = len(chips)
    nfibers = 300

    instrument = 'apogee-n'
    inst = 'N'
    if telescope == 'lco25m':
        instrument = 'apogee-s'
        inst = 'S'
    fil = os.path.abspath(__file__)
    codedir = os.path.dirname(fil)
    datadir = os.path.dirname(os.path.dirname(os.path.dirname(codedir))) + '/data/domeflat/'
    refpix = ascii.read(datadir + 'refpix' + inst + '.dat')
    
    apodir = os.environ.get('APOGEE_REDUX') + '/' + apred + '/'
    mdir = apodir + 'monitor/'
    expdir = apodir + 'exposures/' + instrument + '/'

    dome = fits.getdata(mdir + instrument + 'DomeFlatTrace-all.fits')
    ndomes = len(dome)

    twodFiles = glob.glob(expdir + '*/ap2D-*' + str(expnum) + '.fits')
    twodFiles.sort()
    twodFiles = np.array(twodFiles)

    if len(twodFiles) < 3:
        if silent is False: print('PROBLEM: less then 3 ap2D files found for exposure ' + str(expnum))
    else:
        if silent is False: print('ap2D files found for exposure ' + str(expnum))

    # Loop over the chips
    rms = np.full([nchips, ndomes], 50).astype(np.float64)
    for ichip in range(nchips):
        pix0 = np.array(refpix[chips[ichip]])
        gpeaks = gaussFitAll(infile=twodFiles[ichip], medianrad=medianrad, pix0=pix0)

        # Remove failed and discrepant peakfits
        gd, = np.where(gpeaks['success'] == True)
        gpeaks = gpeaks[gd]

        # Remove discrepant peakfits
        medcenterr = np.nanmedian(gpeaks['perr'][:, 1])
        gd, = np.where(gpeaks['perr'][:, 1] < medcenterr)
        gpeaks = gpeaks[gd]
        ngpeaks = len(gd)
        if silent is False: print("   " + str(ngpeaks) + " successful peakfits")

        # Option to only use fibers with flux higher than average dome flat flux
        if highfluxfrac is not None:
            if (highfluxfrac < 0) | (highfluxfrac > 1):
                sys.exit("The highfluxfrac value needs to be between 0 and 1. Try again.")
            nkeep = int(np.ceil(ngpeaks * highfluxfrac))
            if silent is False: print("   Matching to dome flats based on the " + str(nkeep) + " highest flux fibers")
            # Sort by flux sum and keep the highest flux fibers
            fluxord = np.argsort(gpeaks['sumflux'])[::-1]
            gpeaks = gpeaks[fluxord][:nkeep]
            numord = np.argsort(gpeaks['num'])
            gpeaks = gpeaks[numord]
            ngpeaks = len(gpeaks)

        # Option to only keep fibers above a certain flux level
        if minflux is not None:
            gd, = np.where(gpeaks['sumflux'] > minflux)
            gpeaks = gpeaks[gd]
            ngpeaks = len(gpeaks)
            if silent is False: print("   Keeping " + str(ngpeaks) + " fibers with flux > " + str(minflux))

        dcent = dome['GAUSS_CENT'][:, ichip, gpeaks['num']]
        for idome in range(ndomes):
            diff = np.absolute(dcent[idome] - gpeaks['pars'][:, 1])
            gd, = np.where(np.isnan(diff) == False)
            if len(gd) < 5: continue
            diff = diff[gd]
            ndiff = len(diff)
            rms[ichip, idome] = np.sqrt(np.nansum(diff**2)/ndiff)
            if silent is False: print("   Final match based on " + str(ndiff) + " fibers:")
            if silent is False: print(gpeaks['num'][gd])

    rmsMean = np.nanmean(rms, axis=0)
    gd, = np.where(rmsMean == np.nanmin(rmsMean))
    if silent is False: print(rms[:, gd[0]])

    gdrms = str("%.5f" % round(rmsMean[gd][0],5))
    if silent is False: print("   Best dome flat for exposure " + str(expnum) + ": " + str(dome['PSFID'][gd][0]) + " (<rms> = " + str(gdrms) + ")")
    runtime = str("%.2f" % (time.time() - start_time))
    if silent is False: print("\n   Done in " + runtime + " seconds.\n")
    
    return dome['PSFID'][gd][0], dome['MJD'][gd][0], rmsMean[gd][0]


###################################################################################################
# Program for making the domeflat lookup table.
# Takes about 8 hours to run, unless a later "mjdstart" is specified.
###################################################################################################
def makeLookupTable(apred='daily', telescope='apo25m', medianrad=100, mjdstart=None):
    start_time = time.time()

    chips = np.array(['a','b','c'])
    nchips = len(chips)
    nfibers = 300

    instrument = 'apogee-n'
    inst = 'N'
    if telescope == 'lco25m':
        instrument = 'apogee-s'
        inst = 'S'
    fil = os.path.abspath(__file__)
    codedir = os.path.dirname(fil)
    datadir = os.path.dirname(os.path.dirname(os.path.dirname(codedir))) + '/data/domeflat/'
    refpix = ascii.read(datadir + 'refpix' + inst + '.dat')

    apodir = os.environ.get('APOGEE_REDUX') + '/' + apred + '/'
    mdir = apodir + '/monitor/'

    expdir5 = apodir + 'exposures/' + instrument + '/'
    expdir4 = '/uufs/chpc.utah.edu/common/home/sdss/apogeework/apogee/spectro/redux/dr17/exposures/' + instrument + '/'

    exp = fits.getdata(mdir + instrument + 'Exp.fits')
    gd, = np.where(exp['IMAGETYP'] == 'DomeFlat')
    #gd, = np.where((exp['IMAGETYP'] == 'DomeFlat') & (exp['MJD'] > 56880))
    exp = exp[gd]

    # Option to start at a certain MJD
    if mjdstart is not None: 
        gd, = np.where(exp['MJD'] >= mjdstart)
        exp = exp[gd]
    ndomes = len(gd)
    ndomestr = str(ndomes)
    
    print('Running code on ' + ndomestr + ' dome flats')
    print('Estimated runtime: ' + str(int(round(3.86*ndomes))) + ' seconds\n')

    # Output file name
    outfile = mdir + instrument + 'DomeFlatTrace-all.fits'

    # Lookup table structure.
    dt = np.dtype([('PSFID',           np.int32),
                   ('PLATEID',         np.int32),
                   ('CARTID',          np.int16),
                   ('DATEOBS',         np.str, 23),
                   ('MJD',             np.int32),
                   ('EXPTIME',         np.float64),
                   ('NREAD',           np.int16),
                   ('ROTPOS',          np.float64),
                   ('SEEING',          np.float64),
                   ('AZ',              np.float64),
                   ('ALT',             np.float64),
                   ('IPA',             np.float64),
                   ('FOCUS',           np.float64),
                   ('DITHPIX',         np.float32),
                   ('LN2LEVEL',        np.float32),
                   ('RELHUM',          np.float32),
                   ('MKSVAC',          np.float32),
                   ('TDETTOP',         np.float32),
                   ('TDETBASE',        np.float32),
                   ('TTENTTOP',        np.float32),
                   ('TCLDPMID',        np.float32),
                   ('TGETTER',         np.float32),
                   ('TTLMBRD',         np.float32),
                   ('TLSOUTH',         np.float32),
                   ('TLNORTH',         np.float32),
                   ('TLSCAM2',         np.float32),
                   ('TLSCAM1',         np.float32),
                   ('TLSDETC',         np.float32),
                   ('TLSDETB',         np.float32),
                   ('TPGVAC',          np.float32),
                   ('TCAMAFT',         np.float32),
                   ('TCAMMID',         np.float32),
                   ('TCAMFWD',         np.float32),
                   ('TEMPVPH',         np.float32),
                   ('TRADSHLD',        np.float32),
                   ('TCOLLIM',         np.float32),
                   ('TCPCORN',         np.float32),
                   ('TCLDPHNG',        np.float32),
                   ('PIX0',            np.int16,   (nchips, nfibers)),
                   ('GAUSS_HEIGHT',    np.float64, (nchips, nfibers)),
                   ('E_GAUSS_HEIGHT',  np.float64, (nchips, nfibers)),
                   ('GAUSS_CENT',      np.float64, (nchips, nfibers)),
                   ('E_GAUSS_CENT',    np.float64, (nchips, nfibers)),
                   ('GAUSS_SIGMA',     np.float64, (nchips, nfibers)),
                   ('E_GAUSS_SIGMA',   np.float64, (nchips, nfibers)),
                   ('GAUSS_YOFFSET',   np.float64, (nchips, nfibers)),
                   ('E_GAUSS_YOFFSET', np.float64, (nchips, nfibers)),
                   ('GAUSS_FLUX',      np.float64, (nchips, nfibers)),
                   ('GAUSS_NPEAKS',    np.int16, nchips)])

    outstr = np.zeros(ndomes, dtype=dt)

    # Loop over the dome flats
    for i in range(ndomes):
        ttxt = '\n(' + str(i+1) + '/' + ndomestr + '): '

        # Make sure there's a valid MJD
        if exp['MJD'][i] < 100: 
            print(ttxt + 'PROBLEM: MJD < 100 for ' + str(exp['NUM'][i]))
            continue

        # Find the ap2D files for all 3 chips
        twodFiles = glob.glob(expdir4 + str(exp['MJD'][i]) + '/ap2D*' + str(exp['NUM'][i]) + '.fits')
        if len(twodFiles) < 1:
            twodFiles = glob.glob(expdir5 + str(exp['MJD'][i]) + '/ap2D*' + str(exp['NUM'][i]) + '.fits')
            if len(twodFiles) < 1:
                print(ttxt + 'PROBLEM: ap2D files not found for exposure ' + str(exp['NUM'][i]) + ', MJD ' + str(exp['MJD'][i]))
                continue
        twodFiles.sort()
        twodFiles = np.array(twodFiles)

        if len(twodFiles) < 3:
            print(ttxt + 'PROBLEM: <3 ap2D files found for exposure ' + str(exp['NUM'][i]) + ', MJD ' + str(exp['MJD'][i]))
            continue
        else:
            print(ttxt + 'ap2D files found for exposure ' + str(exp['NUM'][i]) + ', MJD ' + str(exp['MJD'][i]))

        # Get values from master exposure table
        outstr['PSFID'][i] =   exp['NUM'][i]
        outstr['PLATEID'][i] = exp['PLATEID'][i]
        outstr['CARTID'][i] =  exp['CARTID'][i]
        outstr['DATEOBS'][i] = exp['DATEOBS'][i]
        outstr['MJD'][i] =     exp['MJD'][i]

        # Get ap2D header values
        hdr = fits.getheader(twodFiles[0])
        outstr['EXPTIME'][i] =  hdr['EXPTIME']
        outstr['NREAD'][i] =    hdr['NREAD']
        try:
            outstr['ROTPOS'][i] = hdr['ROTPOS']
        except:
            outstr['ROTPOS'][i] = -9999.999
        try:
            doutstr['SEEING'][i] =   hdr['SEEING']
        except:
            outstr['SEEING'][i] = -9999.999
        outstr['AZ'][i] =       hdr['AZ']
        outstr['ALT'][i] =      hdr['ALT']
        outstr['IPA'][i] =      hdr['IPA']
        outstr['FOCUS'][i] =    hdr['FOCUS']
        outstr['DITHPIX'][i] =  hdr['DITHPIX']
        outstr['LN2LEVEL'][i] = hdr['LN2LEVEL']
        outstr['RELHUM'][i] =   hdr['RELHUM']
        outstr['MKSVAC'][i] =   hdr['MKSVAC']
        outstr['TDETTOP'][i] =  hdr['TDETTOP']
        outstr['TDETBASE'][i] = hdr['TDETBASE']
        outstr['TTENTTOP'][i] = hdr['TTENTTOP']
        outstr['TCLDPMID'][i] = hdr['TCLDPMID']
        outstr['TGETTER'][i] =  hdr['TGETTER']
        outstr['TTLMBRD'][i] =  hdr['TTLMBRD']
        outstr['TLSOUTH'][i] =  hdr['TLSOUTH']
        outstr['TLNORTH'][i] =  hdr['TLNORTH']
        outstr['TLSCAM2'][i] =  hdr['TLSCAM2']
        outstr['TLSCAM1'][i] =  hdr['TLSCAM1']
        outstr['TLSDETC'][i] =  hdr['TLSDETC']
        outstr['TLSDETB'][i] =  hdr['TLSDETB']
        outstr['TPGVAC'][i] =   hdr['TPGVAC']
        outstr['TCAMAFT'][i] =  hdr['TCAMAFT']
        outstr['TCAMMID'][i] =  hdr['TCAMMID']
        outstr['TCAMFWD'][i] =  hdr['TCAMFWD']
        outstr['TEMPVPH'][i] =  hdr['TEMPVPH']
        outstr['TRADSHLD'][i] = hdr['TRADSHLD']
        outstr['TCOLLIM'][i] =  hdr['TCOLLIM']
        outstr['TCPCORN'][i] =  hdr['TCPCORN']
        outstr['TCLDPHNG'][i] = hdr['TCLDPHNG']

        # Loop over the chips
        for ichip in range(nchips):
            pix0 = np.array(refpix[chips[ichip]])
            gpeaks = gaussFitAll(infile=twodFiles[ichip], medianrad=medianrad, pix0=pix0)
            #import pdb; pdb.set_trace()

            success, = np.where(gpeaks['success'] == True)
            print('  ' + os.path.basename(twodFiles[ichip]) + ': ' + str(len(success)) + ' successful Gaussian fits')

            outstr['PIX0'][i, ichip, :] =            pix0
            outstr['GAUSS_HEIGHT'][i, ichip, :] =    gpeaks['pars'][:, 0]
            outstr['E_GAUSS_HEIGHT'][i, ichip, :] =  gpeaks['perr'][:, 0]
            outstr['GAUSS_CENT'][i, ichip, :] =      gpeaks['pars'][:, 1]
            outstr['E_GAUSS_CENT'][i, ichip, :] =    gpeaks['perr'][:, 1]
            outstr['GAUSS_SIGMA'][i, ichip, :] =     gpeaks['pars'][:, 2]
            outstr['E_GAUSS_SIGMA'][i, ichip, :] =   gpeaks['perr'][:, 2]
            outstr['GAUSS_YOFFSET'][i, ichip, :] =   gpeaks['pars'][:, 3]
            outstr['E_GAUSS_YOFFSET'][i, ichip, :] = gpeaks['perr'][:, 3]
            outstr['GAUSS_FLUX'][i, ichip, :] =      gpeaks['sumflux']
            outstr['GAUSS_NPEAKS'][i, ichip] =       len(success)

    Table(outstr).write(outfile, overwrite=True)

    runtime = str("%.2f" % (time.time() - start_time))
    print("\nDone in " + runtime + " seconds.\n")

    return


###################################################################################################
# Function for fitting Gaussians to trace positions of all 300 fibers
###################################################################################################
def gaussFitAll(infile=None, medianrad=None, pix0=None):
    flux = fits.open(infile)[1].data
    error = fits.open(infile)[2].data
    npix = flux.shape[0]

    totflux = np.nanmedian(flux[:, (npix//2) - medianrad:(npix//2) + medianrad], axis=1)
    toterror = np.sqrt(np.nanmedian(error[:, (npix//2) - medianrad:(npix//2) + medianrad]**2, axis=1))
    gpeaks = peakfit.peakfit(totflux, sigma=toterror, pix0=pix0)

    return gpeaks


