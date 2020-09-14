pro plotc,x,y,z,err,min=min0,psym=psym,symsize=symsize,nocolorbar=nocolorbar,max=max0,_extra=extra,stp=stp,$
          trim=trim,format=format,overplot=overplot,yflip=yflip,xflip=xflip,xrange=xrange,$
          yrange=yrange,framecolor=framecolor,nodata=nodata,colpos=colpos,coldivisions=coldivisions,$
          log=log,bottom=bottom,ncolors=ncolors,title=title,charthick=charthick

;+
;
; Plot with each points' color specified
;
; INPUTS:
;  x             Array of X values
;  y             Array of Y values
;  z             Array of values to be used for color
;  min=          Min values for Z to be used for color. Z values
;                  less than min are set to min.
;  max=          Max values for Z to be used for color.  Z values
;                  greater than max are set to max.
;  /trim         Trim the ends (below min and above max).  Only plot
;                  points with (min<z<max)
;  psym=         Plot symbol
;  symsize=      Size of plot symbol
;  format=       Format for the colorbar
;  /nocolorbar   Do not plot a colorbar
;  /overplot     Overplot.  Don't erase previous plot.
;  /stp          Stop at the end of the program
;  /xflip        Reverse x-axis
;  /yflip        Reverse y-axis
;  =framecolor   The color of the frame, axis titles and annotations.
;  =colpos       Position array for the colorbar.
;  =coldivisions The number of colorbar divisions.  There will be
;                  (coldivisions+1) annotations.  The default is 6.
;  =bottom       The bottom value to use for the colors.  50 by default.
;  =ncolors      The number of colors/levels to use in the color
;                  range.  200 by default.
;  /log          Plot logarithm of Z.
;  ANY OTHER PLOT KEYWORDS CAN BE SET  (e.g. xrange, yrange, etc.)
;
; OUTPUTS:
;  Plot on the screen
;
; USAGE:
;  IDL>plotc,x,y,z,ps=1
;
; PROGRAMS USED:
;  SCALE.PRO
;  COLORBAR.PRO
;
; By D. Nidever   June 2007
;-

nx = n_elements(x)
ny = n_elements(y)
nz = n_elements(z)


; Not enough parameters input
if nx eq 0 or ny eq 0 then begin
  print,'Syntax - plotc,x,y,z,min=min,max=max,psym=psym,symsize=symsize,nocolorbar=nocolorbar,'
  print,'               framecolor=framecolor,  other plot keywords'
  return
endif

x0 = x
y0 = y

; X/YRANGE
if keyword_set(xrange) then xr=xrange
if keyword_set(yrange) then yr=yrange
if keyword_set(charthick) then charthick=charthick
if keyword_set(xflip) then begin
  if n_elements(xr) eq 0 then xr = [min(x),max(x)]
  xr = reverse(xr)
endif
if keyword_set(yflip) then begin
  if n_elements(yr) eq 0 then yr = [min(y),max(y)]
  yr = reverse(yr)
endif


; Original plot
position = [0.08,0.22,0.95,0.85]
;position = [0.08,0.08,0.95,0.85]
;if keyword_set(nocolorbar) then position = [0.08,0.05,0.95,0.98]
if keyword_set(overplot) then noerase=1 else noerase=0
if nz eq 0 then position = [0.08,0.08,0.95,0.95]
if !p.multi[1] gt 1 or !p.multi[2] gt 1 then undefine,position

if n_elements(psym) gt 1 then tpsym=3 else tpsym=psym
if not keyword_set(overplot) then begin
  PLOT,x,y,_extra=extra,/nodata,psym=tpsym,symsize=symsize,noerase=noerase,position=position,$
       xrange=xr,yrange=yr,co=framecolor,charthick=charthick
endif

