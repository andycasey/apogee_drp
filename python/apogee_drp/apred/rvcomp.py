# routines for assessing RVs from pipeline

import os
import copy
import glob
import pdb
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import esutil
import pickle
import yaml
from astropy.io import fits
from ..utils import apload, applot, bitmask, spectra, norm, yanny, gaia
from holtztools import plots, html, match, struct
from dlnpyutils import utils as dln
from scipy import interpolate
from scipy.signal import correlate
from scipy.ndimage.filters import median_filter, gaussian_filter

colors = ['r','g','b','c','m','y','k']
chips = ['a','b','c']


def allField(files=['apo*/*/apField-*.fits','apo*/*/apFieldC-*.fits','lco*/*/apField-*.fits'],out='allField.fits',verbose=False) :
    """ Concatenate set of apField files 
    """
    # concatenate the structures
    all=struct.concat(files,verbose=verbose)

    # write out the file
    if out is not None:
        print('writing',out)
        struct.wrfits(all,out)

    return all

def allFieldVisits(files=['apo*/*/apFieldVisits-*.fits','apo*/*/apFieldC-*.fits','lco*/*/apFieldVisits-*.fits'],out='allFieldVisits.fits',verbose=False) :
    """ Concatenate set of apFieldVisit files
    """
    # concatenate the structures
    all=struct.concat(files,verbose=verbose)

    # write out the file
    if out is not None:
        print('writing',out)
        struct.wrfits(all,out)

    return all


def vscat(a,fig=None,ls=None,marker='o',nmin=2,mhmin=-3,density=False,out=None) :
    """ Make histograms of VSCATTER for different bins of Teff H], given min NVISITS, and min [M/H]
    """
    if fig == None : fig,ax=plots.multi(4,6,hspace=0.001,wspace=0.4,figsize=(12,8))
    else : fig,ax=fig
    tbins=[3000,3500,4000,4500,5500,8000,30000] 
    hbins=[8,11,12,13,15]
    try: snr = a['SNREV']
    except: snr=a['SNR']
    j=np.where(snr > 300) [0]
    snr[j] = 300
    for i in range(len(tbins)-1) :
        ax[i,0].text(0.9,0.9,'{:d}<=RV_TEFF<{:d}'.format(tbins[i],tbins[i+1]),ha='right',transform=ax[i,0].transAxes,fontsize=8)
        for j in range(len(hbins)-1) :
            ax[0,j].set_title('{:d}<=H<{:d}'.format(hbins[j],hbins[j+1]))
            gd = np.where((a['RV_TEFF']>=tbins[i]) & (a['RV_TEFF']<tbins[i+1]) &
                          (a['H']>=hbins[j]) & (a['H']<hbins[j+1]) &
                           (a['NVISITS']>nmin) & (a['RV_FEH']>mhmin) & (a['VSCATTER'] > 0)) [0]
            print(tbins[i],tbins[i+1],hbins[j],hbins[j+1],nmin,len(gd))
            try :
                #plots.plotc(ax[i,2],snr[gd],a['VSCATTER'][gd],a['RV_FEH'][gd],marker=marker,xr=[0,310],yr=[0,1],xt='S/N',yt='VSCATTER')
                ax[i,j].hist(a['VSCATTER'][gd],bins=np.arange(0,1,0.01),ls=ls,histtype='step',color=colors[j],normed=density)
                ax[i,j].set_xlabel('VSCATTER (km/s)')
                ax[i,j].plot([0.1,0.1],ax[i,j].get_ylim())
                #ax[i,1].hist(a['VSCATTER'][gd],bins=np.arange(0,1,0.01),histtype='step',cumulative=True,normed=True,ls=ls,color=colors[j])
                #ax[i,1].set_xlabel('VSCATTER')
            except : pass

    if out is not None : 
        fig.savefig(out+'.png')
        plt.close()

    fig.suptitle('NVISITS>{:d} [M/H]>{:6.2f}'.format(nmin,mhmin))
    return fig,ax

def apolco(a,minfeh=-3,out=None) :
    """  VSCATTER histograms for APO vs LCO
    """
    apo=np.where((a['TELESCOPE'] == 'apo25m') & (a['RV_FEH']>minfeh) )[0]
    fig=vscat(a[apo],marker='o',density=True)
    lco=np.where((a['TELESCOPE'] == 'lco25m') & (a['RV_FEH']>minfeh) )[0]
    vscat(a[lco],fig=fig,ls=':',marker='+',density=True)
    if out is not None : 
        fig[0].savefig(out+'_1.png')
        plt.close()
    i1,i2=match.match(a['APOGEE_ID'][apo],a['APOGEE_ID'][lco])
    print('matched {:d} stars'.format(len(i1)))
    fig,ax=plots.multi(1,2)
    #plots.plotp(ax[0,0],a['SNR'][apo[i1]],a['VHELIO_AVG'][apo[i1]]-a['VHELIO_AVG'][lco[i2]],yr=[-3,3],yt=r'$\Delta$ VHELIO_AVG',xt='S/N')
    #plots.plotp(ax[0,1],a['SNR'][apo[i1]],a['VHELIO_AVG'][apo[i1]]-a['VHELIO_AVG'][lco[i2]],yr=[-50,50],yt=r'$\Delta$ VHELIO_AVG',xt='S/N')
    #plots.plotp(ax[1,0],a['SNR'][apo[i1]],a['VSCATTER'][apo[i1]]-a['VSCATTER'][lco[i2]],yr=[-0.5,0.5],yt=r'$\Delta$ VSCATTER',xt='S/N')
    #plots.plotp(ax[1,1],a['SNR'][apo[i1]],a['VSCATTER'][apo[i1]]-a['VSCATTER'][lco[i2]],yr=[-5,5],yt=r'$\Delta$ VSCATTER',xt='S/N')
    ax[0].hist(a['VHELIO_AVG'][apo[i1]]-a['VHELIO_AVG'][lco[i2]],bins=np.arange(-0.5,0.5,0.02),histtype='step')
    ax[0].set_xlabel(r'$\Delta$ VHELIO_AVG')
    ax[1].hist(a['VSCATTER'][apo[i1]]-a['VSCATTER'][lco[i2]],bins=np.arange(-0.25,0.25,0.01),histtype='step')
    ax[1].set_xlabel(r'$\Delta$ VSCATTER')
    if out is not None : 
        fig.savefig(out+'_2.png')
        plt.close()


def comp(a,b,av=None,bv=None,domatch=True,out=None) :
    """ VSCATTER comparison of two different data sets
    """
    if domatch :
        i1,i2=match.match(a['APOGEE_ID'],b['APOGEE_ID'])
        gd = np.where(a['NVISITS'][i1] == b['NVISITS'][i2])[0]
        a=a[i1[gd]]
        b=b[i2[gd]]

    fig = vscat(a)
    vscat(b,fig=fig,ls=':')
    if out is not None : 
        fig[0].savefig(out+'_1.png')
        plt.close()

    if domatch :
        fig,ax=plots.multi(1,2)
        #plots.plotp(ax[0,0],a['SNR'],a['VHELIO_AVG']-b['VHELIO_AVG'],yr=[-3,3],yt=r'$\Delta$ VHELIO_AVG')
        #plots.plotp(ax[0,1],a['SNR'],a['VHELIO_AVG']-b['VHELIO_AVG'],yr=[-50,50],yt=r'$\Delta$ VHELIO_AVG')
        #plots.plotp(ax[1,0],a['SNR'],a['VSCATTER']-b['VSCATTER'],yr=[-0.5,0.5],yt=r'$\Delta$ VSCATTER')
        #plots.plotp(ax[1,1],a['SNR'],a['VSCATTER']-b['VSCATTER'],yr=[-5,5],yt=r'$\Delta$ VSCATTER')
        ax[0].hist(a['VHELIO_AVG']-b['VHELIO_AVG'],bins=np.arange(-0.5,0.5,0.02),histtype='step')
        ax[0].set_xlabel(r'$\Delta$ VHELIO_AVG')
        ax[1].hist(a['VSCATTER']-b['VSCATTER'],bins=np.arange(-0.5,0.5,0.02),histtype='step')
        ax[1].set_xlabel(r'$\Delta$ VSCATTER')
        if out is not None : 
            fig.savefig(out+'_2.png')
            plt.close()

    return a,b

def visitsum_tel(all) :

    j=np.where(all['TELESCOPE'] == 'apo25m')[0]
    apo= all[j]
    j=np.where(all['TELESCOPE'] == 'lco25m')[0]
    lco= all[j]
    apoobjs = np.array(list(set(apo['APOGEE_ID'])))
    lcoobjs = np.array(list(set(lco['APOGEE_ID'])))
    i1,i2=match.match(apoobjs,lcoobjs)
    vhelio = []
    vscat = []
    verr = []
    sigfiber = []
    vdiff = []
    n = []
    mjd = []
    tel = []
    for i in i1 :
        j=np.where(all['APOGEE_ID'] == apoobjs[i])[0]
        vhelio.append(all['VHELIO'][j].mean())
        vscat.append(all['VHELIO'][j].std())
        verr.append(all['VRELERR'][j].max())
        sigfiber.append(all['FIBERID'][j].std())
        vdiff.extend(all['VHELIO'][j]-all['VHELIO'][j].mean())
        mjd.extend(all['MJD'][j])
        tel.extend(all['TELESCOPE'][j])
        n.append(len(j))

    fig,ax=plots.multi(1,2)
    mjd=np.array(mjd)
    tel=np.array(tel)
    vdiff=np.array(vdiff)
    plots.plotp(ax[0],mjd,vdiff,typeref=tel,types=['apo25m','lco25m'],color=['b','g'],yr=[-1,1])
    j=np.where(tel == 'apo25m')[0]
    ax[1].hist(vdiff[j],color='b',bins=np.arange(-1,1,0.01),histtype='step')
    mjds= [55800, 56130, 56512, 56876, 57230, 57600, 57966, 58360]
    for i in range(len(mjds)-1) :
        j=np.where((tel == 'apo25m') & (mjd >mjds[i]) & (mjd<mjds[i+1]) )[0]
        print(mjds[i],len(j))
        ax[1].hist(vdiff[j],bins=np.arange(-1,1,0.03),histtype='step')

    j=np.where(tel == 'lco25m')[0]
    ax[1].hist(vdiff[j],color='g',bins=np.arange(-1,1,0.01),histtype='step')
    mjds= [57829, 57966, 58360]
    plt.show()
    pdb.set_trace()


def visitsum(all,out=None,minvisit=1) :
    objs = set(all['APOGEE_ID'])
    if out is None :
        vhelio = []
        vscat = []
        verr = []
        sigfiber = []
        vdiff = []
        n = []
        print('n objects: ', len(objs))
        for iobj,obj in enumerate(objs) :
            j = np.where(all['APOGEE_ID'] == obj)[0]
            print(iobj,len(j))
            vhelio.append(all['VHELIO'][j].mean())
            vscat.append(all['VHELIO'][j].std())
            verr.append(all['VRELERR'][j].max())
            sigfiber.append(all['FIBERID'][j].std())
            vdiff.extend(all['VHELIO'][j]-all['VHELIO'][j].mean())
            n.append(len(j))
        vhelio=np.array(vhelio)
        vscat=np.array(vscat)
        verr=np.array(verr)
        sigfiber=np.array(sigfiber)
        vdiff=np.array(vdiff)
        n=np.array(n)
    else :
        vhelio,vscat,verr,sigfiber,vdiff,n = out

    vdiff=np.array(vdiff)
    fig,ax=plots.multi(2,3)
    gd = np.where(n>minvisit)[0]
    ax[0,0].hist(vscat[gd],bins=np.arange(0.01,1,0.01),histtype='step',cumulative=True,normed=True,color='b')
    ax[2,0].hist(vdiff,color='b',bins=np.arange(-1.,1,0.01),histtype='step')
    gd=np.where((n>minvisit) & (verr < 0.2))[0]
    ax[0,0].hist(vscat[gd],bins=np.arange(0.01,1,0.01),histtype='step',cumulative=True,normed=True,color='g')
    ax[2,1].hist(vscat[gd],bins=np.arange(0.01,1,0.01),histtype='step',color='g')
    fig.tight_layout()
    plt.show()
    return vhelio,vscat,verr,sigfiber,vdiff,n


