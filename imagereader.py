##########################################
#Loops through all .rac files for a given day and extracts payload data and stores it 
#as Python dicts. (Later store in SQL database) 
##########################################

#Created 17.03.09 Ole Martin Christensen

#This lists all .rac files and extracts them. Result in one large python dict containing all files from that
#day and one dict with all images
#
#Currently the code saves data multiple times, in particular the images are save as both hex, 
#binary (to be written out to .jpeg) and .jpeg files, as well as in the original packets. 
#
#remove import of print function after upgrade to python 3
from __future__ import print_function

from os import listdir
import numpy as np
from read_racfile import read_racfile
import json
from JSON_Encoder import JSON_Encoder
import binascii
import sys
import subprocess
from PIL import Image
import os

#import json


AllDataSorted = [] #List of dicts. Each entry is a packet
CCD_image_data = {} #List of dicts. Each entry is a CCD image
CCD_meta_data = {}



def check_and_make_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

#Call external application for conversion of 12 bit jpeg
def read12bit_jpeg(fileName):
        djpegLocation = './djpeg'
        outputFile = fileName[:-4] + ".pnm"
    
        batcmd = djpegLocation + ' -pnm -outfile ' +outputFile + ' ' + fileName #call jpeg decompression executable            
        imagedata = subprocess.check_output(batcmd,shell=True) #load imagedata including header

        with open(outputFile,'rb') as f:
            imagedata=f.read()
                
        newLine=b'\n'
        imagedata=imagedata.split(newLine,3)    #split into magicnumber, shape, maxval and data

        imsize = imagedata[1].split() #size of image in height/width
        imsize = [int(i) for i in imsize]
        imsize.reverse() #flip size to get width/heigth
        
        im = np.frombuffer(imagedata[3], dtype=np.uint16) #read image data
        
        im = im.reshape(imsize) #reshape image
        return im

#save pnm file if uncompressed images are used    
def read16bit_pnmfile(filename):
        im_object = Image.open(filename)
        im = np.asarray(im_object)
        return im