; Colors input
if nz gt 0 then begin

  if nz ne nx then begin
    print,'Z and X must have same number of elements'
    return
  endif

  z0 = z

  ; Get colors
  if n_elements(min0) eq 0 then min=min(z) else min=min0
  if n_elements(max0) eq 0 then max=max(z) else max=max0

  ; Trimming the ends
  if keyword_set(trim) then begin
    gd = where(z ge min and z le max,ngd)
    ; No points left
    if ngd eq 0 then begin
      print,'NO POINTS LEFT'
      return
    endif
    x0 = x0[gd]
    y0 = y0[gd]
    z0 = z0[gd]
  endif

  if n_elements(bottom) eq 0 then bottom = 50
  if n_elements(ncolors) eq 0 then ncolors = 200
  color = (z0>min)<max
  color = SCALE( color, [min,max], [bottom, bottom+ncolors-1])

  if keyword_set(log) then begin

    ; Copied from IMGSCL.PRO

    ; We have negative numbers, rescale
    if min(z0) le 0.0 then begin
      tmp = 1.0 + (z0 <max >min) - min
      tmp = ALog10(Temporary(tmp) > 0.01)
      max_log = alog10(1.0 + max - min)
      ;image = BytScl(tmp, Min=0.0, Max=max_lvlg, Top=top-1B) + 1B
      color = SCALE( tmp, [0.0,max_log], [bottom, bottom+ncolors-1])

    ; All positive, just take the log
    ; The scheme above does not work well for very small, POSITIVE numbers
    endif else begin
      tmp = ALog10(z0)
      min_log = alog10(min)
      max_log = alog10(max)
      ;image = BytScl(tmp, Min=min_lvlg, Max=max_lvlg, Top=top-1B) + 1B
      color = SCALE( tmp, [min_log,max_log], [bottom, bottom+ncolors-1])
    endelse

  endif

  ; Plot with colors
  if not keyword_set(nodata) then begin
    if n_elements(psym) eq 1 then $
      PLOTS,x0,y0,color=color,noclip=0,psym=psym,symsize=symsize $
    else $
      for ip=0,n_elements(x0)-1 do PLOTS,x0[ip],y0[ip],color=color[ip],noclip=0,psym=symcat(psym[ip]),symsize=symsize 
    if n_elements(err) gt 0 then for ip=0,n_elements(x0)-1 do begin
      !p.color=color[ip]
      oploterr,[x0[ip]],[y0[ip]],[err[ip]],3
    endfor
  endif

  ; Colorbar
  if not keyword_set(nocolorbar) then begin

    ; Copied from displayc.pro

    ; Log scaling
    if keyword_set(log) then begin

      xlog = 1
      minor = 9
      coldivisions = 0

      len = strlen(strtrim(long(min),2)) > strlen(strtrim(long(max),2))
      if min lt 1.0 then form = '(G'+strtrim(len+4,2)+'.2)'

      minrange = min
      if min eq 0. and keyword_set(log) then minrange = 1.   ; check imgscl.pro, log=0.01
      maxrange = max

    ; Linear scaling
    endif else begin

      ; Linear scaling
      len = strlen(strtrim(long(min),2)) > strlen(strtrim(long(max),2))
      if min lt 0.0 then len=len+1    ; need another space for negative sign

      scal = abs(max) > abs(min)
      frac = abs(max-min)/6.      ; 6 divisions
      pow = alog10(frac)
      npow = round(pow-1)        ; want an extra decimal space
      if npow ge 0 then form = '(I'+strtrim(len,2)+')'
      if npow lt 0 then form = '(F'+strtrim(len+abs(npow)+1,2)+'.'+strtrim(abs(npow),2)+')'

      ; Really large numbers
      if max gt 1e5 then form = '(G8.2)'                  ; room for two sig figs, sign and exponent

      xlog = 0

      minrange = min
      maxrange = max

    endelse


    if keyword_set(format) then form=format

    if not keyword_set(colpos) then colpos = [0.08,0.92,0.95,0.95]
    if not keyword_set(coldivisions) then coldivisions=6  ; default
    if !p.multi[1] gt 1 or !p.multi[2] gt 1 then begin
      colpos[0]=!x.region[0]+0.2*(!x.region[1]-!x.region[0])
      colpos[1]=!y.region[0]+0.94*(!y.region[1]-!y.region[0])
      colpos[2]=!x.region[0]+0.85*(!x.region[1]-!x.region[0])
      colpos[3]=!y.region[0]+0.96*(!y.region[1]-!y.region[0])
    endif

    ; Displaying the colorbar
    COLORBAR,minrange=minrange,maxrange=maxrange,position=colpos,bottom=bottom,ncolors=ncolors,format=form,$
             color=framecolor,divisions=coldivisions,xlog=xlog,minor=minor,title=title,charthick=charthick


  endif

  ; Leave with the original coordinate system
  if not keyword_set(overplot) and !p.multi[1] eq 1 and !p.multi[2] eq 1 then $
  PLOT,x,y,_extra=extra,/nodata,psym=psym,symsize=symsize,/noerase,position=position,$
       xrange=xr,yrange=yr,co=framecolor,charthick=charthick

; No color input
endif else begin ; colors input

  oplot,x,y,_extra=extra,psym=psym,symsize=symsize

endelse

;print,position
if keyword_set(stp) then stop

end