def field(name,dr14=False,dir='./',minvisit=1) :
    """ look at a single field
    """
    all=struct.concat([dir+'/apVisitSum*.fits'])
    if name == 'M67' : locid=[os.environ['APOGEE_REDUX']+'/r8/fields/apo25m/4162//apVisitSum*']
    elif name == 'N188' : locid=[os.environ['APOGEE_REDUX']+'/r8/fields/apo25m/4217//apVisitSum*', 
                                 os.environ['APOGEE_REDUX']+'/r8/fields/apo25m/5067//apVisitSum*']
    alldr14=struct.concat(locid)
    objs = set(all['APOGEE_ID'])
    vhelio = []
    vscat = []
    verr = []
    sigfiber = []
    vdiff = []
    n = []
    dr14vhelio = []
    dr14vscat = []
    dr14sigfiber = []
    dr14n = []
    dr14vdiff = []
    for obj in objs :
        j = np.where(all['APOGEE_ID'] == obj)[0]
        vhelio.append(all['VHELIO'][j].mean())
        vscat.append(all['VHELIO'][j].std())
        verr.append(all['VRELERR'][j].max())
        sigfiber.append(all['FIBERID'][j].std())
        vdiff.extend(all['VHELIO'][j]-all['VHELIO'][j].mean())
        n.append(len(j))
        #print(all['MJD'][j],all['VHELIO'][j])
        j = np.where(alldr14['APOGEE_ID'] == obj)[0]
        dr14vhelio.append(alldr14['VHELIO'][j].mean())
        dr14vscat.append(alldr14['VHELIO'][j].std())
        dr14sigfiber.append(alldr14['FIBERID'][j].std())
        dr14n.append(len(j))
        dr14vdiff.extend(alldr14['VHELIO'][j]-alldr14['VHELIO'][j].mean())
        #print(all['MJD'][j],all['VHELIO'][j],all['VRELERR'][j])
        #print(alldr14['MJD'][j],alldr14['VHELIO'][j],alldr14['VRELERR'][j])
        #pdb.set_trace()
    vhelio=np.array(vhelio)
    vscat=np.array(vscat)
    verr=np.array(verr)
    sigfiber=np.array(sigfiber)
    n=np.array(n)
    dr14vhelio=np.array(dr14vhelio)
    dr14vscat=np.array(dr14vscat)
    dr14sigfiber=np.array(dr14sigfiber)
    dr14n=np.array(dr14n)
    fig,ax=plots.multi(2,3)
    gd =np.where(n > minvisit)[0]
    ax[0,0].hist(vscat[gd],bins=np.arange(0.01,1,0.01),histtype='step',cumulative=True,normed=True,color='b')
    ax[0,0].hist(dr14vscat[gd],bins=np.arange(0.01,1,0.01),histtype='step',cumulative=True,normed=True,color='r')
    gd=np.where((verr < 0.2) & (n>minvisit))[0]
    ax[0,0].hist(vscat[gd],bins=np.arange(0.01,1,0.01),histtype='step',cumulative=True,normed=True,color='g')
    ax[0,0].hist(dr14vscat[gd],bins=np.arange(0.01,1,0.01),histtype='step',cumulative=True,normed=True,color='m')
    ax[2,1].hist(vscat[gd],bins=np.arange(0.01,1,0.01),histtype='step',color='k')
    ax[2,1].hist(dr14vscat[gd],bins=np.arange(0.01,1,0.01),histtype='step',color='r')

    plots.plotc(ax[1,0],vhelio-dr14vhelio,vscat-dr14vscat,verr,xr=[-0.5,0.5],yr=[-0.3,0.3],zr=[0,0.15])
    plots.plotc(ax[0,1],sigfiber,vscat-dr14vscat,verr,zr=[0,0.15],yr=[-0.3,0.3])
    plots.plotc(ax[1,1],vscat,vscat-dr14vscat,verr,zr=[0,0.15],yr=[-0.3,0.3],xr=[0,0.5])
    ax[2,0].hist(vdiff,color='b',bins=np.arange(-1.,1,0.01),histtype='step')
    ax[2,0].hist(dr14vdiff,color='r',bins=np.arange(-1.,1,0.01),histtype='step')
    fig.tight_layout()
    plt.show()


def visitcomp(plate,mjd,indiv=False,apred='test') :
    """ Compare RVs for plate/mjd with DR14 RVs
    """
    #plt.close('all')
    load=apload.ApLoad(apred=apred)
    a=load.apVisitSum(plate,mjd)[1].data

    #dr14=apload.ApLoad(dr='dr14')
    p=yanny.yanny(os.environ['PLATELIST_DIR']+'/platePlans.par',np=True)
    j=np.where(p['PLATEPLANS']['plateid'] == plate)[0][0]
    locid=p['PLATEPLANS']['locationid'][j]
    b=fits.open(os.environ['APOGEE_REDUX']+'/r8/fields/apo25m/{:04d}/apVisitSum-{:04d}-{:05d}.fits'.format(
                   locid,plate,mjd))[1].data

    fig,ax=plots.multi(2,2)
    i1,i2=match.match(a['FIBERID'],b['FIBERID'])
    plots.plotc(ax[0,0],a['FIBERID'][i1],a['VHELIO'][i1]-b['VHELIO'][i2],a['RV_TEFF'][i1],zr=[3500,5500],xt='Fiber',yt=r'$\Delta$ VHELIO')
    plots.plotc(ax[0,1],a['FIBERID'][i1],a['VHELIO'][i1]-b['VHELIO'][i2],a['RV_TEFF'][i1],zr=[3500,5500],yr=[-2.,2.],xt='Fiber',yt=r'$\Delta$ VHELIO')
    plots.plotc(ax[1,0],a['FIBERID'][i1],a['RV_TEFF'][i1]-b['RV_TEFF'][i2],a['RV_TEFF'][i1],zr=[3500,5500],xt='Fiber',yt=r'$\Delta$ RV_TEFF')
    plots.plotc(ax[1,1],a['RV_TEFF'][i1]-b['RV_TEFF'][i2],a['VHELIO'][i1]-b['VHELIO'][i2],a['RV_TEFF'][i1],zr=[3500,5500],xt=r'$\Delta$ RV_TEFF',yt=r'$\Delta$ VHELIO')
    out=load.filename('Plate',chips=True,plate=plate,mjd=mjd)
    outdir=os.path.dirname(out)
    outname=os.path.basename(out).replace('-a','').replace('.fits','_dr14comp.png')
    fig.tight_layout()
    pdb.set_trace()
    print(outdir+'/plots/'+outname)
    fig.savefig(outdir+'/plots/'+outname)

    if indiv :
        va=load.apPlate(plate,mjd)
        vb={}
        for chip in chips :
            tmp=fits.open(os.environ['APOGEE_REDUX']+'/r8/apo25m/{:04d}/{:05d}/apPlate-{:s}-{:04d}-{:05d}.fits'.format(
                   plate,mjd,chip,plate,mjd))
            vb[chip] = tmp

        fig,ax=plots.multi(1,3,hspace=0.3) 
        pfig,pax=plots.multi(1,3,hspace=0.3) 
        wfig,wax=plots.multi(1,3,hspace=0.3) 
        for i in range(len(i1)) :
            fiber = a['FIBERID'][i1[i]]
            if (a['VHELIO'][i1[i]]-b['VHELIO'][i2[i]]) > 0.5 :
              print(fiber,a['VHELIO'][i1[i]],b['VHELIO'][i2[i]],a['RV_TEFF'][i1[i]],b['RV_TEFF'][i2[i]])
              applot.chip(va,ax=ax,row=300-fiber,color='r')
              #applot.chip(va,ax=pax,row=300-fiber,color='r',pixel=True)
              applot.chip(vb,ax=ax,row=300-fiber,color='b')
              #applot.chip(vb,ax=pax,row=300-fiber,color='b',pixel=True)
              for ichip,chip in enumerate(chips) :
                  pax[ichip].plot(va[chip][1].data[300-fiber,:]/vb[chip][1].data[300-fiber,:])
                  wax[ichip].plot(va[chip][4].data[300-fiber,:]-vb[chip][4].data[300-fiber,:])
              plt.show()

              pdb.set_trace()
              for ichip in range(3) :
                  ax[ichip].cla()
                  pax[ichip].cla()
                  wax[ichip].cla()
    plt.close()

def dr14comp(a,b,av,bv):
    """ compare multiple field RVs from, e.g. allField file with DR14
    """
    load=apload.ApLoad(apred='r11')
    dr14=apload.ApLoad(dr='dr14')

    i1,i2=match.match(a['APOGEE_ID'],b['APOGEE_ID'])
    gd = np.where((a['NVISITS'][i1] == b['NVISITS'][i2]) & (a['SNR'][i1]>75) )[0]
    a=a[i1[gd]]
    b=b[i2[gd]]
   
    j=np.argsort(a['VHELIO_AVG']-b['VHELIO_AVG'])
 
    fig,ax=plots.multi(1,3,hspace=0.3) 
    pfig,pax=plots.multi(1,3,hspace=0.3) 
    wfig,wax=plots.multi(1,3,hspace=0.3) 
    chips=['a','b','c']
    for jj in j :
       j1=np.where(av['APOGEE_ID'] == a['APOGEE_ID'][jj])[0]
       j2=np.where(bv['APOGEE_ID'] == a['APOGEE_ID'][jj])[0]
       print(a['APOGEE_ID'][jj],a['RV_TEFF'][jj],b['RV_TEFF'][jj],a['SNR'][jj],b['SNR'][jj])
       for jjj,kkk in zip(j1,j2) : 
           print(av['MJD'][jjj],av['PLATE'][jjj],av['FIELD'][jjj],av['SNR'][jjj],av['FIBERID'][jjj],av['VHELIO'][jjj],av['ESTVHELIO'][jjj])
           print(bv['MJD'][kkk],bv['PLATE'][kkk],bv['FIELD'][kkk],bv['SNR'][kkk],bv['FIBERID'][kkk],bv['VHELIO'][kkk],bv['ESTVHELIO'][kkk])
           va=load.apPlate(int(av['PLATE'][jjj]),av['MJD'][jjj])
           vsum=load.apVisitSum(int(av['PLATE'][jjj]),av['MJD'][jjj])[1].data
           f=np.where(vsum['FIBERID'] == av['FIBERID'][jjj])[0]
           print(vsum['RV_TEFF'][f])
           applot.chip(va,ax=ax,row=300-av['FIBERID'][jjj],color='r')
           applot.chip(va,ax=pax,row=300-av['FIBERID'][jjj],color='r',pixel=True)
           vb={}
           for chip in chips :
             tmp=fits.open(os.environ['APOGEE_REDUX']+'/r8/apo25m/{:04d}/{:05d}/apPlate-{:s}-{:04d}-{:05d}.fits'.format(
               int(bv['PLATE'][kkk]),bv['MJD'][kkk],chip,int(bv['PLATE'][kkk]),bv['MJD'][kkk]))
             vb[chip] = tmp
           vsum=fits.open(os.environ['APOGEE_REDUX']+'/r8/fields/apo25m/{:04d}/apVisitSum-{:04d}-{:05d}.fits'.format(
               int(bv['LOCATION_ID'][kkk]),int(bv['PLATE'][kkk]),bv['MJD'][kkk]))[1].data
           f=np.where(vsum['FIBERID'] == bv['FIBERID'][kkk])[0]
           print(vsum['RV_TEFF'][f])
           applot.chip(vb,ax=ax,row=300-bv['FIBERID'][kkk],color='b')
           applot.chip(vb,ax=pax,row=300-bv['FIBERID'][kkk],color='b',pixel=True)
           for ichip,chip in enumerate(chips) :
               wax[ichip].plot(va[chip][4].data[300-av['FIBERID'][jjj],:]-vb[chip][4].data[300-bv['FIBERID'][kkk],:])
           plt.show()
           pdb.set_trace()

       for ichip in range(3) :
           ax[ichip].cla()
           pax[ichip].cla()
           wax[ichip].cla()

def standards(a,out=None) :
    """ Compare RVs to standards
    """
    stan = fits.open(os.environ['APOGEE_DRP_DIR']+'/data/rv/rvstandards.fits')[1].data
    h=esutil.htm.HTM()
    m1,m2,rad=h.match(a['ra'],a['dec'],stan['ra'],stan['dec'],1./3600.,maxmatch=500)
    fig,ax=plots.multi(1,1)
    ax.hist(a['VHELIO_AVG'][m1]-stan['RV'][m2],histtype='step',bins=np.arange(-1,1,0.1))
    ax.set_xlabel('RV(APOGEE) - RV(lit)')
    if out is not None :
        fig.savefig(out+'.png')
        plt.close()

   
def all(a,name='DR16',dr='dr14') :
    """ Do a series of RV comparisons for input data and previous DR
    """
    grid=[]
    xtit=[]
    load=apload.ApLoad(dr=dr)
    b=load.allStar()[1].data
   
    # vscatter of new RVs
    vscat(a,out='plots/vscat')
    vscat(a,out='plots/vscat5',nmin=5)
    grid.append(['vscat.png','vscat5.png'])
    xtit.append(name+' : VSCATTER')

    # APO/LCO comparison
    apolco(a,out='plots/apolco')
    grid.append(['apolco_1.png','apolco_2.png'])
    xtit.append(name+' : APO (solid) and LCO (dotted), same stars')
    #apolco(a,out='plots/apolco_nolowz',minfeh=-0.6)
    #grid.append(['apolco_nolowz_1.png','apolco_nolowz_2'])
    #xtit.append(name+', no low [Fe/H]: APO (solid) and LCO (dotted)')

    # RV standards
    standards(a,out='plots/rvstan')
    grid.append(['rvstan.png',''])
    xtit.append(name+', comparison with literature RVs')

    # comparison with previous DR
    comp(a,b,domatch=True,out='plots/drcomp')
    grid.append(['drcomp_1.png','drcomp_2.png'])
    xtit.append(name+', comparison with '+dr+' : same stars, same NVISITS, new(solid) '+dr+'(dotted)')

    html.htmltab(grid,ytitle=xtit,file='plots/rv.html')


