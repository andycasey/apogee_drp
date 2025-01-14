function targflag,targ1,targ2,targ3,targ4,survey=survey

flag=''
if ~keyword_set(survey) then survey = 'apogee'

;; APOGEE-2
if strpos(survey,'apogee2') ge 0 then begin
 if is_bit_set(targ1,0) eq 1 then flag=flag+'APOGEE2_ONEBIN_GT_0_5,'
 if is_bit_set(targ1,1) eq 1 then flag=flag+'APOGEE2_TWOBIN_0_5_TO_0_8,'
 if is_bit_set(targ1,2) eq 1 then flag=flag+'APOGEE2_TWOBIN_GT_0_8,'
 if is_bit_set(targ1,3) eq 1 then flag=flag+'APOGEE2_IRAC_DERED,'
 if is_bit_set(targ1,4) eq 1 then flag=flag+'APOGEE2_WISE_DERED,'
 if is_bit_set(targ1,5) eq 1 then flag=flag+'APOGEE2_SFD_DERED,'
 if is_bit_set(targ1,6) eq 1 then flag=flag+'APOGEE2_NO_DERED,'
 if is_bit_set(targ1,7) eq 1 then flag=flag+'APOGEE2_WASH_GIANT,'
 if is_bit_set(targ1,8) eq 1 then flag=flag+'APOGEE2_WASH_DWARF,'
 if is_bit_set(targ1,9) eq 1 then flag=flag+'APOGEE2_SCI_CLUSTER,'
 if is_bit_set(targ1,10) eq 1 then flag=flag+'APOGEE2_CLUSTER_CANDIDATE,'
 if is_bit_set(targ1,11) eq 1 then flag=flag+'APOGEE2_SHORT,'
 if is_bit_set(targ1,12) eq 1 then flag=flag+'APOGEE2_MEDIUM,'
 if is_bit_set(targ1,13) eq 1 then flag=flag+'APOGEE2_LONG,'
 if is_bit_set(targ1,14) eq 1 then flag=flag+'APOGEE2_NORMAL_SAMPLE,'
 if is_bit_set(targ1,15) eq 1 then flag=flag+'APOGEE2_MANGA_LED,'
 if is_bit_set(targ1,16) eq 1 then flag=flag+'APOGEE2_ONEBIN_GT_0_3,'
 if is_bit_set(targ1,17) eq 1 then flag=flag+'APOGEE2_WASH_NOCLASS,'
 if is_bit_set(targ1,18) eq 1 then flag=flag+'APOGEE2_STREAM_MEMBER,'
 if is_bit_set(targ1,19) eq 1 then flag=flag+'APOGEE2_STREAM_CANDIDATE,'
 if is_bit_set(targ1,20) eq 1 then flag=flag+'APOGEE2_DSPH_MEMBER,'
 if is_bit_set(targ1,21) eq 1 then flag=flag+'APOGEE2_DSPH_CANDIDATE,'
 if is_bit_set(targ1,22) eq 1 then flag=flag+'APOGEE2_MAGCLOUD_MEMBER,'
 if is_bit_set(targ1,23) eq 1 then flag=flag+'APOGEE2_MAGCLOUD_CANDIDATE,'
 if is_bit_set(targ1,24) eq 1 then flag=flag+'APOGEE2_RRLYR,'
 if is_bit_set(targ1,25) eq 1 then flag=flag+'APOGEE2_BULGE_RC,'
 if is_bit_set(targ1,26) eq 1 then flag=flag+'APOGEE2_SGR_DSPH,'
 if is_bit_set(targ1,27) eq 1 then flag=flag+'APOGEE2_APOKASC_GIANT,'
 if is_bit_set(targ1,28) eq 1 then flag=flag+'APOGEE2_APOKASC_DWARF,'
 if is_bit_set(targ1,29) eq 1 then flag=flag+'APOGEE2_FAINT_EXTRA,'
 if is_bit_set(targ1,30) eq 1 then flag=flag+'APOGEE2_APOKASC,'
 ;if is_bit_set(targ1,31) eq 1 then flag=flag+'APOGEE_CHECKED '
 
 if is_bit_set(targ2,0) eq 1 then flag=flag+'APOGEE2_K2_GAP,'
 if is_bit_set(targ2,1) eq 1 then flag=flag+'APOGEE2_CCLOUD_AS4,'
 if is_bit_set(targ2,2) eq 1 then flag=flag+'APOGEE2_STANDARD_STAR,'
 if is_bit_set(targ2,3) eq 1 then flag=flag+'APOGEE2_RV_STANDARD,'
 if is_bit_set(targ2,4) eq 1 then flag=flag+'APOGEE2_SKY,'
 if is_bit_set(targ2,5) eq 1 then flag=flag+'APOGEE2_EXTERNAL_CALIB,'
 if is_bit_set(targ2,6) eq 1 then flag=flag+'APOGEE2_INTERNAL_CALIB,'
 if is_bit_set(targ2,7) eq 1 then flag=flag+'APOGEE2_DISK_SUBSTRUCTURE_MEMBER,'
 if is_bit_set(targ2,8) eq 1 then flag=flag+'APOGEE2_DISK_SUBSTRUCTURE_CANDIDATE,'
 if is_bit_set(targ2,9) eq 1 then flag=flag+'APOGEE2_TELLURIC,'
 if is_bit_set(targ2,10) eq 1 then flag=flag+'APOGEE2_CALIB_CLUSTER,'
 if is_bit_set(targ2,11) eq 1 then flag=flag+'APOGEE2_K2_PLANETHOST,'
 if is_bit_set(targ2,12) eq 1 then flag=flag+'APOGEE2_TIDAL_BINARY,'
 if is_bit_set(targ2,13) eq 1 then flag=flag+'APOGEE2_LITERATURE_CALIB,'
 if is_bit_set(targ2,14) eq 1 then flag=flag+'APOGEE2_GES_OVERLAP,'
 if is_bit_set(targ2,15) eq 1 then flag=flag+'APOGEE2_ARGOS_OVERLAP,'
 if is_bit_set(targ2,16) eq 1 then flag=flag+'APOGEE2_GAIA_OVERLAP,'
 if is_bit_set(targ2,17) eq 1 then flag=flag+'APOGEE2_GALAH_OVERLAP,'
 if is_bit_set(targ2,18) eq 1 then flag=flag+'APOGEE2_RAVE_OVERLAP,'
 if is_bit_set(targ2,19) eq 1 then flag=flag+'APOGEE2_COMMIS_SOUTH_SPEC,'
 if is_bit_set(targ2,20) eq 1 then flag=flag+'APOGEE2_HALO_MEMBER,'
 if is_bit_set(targ2,21) eq 1 then flag=flag+'APOGEE2_HALO_CANDIDATE,'
 if is_bit_set(targ2,22) eq 1 then flag=flag+'APOGEE2_1M_TARGET,'
 if is_bit_set(targ2,23) eq 1 then flag=flag+'APOGEE2_MOD_BRIGHT_LIMIT,'
 if is_bit_set(targ2,24) eq 1 then flag=flag+'APOGEE2_CIS,'
 if is_bit_set(targ2,25) eq 1 then flag=flag+'APOGEE2_CNTAC,'
 if is_bit_set(targ2,26) eq 1 then flag=flag+'APOGEE2_EXTERNAL,'
 if is_bit_set(targ2,27) eq 1 then flag=flag+'APOGEE2_CVZ_AS4_OBAF,'
 if is_bit_set(targ2,28) eq 1 then flag=flag+'APOGEE2_CVZ_AS4_GI,'
 if is_bit_set(targ2,29) eq 1 then flag=flag+'APOGEE2_CVZ_AS4_CTL,'
 if is_bit_set(targ2,30) eq 1 then flag=flag+'APOGEE2_CVZ_AS4_GIANT,'
 ;if is_bit_set(targ2,31) eq 1 then flag=flag+'APOGEE_CHECKED,'

 if is_bit_set(targ3,0) eq 1 then flag=flag+'APOGEE2_KOI,'
 if is_bit_set(targ3,1) eq 1 then flag=flag+'APOGEE2_EB,'
 if is_bit_set(targ3,2) eq 1 then flag=flag+'APOGEE2_KOI_CONTROL,'
 if is_bit_set(targ3,3) eq 1 then flag=flag+'APOGEE2_MDWARF,'
 if is_bit_set(targ3,4) eq 1 then flag=flag+'APOGEE2_SUBSTELLAR_COMPANIONS,'
 if is_bit_set(targ3,5) eq 1 then flag=flag+'APOGEE2_YOUNG_CLUSTER,'
 if is_bit_set(targ3,6) eq 1 then flag=flag+'APOGEE2_K2,'
 if is_bit_set(targ3,7) eq 1 then flag=flag+'APOGEE2_OBJECT,'
 if is_bit_set(targ3,8) eq 1 then flag=flag+'APOGEE2_ANCILLARY,'
 if is_bit_set(targ3,9) eq 1 then flag=flag+'APOGEE2_MASSIVE_STAR,'
 if is_bit_set(targ3,10) eq 1 then flag=flag+'APOGEE2_QSO,'
 if is_bit_set(targ3,11) eq 1 then flag=flag+'APOGEE2_CEPHEID,'
 if is_bit_set(targ3,12) eq 1 then flag=flag+'APOGEE2_LOW_AV_WINDOWS,'
 if is_bit_set(targ3,13) eq 1 then flag=flag+'APOGEE2_BE_STAR,'
 if is_bit_set(targ3,14) eq 1 then flag=flag+'APOGEE2_YOUNG_MOVING_GROUP,'
 if is_bit_set(targ3,15) eq 1 then flag=flag+'APOGEE2_NGC6791,'
 if is_bit_set(targ3,16) eq 1 then flag=flag+'APOGEE2_LABEL_STAR,'
 if is_bit_set(targ3,17) eq 1 then flag=flag+'APOGEE2_FAINT_KEPLER_GIANTS,'
 if is_bit_set(targ3,18) eq 1 then flag=flag+'APOGEE2_W345,'
 if is_bit_set(targ3,19) eq 1 then flag=flag+'APOGEE2_MASSIVE_EVOLVED,'
 if is_bit_set(targ3,20) eq 1 then flag=flag+'APOGEE2_REDDENING_TARGETS,'
 if is_bit_set(targ3,21) eq 1 then flag=flag+'APOGEE2_KEPLER_MDWARF_KOI,'
 if is_bit_set(targ3,22) eq 1 then flag=flag+'APOGEE2_AGB,'
 if is_bit_set(targ3,23) eq 1 then flag=flag+'APOGEE2_M33,'
 if is_bit_set(targ3,24) eq 1 then flag=flag+'APOGEE2_ULTRACOOL,'
 if is_bit_set(targ3,25) eq 1 then flag=flag+'APOGEE2_DISTANT_SEGUE_GIANTS,'
 if is_bit_set(targ3,26) eq 1 then flag=flag+'APOGEE2_CEPHEID_MAPPING,'
 if is_bit_set(targ3,27) eq 1 then flag=flag+'APOGEE2_SA57,'
 if is_bit_set(targ3,28) eq 1 then flag=flag+'APOGEE2_K2_MDWARF,'
 if is_bit_set(targ3,29) eq 1 then flag=flag+'APOGEE2_RVVAR,'
 if is_bit_set(targ3,30) eq 1 then flag=flag+'APOGEE2_M31,'
