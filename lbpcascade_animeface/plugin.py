import os
import cv2
import json
import time
import numpy as np

endFlag = False 

class Plugin: 
    '''
    Plugin initializations. 
    '''

    def __init__(self, interface, image_handler): 
        self.result = dict() 
        self.interface = interface 
        self.image_handler = image_handler 

        # Specify plugin functions availabled. 
        self.funcs = [{"name": "Detect face", "func": self.predict, "args": None}, 
                      {"name": "All faces", "func": self.predict, "args": self.image_handler.image_paths}] 

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
        global endFlag 
        endFlag = True 
        print("Plugin closed.") 


    '''
    Private functions. 
    '''

    def dump_result(self, result): 
        for name in result: self.result[name] = result[name] 
        self.save_json() 

    def save_json(self): 
        if len(self.result) < 1: return 
        try: 
            fname = os.path.join(os.path.split([name for name in self.result][0])[0], "output.json")
            with open(fname, "w") as f: json.dump(self.result, f) 
        except: pass 

    def try_get_from_json(self, path): 
        if path not in self.result: 
            try: 
                fname = os.path.join(os.path.split(path)[0], "output.json")
                with open(fname, "r") as f: self.result = json.load(f) 
            except: pass 
        if path in self.result: 
            print("From cache.")
            return self.result[path] 
        else: return None 

    
    ''' 
    Plugin functions. 
    '''

    def predict(self, paths): 

        # If opened is video in imageHandler: 
        if self.image_handler.is_video_mode(): 
            # Use predictVid function instead. 
            result = self.predictVid(paths is not None) 
            return result 
        # Else not video: 

        #   Got a None if requested to detect single image. 
        if paths is None: 
            #   Force it to be a list. 
            paths = [self.image_handler.get_path()] 

        #   Number of paths. 
        file_len = len(paths)
        result = dict() 

        #   Create a progress dialog in Interface. 
        self.interface._progress_dialog("Finding face") 

        #   For each path: 
        for idx, path in enumerate(paths): 
            global endFlag
            if endFlag: break 
            try: 
                path = str(path) 
                
                #   Try to get result from saved json. 
                r = self.try_get_from_json(path)
                if r is not None: 
                    result[path] = r
                    continue  
                
                #   Not in json: 
                #       Read image and detect. 
                img = cv2.imread(path, 0)  
                faces = self.cascade.detectMultiScale(img,
                                     # detector options
                                     scaleFactor = 1.1,
                                     minNeighbors = 5,
                                     minSize = (24, 24))

                result[path] = list() 
                for (x1, y1, w, h) in faces: 
                    x2 = x1 + w; y2 = y1 + h
                    cx = (x2 + x1) / 2; cy = (y2 + y1) / 2 
                    s = min(w,h) / 2
                    x1 = (cx-s) / img.shape[1]; x2 = (cx+s) / img.shape[1] 
                    y1 = (cy-s) / img.shape[0]; y2 = (cy+s) / img.shape[0]
                    new_result = {"bbox": [x1,y1,x2,y2]}
                    result[path].append(new_result) 

                #   Update progressbar progress. 
                self.interface.dialog.progressbar.update_progressbar((idx+1)/(len(paths))) 

            except Exception as e: 
                print(str(e)) 

        # Update progressbar progress to 1. 
        self.interface.dialog.progressbar.update_progressbar(1.)
        self.dump_result(result) 
        return result 


    # Minor edit for video mode. 
    def predictVid(self, all_frames): 
        # Whole video: 
        if all_frames: paths = self.image_handler.image_paths 
        # Or current frame: 
        else: paths = [self.image_handler.get_path()] 
        
        file_len = len(paths)
        result = dict() 
        self.interface._progress_dialog("Finding face") 

        for idx, path in enumerate(paths): 
            if not all_frames: idx = self.image_handler.iter
            global endFlag
            if endFlag: break 
            try: 
                path = str(path) 
                
                r = self.try_get_from_json(path)
                if r is not None: 
                    result[path] = r
                    continue  
                
                img = self.image_handler.get_frame(idx) 
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) 

                faces = self.cascade.detectMultiScale(img,
                                     # detector options
                                     scaleFactor = 1.1,
                                     minNeighbors = 5,
                                     minSize = (24, 24))

                result[path] = list()
                for (x1, y1, w, h) in faces: 
                    x2 = x1 + w; y2 = y1 + h
                    cx = (x2 + x1) / 2; cy = (y2 + y1) / 2 
                    s = min(w,h) / 2
                    x1 = (cx-s) / img.shape[1]; x2 = (cx+s) / img.shape[1] 
                    y1 = (cy-s) / img.shape[0]; y2 = (cy+s) / img.shape[0]
                    new_result = {"bbox": [x1,y1,x2,y2]}
                    result[path].append(new_result) 

                #   Update progressbar progress. 
                self.interface.dialog.progressbar.update_progressbar((idx+1)/(len(paths))) 

            except Exception as e: 
                print(str(e)) 

        # Update progressbar progress to 1. 
        self.interface.dialog.progressbar.update_progressbar(1.)
        self.dump_result(result) 
        return result 