def visitspec(load,plate,mjd,fiber,gridfile='apg_rvsynthgrid',apstar=False) :
    """ Crude beginnings of an RV routine
    """
    grid = fits.open(os.environ['APOGEE_DRP_DIR']+'/data/synthgrid/'+gridfile+'.fits')
    if gridfile == 'apg_rvsynthgrid' : hdu=1
    elif gridfile == 'apg_rvsynthgrid_v2': hdu=0
    elif apstar : hdu=2
    else : hdu=1
    gridspec=grid[hdu].data
    gridwave = 10.**spectra.fits2vector(grid[hdu].header,2)
    griderr = np.ones(gridspec.shape[0])
    #for ispec in range(gridspec.shape[1]) :
    #    cont = norm.cont(gridspec[:,ispec],griderr)
    #    gridspec[:,ispec] /= cont

    data = load.apVisit(plate,mjd,fiber)

    # compare with DR14 
    comp(a,b,domatch=False,out='plots/dr14all')
    grid.append(['dr14all_1.png',''])
    xtit.append('all stars: DR14 (dotted) and test DR16 (solid)')

    comp(a,b,domatch=True,out='plots/dr14match')
    grid.append(['dr14match_1.png','dr14match_2.png'])
    xtit.append('same stars: DR14 (dotted) and test DR16 (solid)')
    # set bad pixels to nan
    shape=data[1].data.shape
    spec = copy.copy(data[1].data).flatten()
    specerr = copy.copy(data[2].data)
    specwave=data[4].data
    pixmask=bitmask.PixelBitMask()
    bd = np.where( ((data[3].data & pixmask.badval()) > 0) | 
                   ((data[3].data & pixmask.getval('SIG_SKYLINE')) > 0) ) [0]
    spec[bd] = np.nan
    spec = spec.reshape(shape)

    # continuum normalize and sample to grid
    outspec = np.full(len(gridwave),np.nan)
    if not apstar :
        # apVisit wavelengths are reversed
        spec=np.flip(spec)
        specwave=np.flip(specwave)
        specerr=np.flip(specerr)
        for ichip in range(3) :
            cont = norm.cont(spec[ichip,:],specerr[ichip,:])
            spec[ichip,:] /= cont
            gd=np.where(np.isfinite(spec[ichip,:]))[0]
            ip= interpolate.InterpolatedUnivariateSpline(specwave[ichip,gd],spec[ichip,gd],k=3)
            out = ip(gridwave)
            gd = np.where( (gridwave > specwave[ichip,0]) & (gridwave < specwave[ichip,-1]) )[0]
            outspec[gd] = out[gd]
            plt.plot(specwave[ichip,:],spec[ichip,:])
            plt.plot(gridwave[gd],out[gd])
            plt.show()

    for ispec in range(gridspec.shape[1]) :
        print(ispec)
        bd=np.where(np.isnan(outspec))
        outspec[bd]=1.
        out=correlate(outspec,gridspec[:,ispec])
        pdb.set_trace() 

def repeatspec(a) :
    stars=set(a['APOGEE_ID'])
    fig,ax=plots.multi(1,2,hspace=0.001,sharex=True)
    for star in stars :
        j=np.where(a['APOGEE_ID'] == star)[0]
        if len(j) > 1 :
            for i in j :
                print(a['TELESCOPE'][i],a['FIELD'][i],a['NVISITS'][i])
                spec=fits.open(a['TELESCOPE'][i]+'/'+a['FIELD'][i]+'/apStar-r12-'+a['APOGEE_ID'][i]+'.fits')
                if i == j[0] : spec0=copy.copy(spec[1].data[0,:])
                plots.plotl(ax[0],spectra.fits2vector(spec[1].header,1),spec[1].data[0,:])
                plots.plotl(ax[1],spectra.fits2vector(spec[1].header,1),spec[1].data[0,:]/spec0,yr=[0.5,1.5])
            plt.show()
            pdb.set_trace()
            ax[0].cla()
            ax[1].cla()
  
import doppler 
import multiprocessing as mp
from astropy.table import Table, Column
from apogee_drp.apred import bc

def doppler_rv(planfile,survey='apogee',telescope='apo25m',apred='r13',apstar_vers=None,obj=None,
               nobj=0,threads=8,maxvisit=500,snmin=3,nres=[5,4.25,3.5],
               clobber=False,verbose=False,tweak=False,plot=False,windows=None) :
    """ Run DOPPLER RVs for a field
    """ 
  
    plan = yaml.safe_load(open(planfile,'r'))
    if plan['apogee_drp_ver'] != os.environ['APOGEE_DRP_VER'] :
        print('apogee_drp_ver {:s} does not match running version {:s}'.format(plan['apogee_drp_ver'],os.environ['APOGEE_DRP_VER']))
        pdb.set_trace()

    apred = plan['apred_vers']
    if apstar_vers is None : apstar_vers=plan['apstar_vers'] if plan.get('apstar_vers') else 'stars'

    telescope = plan['telescope']
    field = plan['field']
 
    # Get all the VisitSum files for this field and concatenate them
    files = glob.glob(os.environ['APOGEE_REDUX']+'/'+apred+'/visit/'+telescope+'/'+field+'/apVisitSum*')
    if len(files) == 0 :
        print('no apVisitSum files found for {:s}'.format(field))
        return
    else :
        allvisits = struct.concat(files)
    starmask = bitmask.StarBitMask()
    gd = np.where(((allvisits['STARFLAG'] & starmask.badval()) == 0) & 
                  (allvisits['APOGEE_ID'] != b'') &
                  (allvisits['SNR'] > snmin) )[0]
    print(len(allvisits),len(gd))
    allvisits = Table(allvisits)
    # Change datatype of STARFLAG to 64-bit
    allvisits['STARFLAG'] = allvisits['STARFLAG'].astype(np.uint64)

    # Output directory
    load = apload.ApLoad(apred=apred,telescope=telescope)
    outfield = load.filename('Field',field=field)
    if apstar_vers != 'stars' :
        outfield = outfield.replace('/stars/','/'+apstar_vers+'/')
    try : os.makedirs(os.path.dirname(outfield))
    except FileExistsError: pass
    outfieldvisits = load.filename('FieldVisits',field=field)
    if apstar_vers != 'stars' :
        outfieldvisits = outfieldvisits.replace('/stars/','/'+apstar_vers+'/')

    # Get all unique (or requested) objects
    if obj is None :
        if nobj > 0 :
            allobj = set(allvisits['APOGEE_ID'][0:nobj])
        else :
            allobj = set(allvisits['APOGEE_ID'])
    else :
        allobj = obj

    # Output apField structure
    fieldtype = np.dtype([('FILE','S64'),('APOGEE_ID','S20'),('TELESCOPE','S6'),('LOCATION_ID',int),('FIELD','S20'),
                          ('RA',float),('DEC',float),('GLON',float),('GLAT',float),
                          ('J',float),('J_ERR',float),('H',float),('H_ERR',float),('K',float),('K_ERR',float),
                          ('SRC_H','S16'),('WASH_M',float),('WASH_M_ERR',float),('WASH_T2',float),('WASH_T2_ERR',float),
                          ('DDO51',float),('DDO51_ERR',float),('IRAC_3_6',float),('IRAC_3_6_ERR',float),
                          ('IRAC_4_5',float),('IRAC_4_5_ERR',float),('IRAC_5_8',float),('IRAC_5_8_ERR',float),
                          ('WISE_4_5',float),('WISE_4_5_ERR',float),('TARG_4_5',float),('TARG_4_5_ERR',float),
                          ('WASH_DDO51_GIANT_FLAG',int),('WASH_DDO51_STAR_FLAG',int),
                          ('TARG_PMRA',float),('TARG_PMDEC',float),('TARG_PM_SRC','S16'),
                          ('AK_TARG',float),('AK_TARG_METHOD','S32'),
                          ('AK_WISE',float),('SFD_EBV',float),
                          ('APOGEE_TARGET1',int),('APOGEE_TARGET2',int),('APOGEE_TARGET3',int),
                          ('APOGEE2_TARGET1',int),('APOGEE2_TARGET2',int),('APOGEE2_TARGET3',int),('APOGEE2_TARGET4',int),
                          ('TARGFLAGS','S132'),('SURVEY','S16'),('PROGRAMNAME','S32'),
                          ('NINST',int),('NVISITS',int),('COMBTYPE',int),('COMMISS',int),
                          ('SNR',float),('STARFLAG',np.uint64),('STARFLAGS','S132'),('ANDFLAG',np.uint64),('ANDFLAGS','S132'),
                          ('VHELIO_AVG',float),('VSCATTER',float),('VERR',float),
                          ('RV_TEFF',float),('RV_LOGG',float),('RV_FEH',float),('RV_ALPHA',float),('RV_CARB',float),
                          ('RV_CCPFWHM',float),('RV_AUTOFWHM',float),
                          ('N_COMPONENTS',int),('MEANFIB',float),('SIGFIB',float)
                         ])
    allfield = np.zeros(len(allobj),dtype=fieldtype)
    allfield['TELESCOPE'] = telescope
    allfield['FIELD'] = field

    allfiles = []
    allv = []
    nobj = 0
    nvisit = 0
    pixelmask = bitmask.PixelBitMask()

    # loop over requested objects, building up allfiles list of 
    #  [(field,obj,clobber,verbose,tweak,plot,windows),filenames....] to pass to dorv()
    for iobj,star in enumerate(sorted(allobj)) :
        if type(star) is str : star=star.encode()
        allfield['APOGEE_ID'][iobj] = star
        # we will only consider good visits
        visits = np.where(allvisits['APOGEE_ID'][gd] == star)[0]
        print('object: {:}  nvisits: {:d}'.format(star,len(visits)))
        nobj += 1
        nvisit += len(visits)

        if len(visits) > 0 :
            allfiles.append([allvisits[gd[visits]],load,(field,star,clobber,verbose,tweak,plot,windows,apstar_vers)])
    print('total objects: ', nobj, ' total visits: ', nvisit) 

    # Now do the RVs, in parallel if requested
    if threads == 0 :
        output = []
        for speclist in allfiles :
            print(speclist)
            output.append(dorv(speclist))
    else :
        pool = mp.Pool(threads)
        output = pool.map_async(dorv, allfiles).get()
        pool.close()
        pool.join()
    print('done pool')

    # Load up the individual visit RV information

    # First rename old visit RV tags and initialize new ones
    for col in ['VTYPE','VREL','VRELERR','VHELIO','BC','RV_TEFF','RV_LOGG','RV_FEH','RV_CARB','RV_ALPHA'] :
        allvisits.rename_column(col,'EST'+col)
        if col == 'VTYPE' : allvisits[col] = 0
        else : allvisits[col] = np.nan
    for col in ['XCORR_VREL','XCORR_VRELERR','XCORR_VHELIO','BC'] :
        allvisits[col] = np.nan

    # add columns for RV components
    allvisits['N_COMPONENTS'] = -1
    rv_components = Column(name='RV_COMPONENTS',dtype=float,shape=(3),length=len(allvisits))
    allvisits.add_column(rv_components)

    # Now load the new ones with the dorv() output
    allv = []
    for out,files in zip(output,allfiles) :
        if out is not None :
            visits = []
            ncomponents = 0
            for i,(v,g) in enumerate(zip(out[0][1],out[1])) :
                # match by filename components in case there was an error reading in doppler
                name = os.path.basename(v['filename']).replace('.fits','').split('-')
                if telescope == 'apo1m' :
                    visit = np.where( np.char.strip(allvisits['FILE']).astype(str) == os.path.basename(v['filename'].strip()) )[0]
                    if len(visit) == 0 :
                        # special case for incremental release...yuck
                        visit = np.where( np.char.strip(allvisits['FILE']).astype(str) == 
                                    os.path.basename(v['filename'].strip()).replace('-r13-','-r12-') )[0]
                else :
                    visit = np.where( (np.char.strip(allvisits['PLATE']).astype(str) == name[-3]) &
                                      (allvisits['MJD'] == int(name[-2])) &
                                      (allvisits['FIBERID'] == int(name[-1])) )[0]
                if len(visit) > 0 : visit=visit[0]
                else : continue
                visits.append(visit)
                allvisits[visit]['VREL']=v['vrel']
                allvisits[visit]['VRELERR']=v['vrelerr']
                allvisits[visit]['VHELIO']=v['vhelio']
                allvisits[visit]['XCORR_VREL']=v['xcorr_vrel']
                allvisits[visit]['XCORR_VRELERR']=v['xcorr_vrelerr']
                allvisits[visit]['XCORR_VHELIO']=v['xcorr_vhelio']
                allvisits[visit]['BC']=v['bc']
                allvisits[visit]['RV_TEFF']=v['teff']
                allvisits[visit]['RV_LOGG']=v['logg']
                allvisits[visit]['RV_FEH']=v['feh']
                if g is None : allvisits[visit]['N_COMPONENTS']=0
                else : allvisits[visit]['N_COMPONENTS']=g['N_components']
                if allvisits[visit]['N_COMPONENTS'] > 1 :
                    allvisits[visit]['STARFLAG'] |= starmask.getval('MULTIPLE_SUSPECT')
                    n=len(g['best_fit_parameters'])//3
                    gd=np.where(np.array(g['best_fit_parameters'])[0:n] > 0)[0]
                    rv_comp = np.array(g['best_fit_parameters'])[2*n+gd]
                    n_rv_comp = np.min([3,len(rv_comp)])
                    allvisits[visit]['RV_COMPONENTS'][0:n_rv_comp] = rv_comp[0:n_rv_comp]
                # flag visits with suspect RVs
                if allvisits[visit]['RV_TEFF'] < 6000 : bd_diff = 10
                else : bd_diff = 50.
                if (np.abs(allvisits[visit]['VHELIO']-allvisits[visit]['XCORR_VHELIO']) > bd_diff) :
                    allvisits[visit]['STARFLAG'] |= starmask.getval('RV_REJECT')
                elif (np.abs(allvisits[visit]['VHELIO']-allvisits[visit]['XCORR_VHELIO']) > 0) :
                    allvisits[visit]['STARFLAG'] |= starmask.getval('RV_SUSPECT')

            if len(visits) > 0 :
                visits = np.array(visits)
                # set up visit combination, removing visits with suspect RVs
                apogee_id = files[-1][1].decode() 
                gdrv = np.where((allvisits[visits]['STARFLAG'] & starmask.getval('RV_REJECT')) == 0)[0]
                if len(gdrv) > 0 : 
                    allv.append([allvisits[visits[gdrv]],load,(field,apogee_id,clobber,apstar_vers,nres)])

    # Do the visit combination, in parallel if requested
    if threads == 0 :
        output = []
        for v in allv :
            output.append(dovisitcomb(v))
    else :
        pool = mp.Pool(threads)
        output = pool.map_async(dovisitcomb, allv).get()
        pool.close()
        pool.join()
    print('done visitcomb pool pool')

    # Now load the combined star information into allfield structure
    # Note that dovisitcomb() returns an apstar structure, with header
    # information in FITS header, which limits card names to 8 characters
    # Some of these are renamed in allField structure to use different
    # (longer, more clear) names
    for apstar,v in zip(output,allv) :
        j = np.where(allfield['APOGEE_ID'] == v[-1][1].encode())[0]

        # Basic target information
        try: allfield['APOGEE_ID'][j] = apstar.header['OBJID']
        except: allfield['APOGEE_ID'][j] = v[-1][1]
        keys = ['RA','DEC','J','J_ERR','H','H_ERR','K','K_ERR',
                'SRC_H','WASH_M','WASH_M_ERR','WASH_T2','WASH_T2_ERR',
                'DDO51','DDO51_ERR','IRAC_3_6','IRAC_3_6_ERR',
                'IRAC_4_5','IRAC_4_5_ERR','IRAC_5_8','IRAC_5_8_ERR',
                'WISE_4_5','WISE_4_5_ERR','TARG_4_5','TARG_4_5_ERR',
                'WASH_DDO51_GIANT_FLAG','WASH_DDO51_STAR_FLAG',
                'AK_TARG','AK_TARG_METHOD','AK_WISE','SFD_EBV']
        for key in keys :
            try: allfield[key][j] = v[0][0][key]
            except KeyError: pass

        # Rename targeting proper motions
        keys = ['PMRA','PMDEC','PM_SRC']
        for key in keys :
            try: allfield['TARG_'+key][j] = v[0][0][key]
            except KeyError: pass

        # Targeting flags have different names
        apogee_target1 = apstar.header['APTARG1']
        apogee_target2 = apstar.header['APTARG2']
        apogee_target3 = apstar.header['APTARG3']
        apogee2_target1 = apstar.header['AP2TARG1']
        apogee2_target2 = apstar.header['AP2TARG2']
        apogee2_target3 = apstar.header['AP2TARG3']
        apogee2_target4 = apstar.header['AP2TARG4']
        allfield['APOGEE_TARGET1'][j] = apogee_target1
        allfield['APOGEE_TARGET2'][j] = apogee_target2
        allfield['APOGEE_TARGET3'][j] = apogee_target3
        allfield['APOGEE2_TARGET1'][j] = apogee2_target1
        allfield['APOGEE2_TARGET2'][j] = apogee2_target2
        allfield['APOGEE2_TARGET3'][j] = apogee2_target3
        allfield['APOGEE2_TARGET4'][j] = apogee2_target4
        # Add character string for target flags
        allfield['TARGFLAGS'][j] = (bitmask.targflags(apogee_target1,apogee_target2,apogee_target3,0,survey='apogee')+
                                    bitmask.targflags(apogee2_target1,apogee2_target2,apogee2_target3,apogee2_target4,survey='apogee2'))
        # Some modified names
        allfield['N_COMPONENTS'][j] = apstar.header['N_COMP']
        allfield['VHELIO_AVG'][j] = apstar.header['VHELIO']

        # Mostly unmodified names
        for key in ['STARFLAG','ANDFLAG','SNR','VSCATTER','VERR','RV_TEFF','RV_LOGG','RV_FEH','NVISITS','MEANFIB','SIGFIB' ] :
            allfield[key][j] = apstar.header[key]
        # Add character string for star flags
        allfield['STARFLAGS'][j] = starmask.getname(allfield['STARFLAG'][j])
        allfield['ANDFLAGS'][j] = starmask.getname(allfield['ANDFLAG'][j])

        # Tags that are not from apStar
        allfield['SURVEY'][j] =  ','.join(set(v[0]['SURVEY']))
        allfield['PROGRAMNAME'][j] = ','.join(set(v[0]['PROGRAMNAME']))

    # Add GAIA information
    allfield = gaia.add_gaia(allfield)

    # Output apField and apFieldVisits
    hdulist = fits.HDUList()
    hdulist.append(fits.table_to_hdu(Table(allfield)))
    hdulist.writeto(outfield,overwrite=True)

    hdulist=fits.HDUList()
    hdulist.append(fits.table_to_hdu(allvisits))
    hdulist.writeto(outfieldvisits,overwrite=True)

    # Make web page
    if obj is not None : suffix='_obj'
    else : suffix=''
    if tweak: suffix=suffix+'_tweak'
    print('making HTML page ....')
    mkhtml(field,suffix=suffix,apred=apred,telescope=telescope,apstar_vers=apstar_vers)

    return allfield,allvisits



