import os 
import cv2 
import pathlib
import numpy as np 
from tqdm import tqdm 

'''
A simple script to remove similar images in a given list of paths. 
For each path in path list, read img, resize to a standard size of 64*64, 
for each image in encountered unique image, calculate the norm L2 distance. 
If distance within a threshold value (1.), considered to be similar. 
Push into a list for each 'unique' image. Limit the length of this list if 
`batch_size` is specified. Similar images are directly deleted. 

'''


class Tool: 
    '''
    Tool initializations. 
    '''

    def __init__(self, image_paths, interface, batch_size=0):
        self.batch_size = batch_size 
        self.interface = interface 
        self.iter = 0 
        self.image_paths = image_paths 
        self.unique_images = list() 

    def batch_check(self): 
        # Limit the size of unique images to be collected for either 
        # performance issue or memory issue. 
        if self.batch_size <= 0: 
            return 
        l = len(self.unique_images)
        if l > self.batch_size: 
            for _ in range(l - self.batch_size): 
                self.unique_images.pop(0) 
    
    
    '''
    Tool RUN function. 
    ''' 

    def run(self): 
        removed = 0 
        self.interface._progress_dialog("Removing similar images") 
        for idx, path in enumerate(self.image_paths): 

            # Update progressbar progress. 
            self.interface.dialog.progressbar.update_progressbar((idx+1)/(len(self.image_paths))) 

            try: 
                img = cv2.resize(cv2.imread(str(path)), (64,64))  
                status = False 
                for i in range(len(self.unique_images)): 
                    unique_image = self.unique_images[len(self.unique_images)-i-1] 
                    if cv2.norm(img, unique_image, cv2.NORM_L2) / (64*64) < 1: 
                        # Not unique, delete image. 
                        try: os.remove(str(path)); removed += 1 
                        except Exception as e: print("Error:", e) 
                        break 
                        status = True 
                if status: continue
                # Is unique. 
                self.unique_images.append(img) 
                self.batch_check() 
            except Exception as e1: print("Error:", e1) 

        # Show a info dialog. 
        self.interface._info_dialog(f"{removed} similar images found and removed.") 
        print(f"{removed} similar images found and removed.") 