def extract_racfile(directory,racfile):
    

    print(str('Reading file ' + racfile))
    out_directory = racfile
    check_and_make_directory(out_directory)
    check_and_make_directory(out_directory+'/IMAGES/')
    check_and_make_directory(out_directory+'/JSON/')
    
    #Merge CCD data from several files
    CCD_image_data['channel 1'] = []
    CCD_image_data['channel 2'] = []
    CCD_image_data['channel 3'] = []
    CCD_image_data['channel 4'] = []
    CCD_image_data['channel 5'] = []
    CCD_image_data['channel 6'] = []
    CCD_image_data['channel 7'] = []
    
    #data needed for saving actual image to either jpg or pnm-file
    CCD_meta_data['channel 1'] = []
    CCD_meta_data['channel 2'] = []
    CCD_meta_data['channel 3'] = []
    CCD_meta_data['channel 4'] = []
    CCD_meta_data['channel 5'] = []
    CCD_meta_data['channel 6'] = []
    CCD_meta_data['channel 7'] = []
    
    #read file and put data into AllDataSorted
    data_from_file = read_racfile(directory+racfile)
    AllDataSorted.extend(data_from_file)
    
    
    #Go through the channels and save and metadata into output directory
    for j in range(0,7):
        #loop over channels
    
        n = -1
        for x in range(0,len(AllDataSorted)):
            if AllDataSorted[x]['Source_data']['SID_mnemonic'] == ['CCD data channel '+str(j+1)]:
                
                #go through all packets in that image and put image data and meta data into structures
                if AllDataSorted[x]['SPH_grouping_flags'] == '01' or AllDataSorted[x]['SPH_grouping_flags'] == '11':
                    n = n+1 #start new image
                    #print 'CCD data start'
                    CCD_image_data['channel '+str(j+1)].append({}) #start new image
                    CCD_image_data['channel '+str(j+1)][n]['data'] = [] 
                    CCD_image_data['channel '+str(j+1)][n]['start'] = x 
                    CCD_image_data['channel '+str(j+1)][n]['cont'] = [] 
                    CCD_image_data['channel '+str(j+1)][n]['stop'] = []
                    #Add data to image
                    CCD_image_data['channel '+str(j+1)][n]['data'].append(AllDataSorted[x]['Source_data']['IMG'])
                    
                    CCD_meta_data['channel '+str(j+1)].append({})
                    CCD_meta_data['channel '+str(j+1)][n]['JPEGQ']=AllDataSorted[x]['Source_data']['JPEGQ'][0]
                    CCD_meta_data['channel '+str(j+1)][n]['NROW']=AllDataSorted[x]['Source_data']['NROW'][0]
                    CCD_meta_data['channel '+str(j+1)][n]['NCOL']=AllDataSorted[x]['Source_data']['NCOL'][0]
                    
                elif AllDataSorted[x]['SPH_grouping_flags'] == '10':
                    #print 'CCD data stop'
                    CCD_image_data['channel '+str(j+1)][n]['stop'] = x 
                    CCD_image_data['channel '+str(j+1)][n]['data'].append(AllDataSorted[x]['Source_data']['IMG'])
                elif AllDataSorted[x]['SPH_grouping_flags'] == '00':
                    if not CCD_image_data['channel '+str(j+1)]:
                        print('Warning: current .rac file started with continued CCD data for this channel')
                        if n==-1:#currently a work-around
                            CCD_image_data['channel '+str(j+1)].append({})
                            CCD_image_data['channel '+str(j+1)][n+1]['cont'] = []
                            CCD_image_data['channel '+str(j+1)][n+1]['data'] = []
                    CCD_image_data['channel '+str(j+1)][n]['cont'].append(x) 
                    CCD_image_data['channel '+str(j+1)][n]['data'].append(AllDataSorted[x]['Source_data']['IMG'])
        
        #for each channel join together image data from different packets
        for x in range(0,len(CCD_image_data['channel '+str(j+1)])):
            #get-function allows to check if keywords are existing or not
            if CCD_image_data['channel '+str(j+1)][x].get('start')!=None and CCD_image_data['channel '+str(j+1)][x].get('stop')!=None:
                if CCD_image_data['channel '+str(j+1)][x]['start'] and CCD_image_data['channel '+str(j+1)][x]['stop']:
                    a = "".join(CCD_image_data['channel '+str(j+1)][x]['data'])
                    CCD_image_data['channel '+str(j+1)][x]['image'] = binascii.unhexlify(a)
                    CCD_image_data['channel '+str(j+1)][x]['error'] = 0
                else:
                    print('Warning: start or stop does not exist for image: ' + str(x)+', channel '+str(j+1))
                    CCD_image_data['channel '+str(j+1)][x]['error'] = 1
            else:
                print('Warning: start or stop key does not exist for image: ' + str(x)+', channel '+str(j+1))
                CCD_image_data['channel '+str(j+1)][x]['error'] = 1
       
     #end channel loop  
    
    #store all packets from racfile in JSON folder
    filename = out_directory + '/JSON/racfile.json'
    with open(filename, 'w') as outfile:
        print(str('Writing file ' + filename))
        json.dump(AllDataSorted, outfile, sort_keys = True, indent = 4,
               ensure_ascii = False,cls=JSON_Encoder)

    #for each image store image and metadata
    for j in range(0,7):#loop over channels again
        for i in range(len(CCD_image_data['channel '+str(j+1)])):
        #Write images out as jpeg (if compressed image used) and pnm
            CCD_image_data['channel '+str(j+1)][i]['filename'] = ''
            if (CCD_image_data['channel '+str(j+1)][i].get('error') == 0):
                #check JPEGQ to determine type of image (jpg or pnm)     
                filename = out_directory + '/IMAGES/channel'+str(j+1)+'_image_'+ str(i) + '.json'
                with open(filename, 'w') as outfile:
                    json.dump(CCD_meta_data['channel '+str(j+1)][i], outfile, sort_keys = True, indent = 4, ensure_ascii = False,cls=JSON_Encoder)
                
                if (CCD_meta_data['channel '+str(j+1)][i].get('JPEGQ')<=100):
                    filename = out_directory + '/IMAGES/channel'+str(j+1)+'_image_'+ str(i) + '.jpg'
                    print(str('Writing file ' + filename))
                    CCD_image_data['channel '+str(j+1)][i]['filename'] = filename
                    with open(filename,'w') as f:
                        f.write(CCD_image_data['channel '+str(j+1)][i]['image'])
                    
                    read12bit_jpeg(filename) #create pnm file
                    
                else:
                    filename = out_directory + '/IMAGES/image'+str(j+1)+'_'+ str(i) + '.pnm'
                    print(str('Writing file ' + filename))
                    CCD_image_data['channel '+str(j+1)][i]['filename'] = filename
                    cols=int(CCD_meta_data['channel '+str(j+1)][i]['NCOL'])+1
                    rows=int(CCD_meta_data['channel '+str(j+1)][i]['NROW'])
                    pnm_header="P5\n"+str(cols)+" "+str(rows)+"\n65535\n"
                    #image_data=np.frombuffer(CCD_image_data['data channel '+str(j+1)][i]['image'])
                    image_data=CCD_image_data['channel '+str(j+1)][i]['image']
                    with open(filename,'w') as f:
                        f.write(pnm_header)
                        #f.write(image_data.byteswap().tobytes())
                        f.write(image_data)
                    
    #end loop over channels
    
    return AllDataSorted, CCD_image_data


def read_MATS_image(filename):
    json_file = open(filename + '.json','r')
    metadata = json.load(json_file)
    json_file.close
    
    if metadata['JPEGQ']<=100:
        image_data = read12bit_jpeg(filename + '.jpg')
    else:
        image_data = read16bit_pnmfile(filename + '.pnm')

    return image_data, metadata
    

if __name__ == '__main__':
    
    extract_racfile(sys.argv[1],sys.argv[2])