def doppler_rv_star(star,apred,telescope,nres=[5,4.25,3.5],windows=None,tweak=False,
                    clobber=False,verbose=False,plot=False,logger=None):
    """
    Run Doppler on one star and perform visit combination.

    Parameters
    ----------
    star : str
       The '2M' star name.
    apred : str
       APOGEE reduction version.
    telescope : str
       APOGEE telescope (apo25m, loc25m, apo1m).
    nres : array, optional
       Array of sinc widths.  Default is nres=[5,4.25,3.5].
    windows : array, optional
       Array of spectral windows to use.
    tweak : bool, optional
       Have Doppler tweak the continuum with the best-fit template.  Default is False.
    clobber : bool, optional
       Overwrite any existing files.
    verbose : bool, optional
       Verbose output to the screen.
    plot : bool, optional
       Make a plot of spectrum and best-fitting template.
    logger : logger, optional
       A logger for printed output.

    Returns
    -------
    The program outputs Doppler files an apStar combined file to the appropriate
    place specified in the SDSS/APOGEE tree product.

    """

    if logger is None:
        logger = dln.basiclogger()

    snmin = 3
    apstar_vers = 'stars'

    logger.info('Running Doppler and performing visit combination for %s and telescope=%s' % (apogee_id,telescope))

    # Get the visit files for this star and telescope
    db = apogeedb.DBSession()
    allvisits = db.query('visit',cols='*',where="apogee_id='"+star+"' and telescope='"+telescope+"'")
    nallvisits = len(allvisits)
    if nallvisits==0:
        logger.info('No visit files found')
        sys.exit()
    logger.info('%d visit files found' % nallvisits)

    # Select good visit spectra
    starmask = bitmask.StarBitMask()
    gd, = np.where(((allvisits['starflag'] & starmask.badval()) == 0) &
                   (allvisits['snr'] > snmin) )
    if len(gd)==0:
        logger.info('No visits pass QA cuts')
        sys.exit()
    logger.info('%d visits pass QA cuts' % len(gd))
    starvisits = Table(allvisits[gd])
    nvisits = len(gd)
    # Change datatype of STARFLAG to 64-bit
    starvisits['starflag'] = starvisits['starflag'].astype(np.uint64)

    # Output directory
    load = apload.ApLoad(apred=apred,telescope=telescope)
    starfile = load.filename('Star',obj=star)
    stardir = os.path.dirname(starfile)
    try : os.makedirs(os.path.dirname(stardir))
    except FileExistsError: pass

    # Run Doppler with dorv()
    try:
        dopsumstr,dopvisitstr,gaussout = dorv(starvisits,clobber=clobber,verbose=verbose,tweak=tweak,plot=plot,
                                              windows=windows,apstar_vers=apstar_vers,logger=logger)
        logger.info('Doppler completed successfully for {:s}'.format(star))
    except:
        logger.info('Doppler failed for {:s}'.format(star))
        raise


    # First rename old visit RV tags and initialize new ones
    for col in ['vtype','vre','vrelerr','vhelio','bc','rv_teff','rv_logg','rv_feh','rv_carb','rv_alpha']:
        starvisits.rename_column(col,'est'+col)
        if col == 'vtype':
            starvisits[col] = 0
        else:
            starvisits[col] = np.nan
    for col in ['xcorr_vrel','xcorr_vrelerr','xcorr_vhelio','bc']:
        starvisits[col] = np.nan

    # Add columns for RV components
    starvisits['n_components'] = -1
    rv_components = Column(name='rv_components',dtype=float,shape=(3),length=len(starvisits))
    starvisits.add_column(rv_components)

    # Now load the new ones with the dorv() output
    allv = []
    visits = []
    ncomponents = 0
    files = speclist
    for i,(v,g) in enumerate(zip(dopvisitstr,gaussout)) :
        # Match by filename components in case there was an error reading in doppler
        name = os.path.basename(v['filename']).replace('.fits','').split('-')
        if telescope == 'apo1m':
            vind, = np.where( np.char.strip(starvisits['file']).astype(str) == os.path.basename(v['filename'].strip()) )
            if len(vind) == 0:
                # special case for incremental release...yuck
                vind, = np.where( np.char.strip(starvisits['file']).astype(str) == 
                                   os.path.basename(v['filename'].strip()).replace('-r13-','-r12-') )
        else:
            vind, = np.where( (np.char.strip(starvisits['plate']).astype(str) == name[-3]) &
                               (starvisits['mjd'] == int(name[-2])) &
                               (starvisits['fiberid'] == int(name[-1])) )
        if len(vind) > 0:
            vind = vind[0]
        else:
            continue
        visits.append(vind)
        starvisits[vind]['vrel'] = v['vrel']
        starvisits[vind]['vrelerr'] = v['vrelerr']
        starvisits[vind]['vhelio'] = v['vhelio']
        starvisits[vind]['xcorr_vrel'] = v['xcorr_vrel']
        starvisits[vind]['xcorr_vrelerr'] = v['xcorr_vrelerr']
        starvisits[vind]['xcorr_vhelio'] = v['xcorr_vhelio']
        starvisits[vind]['bc'] = v['bc']
        starvisits[vind]['rv_teff'] = v['teff']
        starvisits[vind]['rv_logg'] = v['logg']
        starvisits[vind]['rv_feh'] = v['feh']
        if g is None:
            starvisits[vind]['n_components'] = 0
        else:
            starvisits[vind]['n_components'] = g['N_components']
        if starvisits[vind]['n_components'] > 1 :
            starvisits[vind]['starflag'] |= starmask.getval('multiple_suspect')
            n = len(g['best_fit_parameters'])//3
            gd, = np.where(np.array(g['best_fit_parameters'])[0:n] > 0)
            rv_comp = np.array(g['best_fit_parameters'])[2*n+gd]
            n_rv_comp = np.min([3,len(rv_comp)])
            starvisits[vind]['rv_components'][0:n_rv_comp] = rv_comp[0:n_rv_comp]
        # flag visits with suspect RVs
        if starvisits[vind]['rv_teff'] < 6000:
            bd_diff = 10
        else:
            bd_diff = 50.
        if (np.abs(starvisits[vind]['vhelio']-starvisits[vind]['xcorr_vhelio']) > bd_diff) :
            starvisits[vind]['starflag'] |= starmask.getval('rv_reject')
        elif (np.abs(starvinds[visit]['vhelio']-starvinds[visit]['xcorr_vhelio']) > 0) :
            starvinds[visit]['starflag'] |= starmask.getval('rv_suspect')

    # Get the good visits
    if len(visits)>0:
        visits = np.array(visits)
        gdrv, = np.where((starvisits[visits]['starflag'] & starmask.getval('rv_reject')) == 0)        

    # Do the visit combination
    if len(gdrv)>0:
        apstar = visitcomb(starvisits[visits[gdrv]],load=load,clobber=clobber,apstar_vers=apstar_vers,
                           nres=nres,logger=logger,logger=logger)
    else:
        logger.info('No good visits for '+star)
        raise

    return