endif

;; APOGEE-1
if (strpos(survey,'apogee') ge 0) and (strpos(survey,'apogee2') eq -1) then begin
 if is_bit_set(targ1,0) eq 1 then flag=flag+'APOGEE_FAINT,'
 if is_bit_set(targ1,1) eq 1 then flag=flag+'APOGEE_MEDIUM,'
 if is_bit_set(targ1,2) eq 1 then flag=flag+'APOGEE_BRIGHT,'
 if is_bit_set(targ1,3) eq 1 then flag=flag+'APOGEE_IRAC_DERED,'
 if is_bit_set(targ1,4) eq 1 then flag=flag+'APOGEE_WISE_DERED,'
 if is_bit_set(targ1,5) eq 1 then flag=flag+'APOGEE_SFD_DERED,'
 if is_bit_set(targ1,6) eq 1 then flag=flag+'APOGEE_NO_DERED,'
 if is_bit_set(targ1,7) eq 1 then flag=flag+'APOGEE_WASH_GIANT,'
 if is_bit_set(targ1,8) eq 1 then flag=flag+'APOGEE_WASH_DWARF,'
 if is_bit_set(targ1,9) eq 1 then flag=flag+'APOGEE_SCI_CLUSTER,'
 if is_bit_set(targ1,10) eq 1 then flag=flag+'APOGEE_EXTENDED,'
 if is_bit_set(targ1,11) eq 1 then flag=flag+'APOGEE_SHORT,'
 if is_bit_set(targ1,12) eq 1 then flag=flag+'APOGEE_INTERMEDIATE,'
 if is_bit_set(targ1,13) eq 1 then flag=flag+'APOGEE_LONG,'
 if is_bit_set(targ1,14) eq 1 then flag=flag+'APOGEE_DO_NOT_OBSERVE,'
 if is_bit_set(targ1,15) eq 1 then flag=flag+'APOGEE_SERENDIPITOUS,'
 if is_bit_set(targ1,16) eq 1 then flag=flag+'APOGEE_FIRST_LIGHT,'
 if is_bit_set(targ1,17) eq 1 then flag=flag+'APOGEE_ANCILLARY,'
 if is_bit_set(targ1,18) eq 1 then flag=flag+'APOGEE_M31_CLUSTER,'
 if is_bit_set(targ1,19) eq 1 then flag=flag+'APOGEE_MDWARF,'
 if is_bit_set(targ1,20) eq 1 then flag=flag+'APOGEE_HIRES,'
 if is_bit_set(targ1,21) eq 1 then flag=flag+'APOGEE_OLD_STAR,'
 if is_bit_set(targ1,22) eq 1 then flag=flag+'APOGEE_DISK_RED_GIANT,'
 if is_bit_set(targ1,23) eq 1 then flag=flag+'APOGEE_KEPLER_EB,'
 if is_bit_set(targ1,24) eq 1 then flag=flag+'APOGEE_GC_PAL1,'
 if is_bit_set(targ1,25) eq 1 then flag=flag+'APOGEE_MASSIVE_STAR,'
 if is_bit_set(targ1,26) eq 1 then flag=flag+'APOGEE_SGR_DSPH,'
 if is_bit_set(targ1,27) eq 1 then flag=flag+'APOGEE_KEPLER_SEISMO,'
 if is_bit_set(targ1,28) eq 1 then flag=flag+'APOGEE_KEPLER_HOST,'
 if is_bit_set(targ1,29) eq 1 then flag=flag+'APOGEE_FAINT_EXTRA,'
 if is_bit_set(targ1,30) eq 1 then flag=flag+'APOGEE_SEGUE_OVERLAP,'
 ;if is_bit_set(targ1,31) eq 1 then flag=flag+'APOGEE_CHECKED '
 
 if is_bit_set(targ2,0) eq 1 then flag=flag+'LIGHT_TRAP,'
 if is_bit_set(targ2,1) eq 1 then flag=flag+'APOGEE_FLUX_STANDARD,'
 if is_bit_set(targ2,2) eq 1 then flag=flag+'APOGEE_STANDARD_STAR,'
 if is_bit_set(targ2,3) eq 1 then flag=flag+'APOGEE_RV_STANDARD,'
 if is_bit_set(targ2,4) eq 1 then flag=flag+'APOGEE_SKY,'
 if is_bit_set(targ2,5) eq 1 then flag=flag+'APOGEE_SKY_BAD,'
 if is_bit_set(targ2,6) eq 1 then flag=flag+'APOGEE_GUIDE_STAR,'
 if is_bit_set(targ2,7) eq 1 then flag=flag+'APOGEE_BUNDLE_HOLE,'
 if is_bit_set(targ2,8) eq 1 then flag=flag+'APOGEE_TELLURIC_BAD,'
 if is_bit_set(targ2,9) eq 1 then flag=flag+'APOGEE_TELLURIC,'
 if is_bit_set(targ2,10) eq 1 then flag=flag+'APOGEE_CALIB_CLUSTER,'
 if is_bit_set(targ2,11) eq 1 then flag=flag+'APOGEE_BULGE_GIANT,'
 if is_bit_set(targ2,12) eq 1 then flag=flag+'APOGEE_BULGE_SUPER_GIANT,'
 if is_bit_set(targ2,13) eq 1 then flag=flag+'APOGEE_EMBEDDEDCLUSTER_STAR,'
 if is_bit_set(targ2,14) eq 1 then flag=flag+'APOGEE_LONGBAR,'
 if is_bit_set(targ2,15) eq 1 then flag=flag+'APOGEE_EMISSION_STAR,'
 if is_bit_set(targ2,16) eq 1 then flag=flag+'APOGEE_KEPLER_COOLDWARF,'
 if is_bit_set(targ2,17) eq 1 then flag=flag+'APOGEE_MIRCLUSTER_STAR,'
 if is_bit_set(targ2,18) eq 1 then flag=flag+'APOGEE_RV_MONITOR_IC348,'
 if is_bit_set(targ2,19) eq 1 then flag=flag+'APOGEE_RV_MONITOR_KEPLER,'
 if is_bit_set(targ2,20) eq 1 then flag=flag+'APOGEE_GES_CALIBRATE,'
 if is_bit_set(targ2,21) eq 1 then flag=flag+'APOGEE_BULGE_RV_VERIFY,'
 if is_bit_set(targ2,22) eq 1 then flag=flag+'APOGEE_1MTARGET,'
 ;if is_bit_set(targ2,31) eq 1 then flag=flag+'APOGEE_CHECKED,'
 
endif

;; MWM
if strpos(survey,'mwm') ge 0 then begin
  name = ['MWM_SKY','MWM_TELLURIC','','','','','','MWM_SNC_100PC',$
          'MWM_SNC_250PC','MWM_RV_LONG-BPLATES','MWM_RV_SHORT-BPLATES','MWM_RV_LONG-RM',$
          'MWM_RV_SHORT-RM','MWM_PLANET_TESS','MWM_YSO_CMZ','MWM_YSO_OB',$
          'MWM_YSO_S1','MWM_YSO_S2','MWC_YSO_S2-5','MWM_YSO_S3',$
          'MWM_YSO_CLUSTER','MWM_GG','MWM_DUST','MWM_TESSRGB',$
          'BHM_CSC_APOGEE','MWM_RV_LONG-FPS','MWM_RV_SHORT-FPS','',$
          '','','','']
  for i=0,n_elements(name)-1 do begin
    if is_bit_set(targ1,i) eq 1 then flag+=name[i]+','
  endfor
endif

lastcomma=strpos(flag,',',/reverse_search)
strput,flag,' ',lastcomma
return,strtrim(flag,2)

end

