# Programmed for counting number of GCs around a galaxy and calcuating specific frequency
#Lejay Chen

'''
data saved in: dEdata.fits
     region file: item.selected.reg
  CC diagram: item.cc.png
         SN plot: SNtoV_doubled.png(or .eps)

read-in files:
'100galaxies.xlsx'(in plot_SN())  'sdss_data4.fits'  'den.used'   field catalogs     

magnitude and effective radius from SDSS DR6 
distance modulus from NED
'''

from astropy.table import *
from astropy.io import fits
from astropy.wcs import WCS
from math import *
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from reg_gcs import *
from cc_diagram import *
from plot_SN import *
import os

def selection2(u, g, z, g_best, i, i_4):
	if g-z<1.5 and g-z>0.62 and u-g>0.8 and u-g<1.79 and 18.5<g_best<24.4 and i_4-i>-0.15 and i_4-i<0.25:
		if g-z< 0.77*(u-g)+0.35 and g-z>0.95*(u-g)-0.31:
			return 1  #is gc
		else:
			return 0  #is not gc
	else:
		return 0  #is not gc

filelist = open('den.used').readlines() #list of galaxies
tbl = Table.read('sdss_data4.fits')  #data from SDSS DR6 and NED

gc_num = []
contamination = []
gcs = Table()
#select GC in catalogs around each galaxy
for i in range(len(filelist)):
	item = filelist[i].rstrip()  #index of the galaxy

 	w = WCS(item+'.fits')
 	ra_center,dec_center = w.all_pix2world(200.5,200.5,0)# Pixel to WCS
 	print item#,r_e,tbl[i]['m_M'],ra_center,dec_center

 	image = fits.open(item+'.fits')
 	header = image[0].header
	field = header['object']  #NGVS field name  

	r_e = tbl[i]['petroR50_r']  #effective radius : petrosian R50 
	r =  r_e*4  # r~radius for counting GCs

	cat_field = Table.read('../catalog/cat_apcor/'+field+'.l.Mg002.sexcat.apcor.fits')  # NGVS field catalog

	#luminosity cut: cat_field1  for clear plot
	mask = cat_field['MAGCOR_AP8'][:,1]<22  #only plot objects brighter than mag_g=22
	cat_field1 = cat_field[mask] 
	u_all = cat_field1['MAGCOR_AP8'][:,0]
	g_all = cat_field1['MAGCOR_AP8'][:,1]
	z_all = cat_field1['MAGCOR_AP8'][:,4]

	#region cut: cat_field2  cut an area around the target galaxy
	mask1 = abs(cat_field['RA'] - ra_center) <sqrt(2)*r/3600.
	cat_field2 = cat_field[mask1]
	mask2 = abs(cat_field2['DEC'] - dec_center) < sqrt(2)*r/3600.
	cat_field2 = cat_field2[mask2]
             #count GC numbers
	indices = []
	u = cat_field2['MAGCOR_AP8'][:,0]
	g = cat_field2['MAGCOR_AP8'][:,1]
	z = cat_field2['MAGCOR_AP8'][:,4]
	g_best = cat_field2['MAG_BEST'][:,1]
	i = cat_field2['MAGCOR_AP8'][:,3]
	i_4 = cat_field2['MAGCOR_AP4'][:,3]
	for k in range(len(cat_field2.field(0))):
		ra = cat_field2['RA'][k]
		dec = cat_field2['DEC'][k]
		#  if object in radius r, count as one candidate
		#  if object between radius r and sqrt(2)*r, count as a contamination
		#  These two regions have the same area
		if sqrt((cat_field2['RA'][k] - ra_center)**2 + (cat_field2['DEC'][k] - dec_center)**2) < r/3600.:
			indices.append(selection2(u[k], g[k], z[k], g_best[k], i[k], i_4[k]))
		elif sqrt((cat_field2['RA'][k] - ra_center)**2 + (cat_field2['DEC'][k] - dec_center)**2) < sqrt(2)*r/3600.:
			indices.append(selection2(u[k], g[k], z[k], g_best[k], i[k], i_4[k])*2)
		else:
			indices.append(0)

	indices = np.array(indices)
	gcs = vstack([gcs,cat_field2[indices==1]])
	gc_num.append(len(indices[indices==1])*2)  #gc_num doubled because of truncation of GCLF
	contamination.append(len(indices[indices==2])*2) # contamination count  (error bar)
	
	cc_diagram(u_all,g_all,z_all,u,g,z,item,indices)  #Color-Color Diagram
	build_reg(item,cat_field2,indices)  #build region file for ds9 use

#caluculate and plot SN
dEdata = Table(names=('Index','ra','dec','m-M','MV','SN','SNerr','M_z','SN_z','SN_z_err'),dtype=('a4','f8','f8','f4','f4','f4','f4','f4','f4','f4')) #save galaxy data in text for confirmation
for i in range(len(filelist)):

	z = tbl[i]['modelMag_z']
	m_M = round(tbl[i]['m_M'],1)
	Mz = round(z -  m_M, 1)  #absolute magnitude

	#absolute magnitude
	V = tbl[i]['modelMag_g']  - 0.59*( tbl[i]['modelMag_g']  - tbl[i]['modelMag_r']  ) - 0.01  #magnitude transfermation from SDSS to UBV
	MV = round(V - tbl[i]['m_M'],1) 

             # specific frequency
	SN = round(gc_num[i]*10**(0.4*(MV+ 15 )),1)
	SN_z = round(gc_num[i]*10**(0.4*(Mz+ 15 )),1)

             #error bar calculated from contamination
	SN_err = round(contamination[i]*10**(0.4*(MV+ 15)),1)  
	SN_z_err = round(contamination[i]*10**(0.4*(Mz+ 15)),1)

	dEdata.add_row((filelist[i].rstrip(),round(tbl[i]['ra'],5),round(tbl[i]['dec'],5),m_M,MV,SN,SN_err,Mz,SN_z,SN_z_err))

if os.path.isfile('dEdata.fits'):
	os.system('rm dEdata.fits')
	os.system('rm gcs.around.dEN.fits')
gcs.write('gcs.around.dEN.fits')
dEdata.write('dEdata.fits')
plot_SN()#plot SN_list to MV diagram along with data from literature