def dorv(allvisit,obj=None,telescope=None,apred=None,clobber=False,verbose=False,tweak=False,
         plot=False,windows=None,apstar_vers='stars',logger=None):
    """ Do the Doppler rv jointfit from list of files
    """

    if logger is None:
        logger = dln.basiclogger()

    if type(obj) is not str:
        obj = obj.decode('UTF-8')
    if tweak==True:
        suffix = '_tweak'
    else:
        suffix = '_out'
    if obj is None:
        obj = allvisit['apogee_id'][0]
    if apred is None:
        apred = allvisit['apred_vers'][0]
    if telescope is None:
        telescope = allvisit['telescope'][0]
    load = apload.ApLoad(apred=apred,telescope=telescope)
    outdir = os.path.dirname(load.filename('Star',obj=obj))
    if apstar_vers != 'stars':
        outdir = outdir.replace('/stars/','/'+apstar_vers+'/')

    if os.path.exists(outdir+'/'+obj+suffix+'_doppler.pkl') and not clobber:
        logger.info(obj+' already done')
        fp = open(outdir+'/'+obj+suffix+'_doppler.pkl','rb')
        try: 
            out = pickle.load(fp)
            sumstr,finalstr,bmodel,specmlist,gout = out
            fp.close()
            return sumstr,finalstr,gout
        except: 
            print('error loading: ', obj+suffix+'_doppler.pkl')
            pass

    speclist = []
    pixelmask = bitmask.PixelBitMask()
    badval = pixelmask.badval()|pixelmask.getval('SIG_SKYLINE')|pixelmask.getval('LITTROW_GHOST')
   
    # If we have a significant number of low S/N visits, combine first using
    #    barycentric correction only, use that to get an estimate of systemic
    #    velocity, then do RV determination restricting RVs to within 50 km/s
    #    of estimate. This seems to help significant for faint visits
    lowsnr_visits = np.where(allvisit['SNR']<10)[0]
    if (len(lowsnr_visits) > 1) & (len(lowsnr_visits)/len(allvisit) > 0.1) :
        try :
            apstar_bc = visitcomb(allvisit,bconly=True,load=load,write=False,dorvfit=False,apstar_vers=apstar_vers) 
            apstar_bc.setmask(badval)
            spec = doppler.Spec1D(apstar_bc.flux[0,:],err=apstar_bc.err[0,:],bitmask=apstar_bc.bitmask[0,:],
                                  mask=apstar_bc.mask[0,:],wave=apstar_bc.wave,lsfpars=np.array([0]),
                                  lsfsigma=apstar_bc.wave/22500/2.354,instrument='APOGEE',
                                  filename=apstar_bc.filename)
            logger.info('Lots of low-S/N visits. Running BC jointfit for :',obj)
            out = doppler.rv.jointfit([spec],verbose=verbose,plot=plot,tweak=tweak,maxvel=[-500,500])
            rvrange = [out[1][0]['vrel']-50, out[1][0]['vrel']+50]
        except :
            logger.info('  BC jointfit failed')
            rvrange = [-500,500]
    elif allvisit['h'].max() > 13.5 : 
        # If it's faint, restrict to +/- 500 km/s
        rvrange = [-500,500]
    else:
        # Otherwise, restrict to +/ 1000 km/s
        rvrange = [-1000,1000]

    # Loop over visits
    for i in range(len(allvisit)):

        visitfile = allvisit['file'][i]

        ## Load all of the visits into doppler Spec1D objects
        #if load.telescope == 'apo1m' :
        #    visitfile = load.allfile('Visit',plate=allvisit['plate'][i],
        #                            mjd=allvisit['mjd'][i],reduction=allvisit['apogee_id'][i])
        #else :
        #    visitfile = load.allfile('Visit',plate=int(allvisit['plate'][i]),
        #                             mjd=allvisit['mjd'][i],fiber=allvisit['fiberid'][i])
        spec = doppler.read(visitfile,badval=badval)

        if windows is not None :
            # If we have spectral windows to mask, do so here
            for ichip in range(3) :
                mask = np.full_like(spec.mask[:,ichip],True)
                gd = []
                for window in windows :
                    gd.extend(np.where((spec.wave[:,ichip] > window[0]) & (spec.wave[:,ichip] < window[1]))[0])
                mask[gd] = False
                spec.mask[:,ichip] |= mask
                 
        if spec is not None : speclist.append(spec)

    # Now do the Doppler jointfit to get RVs
    # Dump empty pickle to stand in case of failure (to prevent redo if not clobber)
    try:
        # Dump empty pickle to stand in case of failure (to prevent redo if not clobber)
        fp = open(outdir+'/'+obj+suffix+'_doppler.pkl','wb')
        pickle.dump(None,fp)
        fp.close()
        logger.info('Running Doppler jointfit for : {:s}  rvrange:[{:.1f},{:.1f}]  nvisits: {:d}'.format(obj,*rvrange,len(speclist)))
        sumstr,finalstr,bmodel,specmlist = doppler.rv.jointfit(speclist,maxvel=rvrange,verbose=verbose,
                                                               plot=plot,saveplot=plot,outdir=outdir+'/',tweak=tweak)
        logger.info('Running CCF decomposition for :'+obj)
        gout = gauss_decomp(finalstr,phase='two',filt=True)
        fp = open(outdir+'/'+obj+suffix+'_doppler.pkl','wb')
        pickle.dump([sumstr,finalstr,bmodel,specmlist,gout],fp)
        fp.close()
        # Making plots
        logger.info('Making plots for :'+obj+' '+outdir)
        try: os.makedirs(outdir+'/plots/')
        except: pass
        dop_plot(outdir+'/plots/',obj,[sumstr,finalstr,bmodel,specmlist],decomp=gout)
    except KeyboardInterrupt: 
        raise
    except ValueError as err:
        logger.error('Exception raised in dorv for: '+obj)
        logger.error("ValueError: {0}".format(err))
        return
    except RuntimeError as err:
        logger.error('Exception raised in dorv for: '+obj)
        logger.error("Runtime error: {0}".format(err))
        return
    except :
        raise
        logger.error('Exception raised in dorv for: ', field, obj)
        return

    # Return summary RV info, visit RV info, decomp info 
    return sumstr,finalstr,gout


def dovisitcomb(allvisit,obj=None,clobber=False,apstar_vers='stars',
                nres=[5,4.25,3.5],logger=None):
    """ Routine to do visit combination in parallel
    """

    if logger is None:
        logger = dln.basiclogger()

    if obj is None:
        obj = allvisit['apogee_id'][0]
    telescope = allvisit['telescope'][0]
    apred = allvisit['apred_vers'][0]
    load = apload.ApLoad(apred=apred,telescope=telescope)
    pixelmask = bitmask.PixelBitMask()

    # Already done?
    outdir = os.path.dirname(load.filename('Star',obj=obj))
    if apstar_vers != 'stars' :
        outdir = outdir.replace('/stars/','/'+apstar_vers+'/')
    if os.path.exists(outdir+'/'+obj+'_doppler.fits') and not clobber:
        logger.info(obj+' already done visitcomb')
        fp = open(outdir+'/'+obj+'.pkl','rb')
        try: 
            out = pickle.load(fp)
            fp.close()
            return out
        except: 
            logger.info('error loading: '+obj+'.pkl')
            pass

    # Do the combination
    apstar = visitcomb(allvisit,load=load,plot=False,apstar_vers=apstar_vers,nres=nres)

    # dump
    pickle.dump(apstar,open(outdir+'/'+apogee_id+'.pkl','wb'))

    return apstar

def gaussian(amp, fwhm, mean):
    """ Gaussian as defined by gausspy
    """
    return lambda x: amp * np.exp(-4. * np.log(2) * (x-mean)**2 / fwhm**2)

import gausspy.gp as gp

def gauss_decomp(out,phase='one',alpha1=0.5,alpha2=1.5,thresh=[4,4],plot=None,filt=False) :
    """ Do Gaussian decomposition of CCF using gausspy

        Parameters:
        out : list of dictionaries for each frame, giving x_ccf, ccf, and ccferr
        phase : gausspy paramater
        alpha1 : gausspy parameter
        alpha2 : gausspy parameter for second set of gaussians if phase=='two'
        thresh : gausspy parameter
        plot (str) : if not None, do plot and use as root file name for plot
        filt (bool) : if true, apply filtering to remove components judged to be insignificant
    """
    g = gp.GaussianDecomposer()
    g.set('phase',phase)
    g.set('SNR_thresh',thresh)
    g.set('alpha1',alpha1)
    g.set('alpha2',alpha2)
    gout=[]
    if plot is not None : fig,ax=plots.multi(1,len(out),hspace=0.001,figsize=(6,2+n))
    for i,final in enumerate(out) :
        gd=np.where(np.isfinite(final['x_ccf']))[0]
        x=final['x_ccf'][gd]
        y=final['ccf'][gd] 
        # high pass filter for better performance
        if filt : final['ccf'][gd]-= gaussian_filter(final['ccf'][gd],50,mode='nearest')
        try : 
            decomp=g.decompose(x,final['ccf'][gd],final['ccferr'][gd])
            n=decomp['N_components']
        except :
            print('Exception in Gaussian decomposition, setting to 0 components')
            n=0
            decomp=None
        if filt and n>0 :
            # remove components if they are within width of brighter component, or <0.25 peak ,
            #   or more than twice as wide, or if primary component is wide
            for j in range(1,n) :
                pars_j = decomp['best_fit_parameters'][j::n]
                for k in range(j) :
                    pars_k = decomp['best_fit_parameters'][k::n]
                    if (pars_j[0]>pars_k[0] and pars_k[0]>0 and 
                                (abs(pars_j[2]-pars_k[2])<abs(pars_j[1])  or 
                                 pars_k[0]<0.25*pars_j[0] or 
                                 abs(pars_j[1])>100 or
                                 np.abs(pars_k[1])>2*np.abs(pars_j[1]) ) ) :
                        decomp['best_fit_parameters'][k] = 0
                        decomp['N_components'] -= 1
                    elif (pars_k[0]>pars_j[0] and pars_j[0]>0 and
                                (abs(pars_j[2]-pars_k[2])<abs(pars_k[1]) or 
                                 pars_j[0]<0.25*pars_k[0] or 
                                 abs(pars_k[1])>100 or
                                 np.abs(pars_j[1])>2*np.abs(pars_k[1]) ) )  :
                        decomp['best_fit_parameters'][j] = 0
                        pars_j = decomp['best_fit_parameters'][j::n]
                        decomp['N_components'] -= 1
                  
        gout.append(decomp)
        if plot is not None:
            plots.plotl(ax[i],final['x_ccf'],final['ccf'])
            ax[i].plot(final['x_ccf'],final['ccferr'],color='r')
            for j in range(n) :
                pars=gout[i]['best_fit_parameters'][j::n]
                ax[i].plot(x,gaussian(*pars)(x))
                if pars[0] > 0 : color='k'
                else : color='r'
                ax[i].text(0.1,0.8-j*0.1,'{:8.1f}{:8.1f}{:8.1f}'.format(*pars),transform=ax[i].transAxes,color=color)
            fig.savefig(plot+'_ccf.png')
    del g
    return gout


