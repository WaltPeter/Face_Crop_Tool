import os
import cv2
import json
import time
import numpy as np

class Plugin: 
    '''
    Plugin initializations. 
    '''

    def __init__(self):
        super().__init__()

    def load(self, base): 
        try: 
            path = os.path.join(base, "lbpcascade_animeface", "Cascade", "lbpcascade_animeface.xml")
            self.cascade = cv2.CascadeClassifier(path) 
        except Exception as e: print("lbpcascade_animeface:", e); return False 
        return True 

    
    '''
    Plugin destructions 
    '''

    def close(self): 
        print("Plugin closed.") 

    
    ''' 
    Plugin functions. 
    '''