def dop_plot(outdir,obj,dopout,decomp=None) :
    """ RV diagnostic plots
    """
    sumstr,finalstr,bmodel,specmlist = dopout

    matplotlib.use('Agg')
    n = len(bmodel)
    # Plot final spectra and final models
    # full spectrum
    fig,ax = plots.multi(1,n,hspace=0.001,figsize=(8,2+n))
    ax = np.atleast_1d(ax)
    # continuum
    figc,axc = plots.multi(1,n,hspace=0.001,figsize=(8,2+n))
    axc = np.atleast_1d(axc)
    # windows
    windows = [[15700,15780],[15850,16000],[16700,16930]]
    fig2,ax2 = plots.multi(len(windows),n,hspace=0.001,wspace=0.001,figsize=(12,2+n))
    ax2 = np.atleast_2d(ax2)

    # Loop over visits
    for i,(mod,spec) in enumerate(zip(bmodel,specmlist)) :
        ax[i].plot(spec.wave,spec.flux,color='k')
        for iorder in range(3) :
            gd = np.where(~spec.mask[:,iorder])[0]
            ax[i].plot(spec.wave[gd,iorder],spec.flux[gd,iorder],color='g')
        ax[i].plot(mod.wave,mod.flux,color='r')
        ax[i].text(0.1,0.1,'{:d}'.format(spec.head['MJD5']),transform=ax[i].transAxes)
        for iwind,wind in enumerate(windows) :
            ax2[i,iwind].plot(spec.wave,spec.flux,color='k')
            for iorder in range(3) :
                gd = np.where(~spec.mask[:,iorder])[0]
                ax2[i,iwind].plot(spec.wave[gd,iorder],spec.flux[gd,iorder],color='g')
            ax2[i,iwind].plot(mod.wave,mod.flux,color='r')
            ax2[i,iwind].set_xlim(wind[0],wind[1])
            ax2[i,iwind].set_ylim(0.5,1.3)
            if iwind == 0 : ax2[i,iwind].text(0.1,0.1,'{:d}'.format(spec.head['MJD5']),transform=ax2[i,0].transAxes)
        axc[i].plot(spec.wave,spec.flux*spec.cont,color='k')
        axc[i].plot(spec.wave,spec.cont,color='g')
        axc[i].text(0.1,0.1,'{:d}'.format(spec.head['MJD5']),transform=axc[i].transAxes)
    fig.savefig(outdir+'/'+obj+'_spec.png')
    plt.close()
    fig2.savefig(outdir+'/'+obj+'_spec2.png')
    plt.close()
    figc.savefig(outdir+'/'+obj+'_cont.png')
    plt.close()

    # Plot cross correlation functions with final model
    fig,ax = plots.multi(1,n,hspace=0.001,figsize=(6,2+n))
    ax = np.atleast_1d(ax)
    vmed = np.median(out[1]['vrel'])
        for i,(final,spec) in enumerate(zip(finalstr,specmlist)) :
        ax[i].plot(final['x_ccf'],final['ccf'],color='k')
        ax[i].plot(final['x_ccf'],final['ccferr'],color='r')
        ax[i].plot([final['vrel'],final['vrel']],ax[i].get_ylim(),color='g',label='fit RV')
        ax[i].plot([final['xcorr_vrel'],final['xcorr_vrel']],ax[i].get_ylim(),color='r',label='xcorr RV')
        ax[i].text(0.1,0.9,'{:d}'.format(spec.head['MJD5']),transform=ax[i].transAxes)
        ax[i].set_xlim(vmed-200,vmed+200)
        ax[i].legend()
        if decomp is not None :
            try: n=decomp[i]['N_components']
            except: n=0
            if n>0 : n=len(decomp[i]['best_fit_parameters'])//3
            x = final['x_ccf']
            for j in range(n) :
                pars = decomp[i]['best_fit_parameters'][j::n]
                ax[i].plot(x,gaussian(*pars)(x))
                if pars[0] > 0 : color='k'
                else : color='r'
                ax[i].text(0.1,0.8-j*0.1,'{:8.1f}{:8.1f}{:8.1f}'.format(*pars),transform=ax[i].transAxes,color=color)
    fig.savefig(outdir+'/'+obj+'_ccf.png')
    plt.close()


from scipy.signal import convolve
def dop_comp(field) :
    """ Compare RVs from different data releases
    """
    dop = fits.open(field+'/'+field+'_rv.fits')
    r13 = apload.ApLoad(apred='r13')
    old = r13.apField(field)

    i1,i2 = match.match(dop[1].data['APOGEE_ID'],old[1].data['APOGEE_ID'])
    print(len(dop[1].data),len(old[1].data),len(i1))

    fig,ax=plots.multi(1,1)
    plots.plotc(ax,dop[1].data['RV_TEFF'][i1],dop[1].data['VHELIO_AVG'][i1]-old[1].data['VHELIO_AVG'][i2],dop[1].data['VSCATTER'][i1])

    j=np.argsort(np.abs(dop[1].data['VHELIO_AVG'][i1]-old[1].data['VHELIO_AVG'][i2],dop[1].data['VSCATTER'][i1]))

    plots._data = dop[1].data
    plots._id_cols=['APOGEE_ID']
    plots.event(fig)
    key=' '
    sf,sax=plots.multi(1,2,sharex=True,hspace=0.001)
    while key != 'e' :
        x,y,key,index = plots.mark(fig,index=True)
        obj = dop[1].data['APOGEE_ID'][i1[index]]
        #jv = np.where(dop[2].data['APOGEE_ID'] == dop[1].data['APOGEE_ID'][i1])[0]
        out=pickle.load(open(field+'/'+obj+'_out.pkl','rb'))
        print(obj,old[1].data['APOGEE_ID'][i2[index]])
        print(out[0])
        sax[0].cla()
        spec=old[2].data['SPEC'][i2[index]]
        plots.plotl(sax[0],old[3].data['WAVE'][0,:],spec/convolve(spec,np.ones(500)/500,mode='same'),xr=[15000,17000],yr=[0.5,1.5])
        for mod,obs in zip(out[2],out[3]) :
            sax[1].cla()
            for chip in range(3) :
                plots.plotl(sax[1],obs.wave[:,chip],obs.flux[:,chip],color='k',yr=[0.5,1.5])
                gd = np.where(obs.mask[:,chip] == False)[0]
                plots.plotl(sax[1],obs.wave[gd,chip],obs.flux[gd,chip],color='g')
                plots.plotl(sax[1],mod.wave[:,chip],mod.flux[:,chip],color='r')
            plt.draw()
            input('hit a key: ')

def mkhtml(field,suffix='',apred='r13',telescope='apo25m',apstar_vers='stars') :
    """ Make web pages with tables/plots of RV output
        c.f., Doppler vs IDL
    """

    starmask=bitmask.StarBitMask()
    # get new RV results
    load=apload.ApLoad(apred=apred,telescope=telescope)
    #apf=load.apField(field)[1].data
    infile=load.filename('Field',field=field)
    if apstar_vers != 'stars' :
        infile=infile.replace('/stars/','/'+apstar_vers+'/')
    apf=fits.open(infile)[1].data

    infile=load.filename('FieldVisits',field=field)
    if apstar_vers != 'stars' :
        infile=infile.replace('/stars/','/'+apstar_vers+'/')
    #apfv=load.apFieldVisits(field)[1].data
    apfv=fits.open(infile)[1].data

    outdir=os.path.dirname(infile)
    try: os.makedirs(outdir+'/plots/')
    except: pass
 
    # get old IDLresults
    r13 = apload.ApLoad(apred='r13',telescope=telescope)
    try :
        apfieldvisits = r13.apFieldVisits(field)[1].data
        apfield = r13.apField(field)[1].data
        doapfield = True
    except : 
        print('No apField files found ...')
        doapfield = False

    # match
    if doapfield: i1,i2 = match.match(apfv['FILE'],apfieldvisits['FILE'])
    fig,ax=plots.multi(1,2,figsize=(12,4),hspace=0.5)
    ax[0].hist(apf['VHELIO_AVG'],bins=np.arange(-600,600,5),label='doppler',color='g',histtype='step')
    if doapfield: ax[0].hist(apfield['VHELIO_AVG'],bins=np.arange(-600,600,5),label='IDL',color='r',histtype='step')
    ax[0].legend()
    ax[0].set_xlabel('VHELIO_AVG')
    ax[1].hist(apf['VSCATTER'],bins=np.arange(0,5,0.02),label='doppler',color='g',histtype='step')
    if doapfield: ax[1].hist(apfield['VSCATTER'],bins=np.arange(0,1,0.02),label='IDL',color='r',histtype='step')
    ax[1].legend()
    ax[1].set_xlabel('VSCATTER')
    fig.savefig(outdir+'/plots/'+field+'_rvhist.png')

    # create HTML and loop over objects
    fp=open(outdir+'/'+field+suffix+'.html','w')
    fp.write('<HTML>\n')
    fp.write('<HEAD><script type=text/javascript src=../../../html/sorttable.js></script></head>')
    fp.write('<BODY>\n')
    fp.write('<H2> Field: {:s}</H2><p>\n'.format(field))
    fp.write('<A HREF=plots/{:s}_rvhist.png> <IMG SRC=plots/{:s}_rvhist.png> </A>'.format(field,field))
   
    fp.write('<BR>Click on column headers to sort by column value<BR>\n') 
    fp.write('<TABLE BORDER=2 CLASS=sortable>\n')
    fp.write('<TR><TD>Obj<TD>Delta(VSCATTER)<TD>H<TD>Doppler RV_TEFF<TD>N_components<TD>Combined spectrum<TD>RV plot<TD>Spectrum<TD>Spectrum windows<TD> continuum\n')
    for star in apf :
        obj=star['APOGEE_ID']
        print(obj)

        # get visits in Doppler allvisit table
        j=np.where(apfv['APOGEE_ID'] == obj)[0]
        if len(j) == 0 : 
            print('missing {:s} in apfv'.format(obj))
            continue

        # get object in apField
        try: k=np.where(apfield['APOGEE_ID'] == obj)[0][0]
        except: k=-1
        if doapfield :jj=np.where(apfieldvisits['APOGEE_ID'] == obj)[0] 

        # star information
        if star['TARGFLAGS'].find('TELLURIC') >=0 :
            fp.write('<TR><TD bgcolor=lightblue>')
        else :
            fp.write('<TR><TD>')
        fp.write('{:s}'.format(obj))
        fp.write('(<A HREF="http://simbad.cfa.harvard.edu/simbad/sim-basic?Ident={:12.5f}%09{:12.5f}++&submit=SIMBAD+search"> SIMBAD </A>)<BR>'.format
                   (star['RA'],star['DEC']))
        fp.write('H  = {:7.2f}<br>'.format(star['H']))
        fp.write('SNR  = {:7.2f}<br>'.format(star['SNR']))
        fp.write('{:s}<br>'.format(star['TARGFLAGS']))
        fp.write('{:s}<br>'.format(star['STARFLAGS']))

        # average velocities
        fp.write('<TABLE BORDER=2>\n')
        fp.write('<TR><TD><TD>VHELIO_AVG<TD>VSCATTER<TD>TEFF<TD>LOGG<TD>[FE/H]\n')
        fp.write('<TR><TD>Doppler<TD>{:8.2f}<TD>{:8.2f}<TD>{:8.0f}<TD>{:8.2f}<TD>{:8.2f}\n'.format(
                 star['VHELIO_AVG'],star['VSCATTER'],
                 star['RV_TEFF'],star['RV_LOGG'],star['RV_FEH']))
        fp.write('<TR><TD>Doppler Xcorr<TD>{:8.2f}<TD>{:8.2f}<TD>{:8.0f}<TD>{:8.2f}<TD>{:8.2f}\n'.format(
                 np.median(apfv['XCORR_VHELIO'][j]),
                 apfv['XCORR_VHELIO'][j].std(ddof=1),
                 star['RV_TEFF'],star['RV_LOGG'],star['RV_FEH']))
        if k>=0 :
            gd = np.where(np.abs(apfieldvisits['VHELIO']) < 999)[0]
            fp.write('<TR><TD>IDL<TD>{:8.2f}<TD>{:8.2f}<TD>{:8.0f}<TD>{:8.2f}<TD>{:8.2f}\n'.format(
                     apfield['VHELIO_AVG'][k],apfield['VSCATTER'][k],
                     apfield['RV_TEFF'][k],apfield['RV_LOGG'][k],apfield['RV_FEH'][k]))
        fp.write('</TABLE><br>')

        # flag bad RVs
        vhelio=apfv['VHELIO'][j]

        # individual visit velocities
        fp.write('<TABLE BORDER=2>')
        fp.write('<TR><TD>JD<TD>PLATE<TD>MJD<TD>FIBER<TD>S/N<TD>Doppler xcorr<TD> xcorr_err<TD>Doppler<TD>VERR<TD>IDL<TD>VERR<TD>ESTBC<TD>Dop BC<TD>apS BC\n')
        for ind,i in enumerate(j) :
            try : 
                ii = np.where(apfieldvisits['FILE'] == apfv['FILE'][i])[0][0]
                vhelio_idl =  apfieldvisits['VHELIO'][ii]
                vrelerr_idl =  apfieldvisits['VRELERR'][ii]
                bc_idl =  apfieldvisits['BC'][ii]
                vscatter_idl = apfield['VSCATTER'][k]
            except : 
                vhelio_idl,vrelerr_idl,bc_idl = -99999,-99999,-99999
                vscatter_idl = -99999
            if np.isfinite(apfv['VHELIO'][i]) == False :
                bgcolor='bgcolor=red'
            elif apfv['STARFLAG'][i] & starmask.getval('RV_REJECT') > 0 :
                bgcolor='bgcolor=lightpink'
            elif apfv['STARFLAG'][i] & starmask.getval('RV_SUSPECT') > 0 :
                bgcolor='bgcolor=#F4DEDE'
            else : bgcolor=''
            fp.write(('<TR {:s}> <TD> <A HREF={:s} TARGET="_obj"> {:12.3f}</A> <TD> {:s} <TD> {:5d} <TD> {:5d}'+
                     '<TD> {:8.1f} <TD> {:8.2f} <TD> {:8.2f} <TD> {:8.2f} <TD> {:8.2f} <TD> {:8.2f} <TD> {:8.2f}'+
                     '<TD> {:8.2f} <TD> {:8.2f} <TD>{:8.2f}\n').format(
                      bgcolor,
                      apfv['FILE'][i].replace('.fits','_dopfit.png').replace('-r12-','-r13-'),
                      apfv['JD'][i],apfv['PLATE'][i],apfv['MJD'][i],apfv['FIBERID'][i],
                      apfv['SNR'][i],
                      apfv['XCORR_VHELIO'][i],apfv['XCORR_VRELERR'][i],
                      apfv['VHELIO'][i],apfv['VRELERR'][i],
                      vhelio_idl, vrelerr_idl, apfv['ESTBC'][i],apfv['BC'][i],bc_idl))
        fp.write('</TABLE>\n')

        # vscatter difference with IDL
        fp.write('<TD> {:8.2f}\n'.format(star['VSCATTER']-vscatter_idl))
        fp.write('<TD> {:8.2f}\n'.format(star['H']))
        fp.write('<TD> {:8.2f}\n'.format(star['RV_TEFF']))
        fp.write('<TD> {:d}\n'.format(star['N_COMPONENTS']))

        # plot visit RVs
        if doapfield : 
            vidl=apfieldvisits['VHELIO'][jj]
            gd = np.where(np.abs(vidl) < 999)[0]
            vmax=np.nanmax(np.append(vhelio,vidl[gd]))
            vmin=np.nanmin(np.append(vhelio,vidl[gd]))
        else :
            vmax=np.nanmax(vhelio)
            vmin=np.nanmin(vhelio)
        yr=[vmin-0.1*(vmax-vmin),vmax+0.1*(vmax-vmin)]
        try :
            fig,ax=plots.multi(1,1)
            gd_dop = np.where((apfv['STARFLAG'][j] & starmask.getval('RV_REJECT')) == 0)[0]
            if len(gd_dop) > 0 : 
                plots.plotp(ax,apfv['MJD'][j[gd_dop]],vhelio[gd_dop],size=15,color='g',yr=yr,label='Doppler')
            bd_dop = np.where((apfv['STARFLAG'][j] & starmask.getval('RV_REJECT')) > 0)[0]
            if len(bd_dop) > 0 : ax.scatter(apfv['MJD'][j[bd_dop]],vhelio[bd_dop],s=15,
                                            facecolors='none',edgecolors='g',label='rejected Doppler')
            ax.plot(ax.get_xlim(),[star['VHELIO_AVG'],star['VHELIO_AVG']],color='g')
            if doapfield : 
                plots.plotp(ax,apfieldvisits['MJD'][jj[gd]],vidl[gd],size=15,color='r',yr=yr,label='IDL')
                ax.plot(ax.get_xlim(),[apfield['VHELIO_AVG'][k],apfield['VHELIO_AVG'][k]],color='r')
            ax.legend()
            fig.savefig(outdir+'/plots/'+obj+'_rv.png')
            plt.close()
        except KeyboardInterrupt: raise
        except :
            print('Plotting error....')
            plt.close()
            pass

        # include plots
        fp.write('<TD><a HREF=plots/{:s}.png TARGET="_obj"> <IMG SRC=plots/{:s}.png WIDTH=600></A>\n'.format(obj,obj))
        fp.write('<TD><IMG SRC=plots/{:s}_rv.png TARGET="_obj">\n'.format(obj))
        fp.write('<TD><A HREF=plots/{:s}_ccf.png TARGET="_obj"> <IMG SRC=plots/{:s}_ccf.png></A>\n'.format(obj,obj))
        fp.write('<TD><A HREF=plots/{:s}_spec.png TARGET="_obj"> <IMG SRC=plots/{:s}_spec.png></a>\n'.format(obj,obj))
        fp.write('<TD><A HREF=plots/{:s}_spec2.png TARGET="_obj"> <IMG SRC=plots/{:s}_spec2.png></a>\n'.format(obj,obj))
        fp.write('<TD><A HREF=plots/{:s}_cont.png TARGET="_obj"> <IMG SRC=plots/{:s}_cont.png></a>\n'.format(obj,obj))
    fp.close() 

def overlap(fields) :
    """ compare RVs from different fields for overlapping stars
    """

    r13=apload.ApLoad(apred='r13')
    f=[]
    a=[]
    for field in fields :
        f.append(fits.open(field+'/'+field+'_rv.fits'))
        a.append( r13.apFieldVisits(field))

    outdir=fields[0]+'_'+fields[1]
    try: os.makedirs(outdir)
    except: pass

    fp=open(outdir+'/'+outdir+'.html','w')
    fp.write('<HTML>\n')
    fp.write('<HEAD><script type=text/javascript src=../html/sorttable.js></script></head>')
    fp.write('<BODY>\n')
    fp.write('<TABLE BORDER=2>\n')

    matplotlib.use('Agg')
    i1,i2=match.match(f[0][1].data['APOGEE_ID'],f[1][1].data['APOGEE_ID'])
    colors=['g','r','b','m']
    for star in f[0][1].data['APOGEE_ID'][i1] :
        print(star)
        fp.write('<TR><TD>{:s}<BR>\n'.format(star))
        fp.write('<TABLE BORDER=2>\n')
        fig,ax=plots.multi(1,1)
        for i,field in enumerate(f) :
            j=np.where(field[2].data['APOGEE_ID'] == star)[0]
            plots.plotp(ax,field[2].data['MJD'][j],field[2].data['VHELIO'][j],color=colors[i],size=10)
            j=np.where(field[1].data['APOGEE_ID'] == star)[0][0]
            fp.write('<TR><TD>Doppler<TD>{:8.2f}<TD>{:8.2f}<TD>{:8.0f}<TD>{:8.2f}<TD>{:8.2f}\n'.format(
                 field[1].data['VHELIO_AVG'][j],field[1].data['VSCATTER'][j],
                 field[1].data['RV_TEFF'][j],field[1].data['RV_LOGG'][j],field[1].data['RV_FEH'][j]))
        for i,field in enumerate(a) :
            j=np.where(field[1].data['APOGEE_ID'] == star)[0]
            gd=np.where(np.abs(field[1].data['VHELIO'][j]) < 999)[0]
            plots.plotp(ax,field[1].data['MJD'][j[gd]],field[1].data['VHELIO'][j[gd]],color=colors[i+2],size=10)
            #fp.write('<TR><TD>IDL<TD>{:8.2f}<TD>{:8.2f}<TD>{:8.2f}<TD>{:8.0f}<TD>{:8.2f}<TD>{:8.2f}\n'.format(
            #     field[1].data['VHELIO_AVG'],field[1].data['VSCATTER'],
            #     field[1].data['RV_TEFF'],field[1].data['RV_LOGG'],field[1].data['RV_FEH']))
        plt.draw()
        plt.close()
        fig.savefig(outdir+'/'+star+'.png')
        fp.write('</TABLE>\n')
        fp.write('<TD><a HREF={:s}.png> <IMG SRC={:s}.png> </a>\n'.format(star,star))
    fp.write('</TABLE>')
    fp.close()

from apogee_drp.apred import wave
from apogee_drp.apred import sincint

def visitcomb(allvisit,load=None, apred='r13',telescope='apo25m',nres=[5,4.25,3.5],bconly=False,
              plot=False,write=True,dorvfit=True,apstar_vers='stars',logger=None):
    """ Combine multiple visits with individual RVs to rest frame sum
    """

    if logger is None:
        logger = dln.basiclogger()

    if load is None: load = apload.ApLoad(apred=apred,telescope=telescope)
    cspeed = 2.99792458e5  # speed of light in km/s

    logger.info('Doing visitcomb for {:s} '.format(allvisit['apogee_id'][0]))

    wnew = norm.apStarWave()  
    nwave = len(wnew)
    nvisit = len(allvisit)

    # initialize array for stack of interpolated spectra
    zeros = np.zeros([nvisit,nwave])
    izeros = np.zeros([nvisit,nwave],dtype=int)
    stack = apload.ApSpec(zeros,err=zeros.copy(),bitmask=izeros,cont=zeros.copy(),
                          sky=zeros.copy(),skyerr=zeros.copy(),telluric=zeros.copy(),telerr=zeros.copy())

    apogee_target1, apogee_target2, apogee_target3 = 0, 0, 0
    apogee2_target1, apogee2_target2, apogee2_target3, apogee2_target4 = 0, 0, 0, 0
    starflag,andflag = np.uint64(0),np.uint64(0)
    starmask = bitmask.StarBitMask()

    # Loop over each visit and interpolate to final wavelength grid
    if plot : fig,ax=plots.multi(1,2,hspace=0.001)
    for i,visit in enumerate(allvisit) :

        if bconly: vrel = -visit['bc']
        else: vrel = visit['vrel']

        # Skip if we don't have an RV
        if np.isfinite(vrel) is False : continue

        # Load the visit
        if load.telescope == 'apo1m':
            apvisit = load.apVisit1m(visit['plate'],visit['mjd'],visit['apogee_id'],load=True)
        else:
            apvisit = load.apVisit(int(visit['plate']),visit['mjd'],visit['fiberid'],load=True)
        pixelmask = bitmask.PixelBitMask()

        # Rest-frame wavelengths transformed to this visit spectra
        w = norm.apStarWave()*(1.0+vrel/cspeed)

        # Loop over the chips
        for chip in range(3) :

            # Get the pixel values to interpolate to
            pix = wave.wave2pix(w,apvisit.wave[chip,:])
            gd, = np.where(np.isfinite(pix))

            # Get a smoothed, filtered spectrum to use as replacement for bad values
            cont = gaussian_filter(median_filter(apvisit.flux[chip,:],[501],mode='reflect'),100)
            errcont = gaussian_filter(median_filter(apvisit.flux[chip,:],[501],mode='reflect'),100)
            bd = np.where(apvisit.bitmask[chip,:]&pixelmask.badval())[0]
            if len(bd) > 0: 
                apvisit.flux[chip,bd] = cont[bd] 
                apvisit.err[chip,bd] = errcont[bd] 

            # Load up quantity/error pairs for interpolation
            raw = [[apvisit.flux[chip,:],apvisit.err[chip,:]**2],
                   [apvisit.sky[chip,:],apvisit.skyerr[chip,:]**2],
                   [apvisit.telluric[chip,:],apvisit.telerr[chip,:]**2]]

            # Load up individual mask bits
            for ibit,name in enumerate(pixelmask.name):
                if name is not '' and len(np.where(apvisit.bitmask[chip,:]&2**ibit)[0]) > 0:
                    raw.append([np.clip(apvisit.bitmask[chip,:]&2**ibit,None,1),None])

            # Do the sinc interpolation
            out = sincint.sincint(pix[gd],nres[chip],raw)

            # From output flux, get continuum to remove, so that all spectra are
            #   on same scale. We'll later multiply in the median continuum
            flux = out[0][0]
            stack.cont[i,gd] = gaussian_filter(median_filter(flux,[501],mode='reflect'),100)

            # Load interpolated spectra into output stack
            stack.flux[i,gd] = out[0][0] / stack.cont[i,gd]
            stack.err[i,gd] = out[0][1] / stack.cont[i,gd]
            stack.sky[i,gd] = out[1][0]
            stack.skyerr[i,gd] = out[1][1]
            stack.telluric[i,gd] = out[2][0]
            stack.telerr[i,gd] = out[2][1]
            # For mask, set bits where interpolated value is above some threshold
            #   defined for each mask bit
            iout = 3
            for ibit,name in enumerate(pixelmask.name):
                if name is not '' and len(np.where(apvisit.bitmask[chip,:]&2**ibit)[0]) > 0:
                    j = np.where(np.abs(out[iout][0]) > pixelmask.maskcontrib[ibit])[0]
                    stack.bitmask[i,gd[j]] |= 2**ibit
                    iout += 1

        # Increase uncertainties for persistence pixels
        bd, = np.where((stack.bitmask[i,:]&pixelmask.getval('PERSIST_HIGH')) > 0)
        if len(bd) > 0: stack.err[i,bd] *= np.sqrt(5)
        bd, = np.where(((stack.bitmask[i,:]&pixelmask.getval('PERSIST_HIGH')) == 0) &
                       ((stack.bitmask[i,:]&pixelmask.getval('PERSIST_MED')) > 0) )
        if len(bd) > 0: stack.err[i,bd] *= np.sqrt(4)
        bd, = np.where(((stack.bitmask[i,:]&pixelmask.getval('PERSIST_HIGH')) == 0) &
                       ((stack.bitmask[i,:]&pixelmask.getval('PERSIST_MED')) == 0) &
                       ((stack.bitmask[i,:]&pixelmask.getval('PERSIST_LOW')) > 0) )
        if len(bd) > 0: stack.err[i,bd] *= np.sqrt(3)
        bd, = np.where((stack.bitmask[i,:]&pixelmask.getval('SIG_SKYLINE')) > 0)
        if len(bd) > 0: stack.err[i,bd] *= np.sqrt(100)

        if plot:
            ax[0].plot(norm.apStarWave(),stack.flux[i,:])
            ax[1].plot(norm.apStarWave(),stack.flux[i,:]/stack.err[i,:])
            plt.draw()
            pdb.set_trace()

        # Accumulate for header of combined frame. Turn off visit specific RV flags first
        visitflag = visit['starflag'] & ~starmask.getval('rv_reject') & ~starmask.getval('rv_suspect')
        starflag |= visitflag
        andflag &= visitflag
        if visit['survey'] == 'apogee' :
            apogee_target1 |= visit['apogee_target1']
            apogee_target2 |= visit['apogee_target2']
            apogee_target3 |= visit['apogee_target3']
        elif visit['survey'].find('apogee2') >=0  :
            apogee2_target1 |= visit['apogee_target1']
            apogee2_target2 |= visit['apogee_target2'] 
            apogee2_target3 |= visit['apogee_target3']
            try: apogee2_target4 |= visit['apogee_target4']
            except: pass
        # MWM target flags?
            

    # Create final spectrum
    zeros = np.zeros([nvisit+2,nwave])
    izeros = np.zeros([nvisit+2,nwave],dtype=int)
    apstar = apload.ApSpec(zeros,err=zeros.copy(),bitmask=izeros,wave=norm.apStarWave(),
                           sky=zeros.copy(),skyerr=zeros.copy(),telluric=zeros.copy(),
                           telerr=zeros.copy(),cont=zeros.copy(),template=zeros.copy())
    apstar.header['CRVAL1'] = norm.logw0
    apstar.header['CDELT1'] = norm.dlogw
    apstar.header['CRPIX1'] = 1
    apstar.header['CTYPE1'] = ('LOG-LINEAR','Logarithmic wavelength scale in subsequent HDU')
    apstar.header['DC-FLAG'] = 1

    # Pixel-by-pixel weighted average
    cont = np.median(stack.cont,axis=0)
    apstar.flux[0,:] = np.sum(stack.flux/stack.err**2,axis=0)/np.sum(1./stack.err**2,axis=0) * cont
    apstar.err[0,:] =  np.sqrt(1./np.sum(1./stack.err**2,axis=0)) * cont
    apstar.bitmask[0,:] = np.bitwise_and.reduce(stack.bitmask,0)
    apstar.cont[0,:] = cont

    # Individual visits
    apstar.flux[2:,:] = stack.flux * stack.cont
    apstar.err[2:,:] = stack.err * stack.cont
    apstar.bitmask[2:,:] = stack.bitmask
    apstar.sky[2:,:] = stack.sky
    apstar.skyerr[2:,:] = stack.skyerr
    apstar.telluric[2:,:] = stack.telluric
    apstar.telerr[2:,:] = stack.telerr

    # Populate header
    apstar.header['FIELD'] = (allvisit['field'][0], 'APOGEE field name')
    apstar.header['OBJID'] = (allvisit['apogee_id'][0], 'APOGEE object name')
    try :apstar.header['SNR'] = (np.nanmedian(apstar.flux/apstar.err), 'Median S/N per apStar pixel')
    except :apstar.header['SNR'] = (0., 'Median S/N per apStar pixel')
    apstar.header['RA'] = (allvisit['ra'].max(), 'right ascension, deg, J2000')
    apstar.header['DEC'] = (allvisit['dec'].max(), 'declination, deg, J2000')
    apstar.header['GLON'] = (allvisit['glon'].max(), 'Galactic longitude')
    apstar.header['GLAT'] = (allvisit['glat'].max(), 'Galactic latitude')
    apstar.header['J'] = (allvisit['j'].max(), '2MASS J magnitude')
    apstar.header['J_ERR'] = (allvisit['j_err'].max(), '2MASS J magnitude uncertainty')
    apstar.header['H'] = (allvisit['h'].max(), '2MASS H magnitude')
    apstar.header['H_ERR'] = (allvisit['h_err'].max(), '2MASS H magnitude uncertainty')
    apstar.header['K'] = (allvisit['k'].max(), '2MASS K magnitude')
    apstar.header['K_ERR'] = (allvisit['k_err'].max(), '2MASS K magnitude uncertainty')
    try: apstar.header['SRC_H'] = (allvisit[0]['src_h'], 'source of H magnitude')
    except KeyError: pass
    keys = ['wash_m','wash_t2','ddo51','irac_3_6',
            'irac_4_5','irac_5_8','wise_4_5','targ_4_5'] 
    for key in keys:
        try: apstar.header[key] = allvisit[key].max()
        except KeyError: pass

    apstar.header['AKTARG'] = (allvisit['ak_targ'].max(), 'Extinction used for targeting')
    apstar.header['AKMETHOD'] = (allvisit[0]['ak_targ_method'],'Extinction method using for targeting')
    apstar.header['AKWISE'] = (allvisit['ak_wise'].max(),'WISE all-sky extinction')
    apstar.header['SFD_EBV'] = (allvisit['sfd_ebv'].max(),'SFD E(B-V)')
    apstar.header['APTARG1'] = (apogee_target1, 'APOGEE_TARGET1 targeting flag')
    apstar.header['APTARG2'] = (apogee_target2, 'APOGEE_TARGET2 targeting flag')
    apstar.header['APTARG3'] = (apogee_target3, 'APOGEE_TARGET3 targeting flag')
    apstar.header['AP2TARG1'] = (apogee2_target1, 'APOGEE2_TARGET1 targeting flag')
    apstar.header['AP2TARG2'] = (apogee2_target2, 'APOGEE2_TARGET2 targeting flag')
    apstar.header['AP2TARG3'] = (apogee2_target3, 'APOGEE2_TARGET3 targeting flag')
    apstar.header['AP2TARG4'] = (apogee2_target4, 'APOGEE2_TARGET4 targeting flag')
    apstar.header['NVISITS'] = (len(allvisit), 'Number of visit spectra combined flag')
    apstar.header['STARFLAG'] = (starflag,'bitwise OR of individual visit starflags')
    apstar.header['ANDFLAG'] = (andflag,'bitwise AND of individual visit starflags')

    try: apstar.header['N_COMP'] = (allvisit['n_components'].max(),'Maximum number of components in RV CCFs')
    except: pass
    apstar.header['VHELIO'] = ((allvisit['vhelio']*allvisit['snr']).sum() / allvisit['snr'].sum(),'S/N weighted mean barycentric RV')
    if len(allvisit) > 1 : apstar.header['vscatter'] = (allvisit['vhelio'].std(ddof=1), 'standard deviation of visit RVs')
    else: apstar.header['VSCATTER'] = (0., 'standard deviation of visit RVs')
    apstar.header['VERR'] = (0.,'unused')
    apstar.header['RV_TEFF'] = (allvisit['rv_teff'].max(),'Effective temperature from RV fit')
    apstar.header['RV_LOGG'] = (allvisit['rv_logg'].max(),'Surface gravity from RV fit')
    apstar.header['RV_FEH'] = (allvisit['rv_feh'].max(),'Metallicity from RV fit')

    if len(allvisit) > 0: meanfib=(allvisit['fiberid']*allvisit['SNR']).sum()/allvisit['SNR'].sum()
    else: meanfib = 999999.
    if len(allvisit) > 1: sigfib=allvisit['fiberid'].std(ddof=1)
    else: sigfib = 0.
    apstar.header['MEANFIB'] = (meanfib,'S/N weighted mean fiber number')
    apstar.header['SIGFIB'] = (sigfib,'standard deviation (unweighted) of fiber number')
    apstar.header['NRES'] = ('{:5.2f}{:5.2f}{:5.2f}'.format(*nres),'number of pixels/resolution used for sinc')

    # individual visit information in header
    for i0,visit in enumerate(allvisit) :
        i = i0+1
        apstar.header['SFILE{:d}'.format(i)] = (visit['file'],' Visit #{:d} spectrum file'.format(i))
        apstar.header['DATE{:d}'.format(i)] = (visit['dateobs'], 'DATE-OBS of visit {:d}'.format(i))
        apstar.header['JD{:d}'.format(i)] = (visit['jd'], 'Julian date of visit {:d}'.format(i))
        # hjd = helio_jd(visitstr[i].jd-2400000.0,visitstr[i].ra,visitstr[i].dec)
        #apstar.header['HJD{:d}'.format(i)] = 
        apstar.header['FIBER{:d}'.format(i)] = (visit['fiberid'],' Fiber, visit {:d}'.format(i))
        apstar.header['BC{:d}'.format(i)] = (visit['bc'],' Barycentric correction (km/s), visit {:d}'.format(i))
        apstar.header['VRAD{:d}'.format(i)] = (visit['vrel'],' Doppler shift (km/s) of visit {:d}'.format(i))
        #apstar.header['VERR%d'.format(i)] = 
        apstar.header['VHELIO{:d}'.format(i)] = (visit['vhelio'],' Barycentric velocity (km/s), visit {:d}'.format(i))
        apstar.header['SNRVIS{:d}'.format(i)] = (visit['snr'],' Signal/Noise ratio, visit {:d}'.format(i))
        apstar.header['FLAG{:d}'.format(i)] = (visit['starflag'],' STARFLAG for visit {:d}'.format(i))
        apstar.header.insert('SFILE{:d}'.format(i),('COMMENT','VISIT {:d} INFORMATION'.format(i)))

    # Do a RV fit just to get a template and normalized spectrum, for plotting
    if dorvfit:
        try:
            apstar.setmask(pixelmask.badval())
            spec = doppler.Spec1D(apstar.flux[0,:],err=apstar.err[0,:],bitmask=apstar.bitmask[0,:],
                                  mask=apstar.mask[0,:],wave=apstar.wave,lsfpars=np.array([0]),
                                  lsfsigma=apstar.wave/22500/2.354,instrument='APOGEE',
                                  filename=apstar.filename)
            out = doppler.rv.jointfit([spec],verbose=False,plot=False,tweak=False,maxvel=[-50,50])
            apstar.cont = out[3][0].flux
            apstar.template = out[2][0].flux
        except ValueError as err:
            info.error('Exception raised in visitcomb RV for: ', apstar.header['FIELD'],apstar.header['OBJID'])
            info.error("ValueError: {0}".format(err))
        except RuntimeError as err:
            info.error('Exception raised in visitcomb RV for: ', apstar.header['FIELD'],apstar.header['OBJID'])
            info.error("Runtime error: {0}".format(err))
        except: 
            info.error('Exception raised in visitcomb RV fit for: ',apstar.header['FIELD'],apstar.header['OBJID'])

    # Write the spectrum to file
    if write:
        outfile = load.filename('Star',obj=apstar.header['OBJID'])
        if apstar_vers != 'stars' :
            outfile = outfile.replace('/stars/','/'+apstar_vers+'/')
        outdir = os.path.dirname(outfile)
        try: os.makedirs(os.path.dirname(outfile))
        except: pass
        apstar.write(outfile)

        # Plot
        gd, = np.where((apstar.bitmask[0,:] & (pixelmask.badval()|pixelmask.getval('SIG_SKYLINE'))) == 0)
        fig,ax = plots.multi(1,3,hspace=0.001,figsize=(48,6))
        med = np.nanmedian(apstar.flux[0,:])
        plots.plotl(ax[0],norm.apStarWave(),apstar.flux[0,:],color='k',yr=[0,2*med])
        ax[0].plot(norm.apStarWave()[gd],apstar.flux[0,gd],color='g')
        ax[0].set_ylabel('Flux')
        try:
            ax[1].plot(norm.apStarWave()[gd],apstar.cont[gd],color='g')
            ax[1].set_ylabel('Normalized')
            ax[1].plot(norm.apStarWave(),apstar.template,color='r')
        except: pass
        plots.plotl(ax[2],norm.apStarWave(),apstar.flux[0,:]/apstar.err[0,:],yt='S/N')
        for i in range(3) : ax[i].set_xlim(15100,17000)
        ax[0].set_xlabel('Wavelength')
        fig.savefig(outdir+'/plots/'+apstar.header['OBJID']+'.png')

    # Plot
    if plot: 
        ax[0].plot(norm.apStarWave(),apstar.flux,color='k')
        ax[1].plot(norm.apStarWave(),apstar.flux/apstar.err,color='k')
        plt.draw()
        pdb.set_trace()

    return apstar

def comp_apstar(field,apred='r13',telescope='apo25m') :

    load=apload.ApLoad(apred=apred,telescope=telescope)
    apfield=load.apField(field)

    fig,ax=plots.multi(1,3,hspace=0.001)
    w=norm.apStarWave() 
    for i,star in enumerate(apfield[1].data['APOGEE_ID']) : 
        old=load.apStar(field,star)
        plots.plotl(ax[0],w,old[1].data[0,:]*1.e-17)
        for j in [2] :plots.plotl(ax[1],w,old[2].data[j,:]*1.e-17)
        plots.plotl(ax[2],w,old[3].data[0,:])
        #plots.plotl(ax[0],old[3].data['WAVE'][0,:],old[2].data['SPEC'][i,:]) 
        #plots.plotl(ax[1],old[3].data['WAVE'][0,:],old[2].data['ERR'][i,:]) 
        #plots.plotl(ax[2],old[3].data['WAVE'][0,:],old[2].data['MASK'][i,:]) 

        new=fits.open('apo25m/K01_082+17/apStar-r13-'+star+'.fits') 
        plots.plotl(ax[0],w,new[1].data[0,:]*1.e-17) 
        for j in [2] :plots.plotl(ax[1],w,new[2].data[j,:]*1.e-17)
        ax[1].set_ylim(0,1.e-16)
        plots.plotl(ax[2],w,new[3].data[0,:])
        plt.draw() 
        pdb.set_trace() 
        ax[0].cla()    
        ax[1].cla()    
        ax[2].cla()    

