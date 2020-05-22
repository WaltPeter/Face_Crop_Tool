import warnings 
warnings.filterwarnings("ignore")

import os
import cv2
import json
import time
import numpy as np
import tensorflow as tf
from nms_wrapper import NMSType, NMSWrapper
from faster_rcnn_wrapper import FasterRCNNSlim 

class Plugin: 
    '''
    Core functions 
    '''

    def detect(self, image):
        # pre-processing image for Faster-RCNN
        img_origin = image.astype(np.float32, copy=True)
        img_origin -= np.array([[[102.9801, 115.9465, 112.7717]]])

        img_shape = img_origin.shape
        img_size_min = np.min(img_shape[:2])
        img_size_max = np.max(img_shape[:2])

        img_scale = 600 / img_size_min
        if np.round(img_scale * img_size_max) > 1000:
            img_scale = 1000 / img_size_max
        img = cv2.resize(img_origin, None, None, img_scale, img_scale, cv2.INTER_LINEAR)
        img_info = np.array([img.shape[0], img.shape[1], img_scale], dtype=np.float32)
        img = np.expand_dims(img, 0)

        # test image
        _, scores, bbox_pred, rois = self.net.test_image(self.sess, img, img_info)

        # bbox transform
        boxes = rois[:, 1:] / img_scale

        boxes = boxes.astype(bbox_pred.dtype, copy=False)
        widths = boxes[:, 2] - boxes[:, 0] + 1
        heights = boxes[:, 3] - boxes[:, 1] + 1
        ctr_x = boxes[:, 0] + 0.5 * widths
        ctr_y = boxes[:, 1] + 0.5 * heights
        dx = bbox_pred[:, 0::4]
        dy = bbox_pred[:, 1::4]
        dw = bbox_pred[:, 2::4]
        dh = bbox_pred[:, 3::4]
        pred_ctr_x = dx * widths[:, np.newaxis] + ctr_x[:, np.newaxis]
        pred_ctr_y = dy * heights[:, np.newaxis] + ctr_y[:, np.newaxis]
        pred_w = np.exp(dw) * widths[:, np.newaxis]
        pred_h = np.exp(dh) * heights[:, np.newaxis]
        pred_boxes = np.zeros_like(bbox_pred, dtype=bbox_pred.dtype)
        pred_boxes[:, 0::4] = pred_ctr_x - 0.5 * pred_w
        pred_boxes[:, 1::4] = pred_ctr_y - 0.5 * pred_h
        pred_boxes[:, 2::4] = pred_ctr_x + 0.5 * pred_w
        pred_boxes[:, 3::4] = pred_ctr_y + 0.5 * pred_h
        # clipping edge
        pred_boxes[:, 0::4] = np.maximum(pred_boxes[:, 0::4], 0)
        pred_boxes[:, 1::4] = np.maximum(pred_boxes[:, 1::4], 0)
        pred_boxes[:, 2::4] = np.minimum(pred_boxes[:, 2::4], img_shape[1] - 1)
        pred_boxes[:, 3::4] = np.minimum(pred_boxes[:, 3::4], img_shape[0] - 1)
        return scores, pred_boxes


    def fmt_time(self, dtime):
        if dtime <= 0:
            return "0:00.000"
        elif dtime < 60:
            return "0:%02d.%03d" % (int(dtime), int(dtime * 1000) % 1000)
        elif dtime < 3600:
            return "%d:%02d.%03d" % (int(dtime / 60), int(dtime) % 60, int(dtime * 1000) % 1000)
        else:
            return "%d:%02d:%02d.%03d" % (int(dtime / 3600), int((dtime % 3600) / 60), int(dtime) % 60,
                                        int(dtime * 1000) % 1000)


    '''
    Plugin initializations 
    '''
    def __init__(self, interface, image_handler): 
        self.result = dict() 
        self.interface = interface 
        self.image_handler = image_handler 
        self.nms_thresh = 0.3 
        self.conf_thresh = 0.8 
        self.nms_type = NMSType.CPU_NMS
        self.nms = NMSWrapper(self.nms_type)
        self.funcs = [{"name": "Detect face", "func": self.predict, "args": None}, 
                      {"name": "All faces", "func": self.predict, "args": self.image_handler.image_paths}] 

    def load(self, base): 
        cfg = tf.ConfigProto()
        cfg.gpu_options.allow_growth = True
        self.sess = tf.Session(config=cfg)
        self.net = FasterRCNNSlim() 
        saver = tf.train.Saver()
        path = os.path.join(base, "animeFace/model/res101_faster_rcnn_iter_60000.ckpt")
        try: 
            saver.restore(self.sess, path) 
        except: print("animeFace:", path); return False 
        return True 


    '''
    Plugin destructions 
    '''
                
    def close(self): 
        try: self.sess.close() 
        except: pass 
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
    Plugin functions 
    '''

    def predict(self, paths): 
        if self.image_handler.is_video_mode(): 
            result = self.predictVid(paths is not None) 
            return result 
        if paths is None: 
            paths = [self.image_handler.get_path()] 
        file_len = len(paths)
        result = dict() 
        self.interface._progress_dialog("Finding face") 
        for idx, path in enumerate(paths): 
            try: 
                path = str(path) 
                
                r = self.try_get_from_json(path)
                if r is not None: 
                    result[path] = r
                    continue  
                
                img = cv2.imread(path)  
                scores, boxes = self.detect(img)
                boxes = boxes[:, 4:8]
                scores = scores[:, 1]
                keep = self.nms(np.hstack([boxes, scores[:, np.newaxis]]).astype(np.float32), self.nms_thresh)
                boxes = boxes[keep, :]
                scores = scores[keep]
                inds = np.where(scores >= self.conf_thresh)[0]
                scores = scores[inds]
                boxes = boxes[inds, :]

                for i in range(scores.shape[0]): 
                    x1, y1, x2, y2 = boxes[i, :].tolist()
                    w = x2 - x1; h = y2 - y1 
                    cx = (x2 + x1) / 2; cy = (y2 + y1) / 2 
                    s = min(w,h) / 2
                    x1 = (cx-s) / img.shape[1]; x2 = (cx+s) / img.shape[1] 
                    y1 = (cy-s) / img.shape[0]; y2 = (cy+s) / img.shape[0]
                    new_result = {"score": float(scores[i]), "bbox": [x1,y1,x2,y2]}
                    try: result[path].append(new_result) 
                    except: result[path] = list(); result[path].append(new_result) 
                self.interface.dialog.progressbar.update_progressbar((idx+1)/(len(paths)))
            except Exception as e: 
                print(str(e)) 
                if "closed Session" in str(e): 
                    break  

        self.interface.dialog.progressbar.update_progressbar(1.)
        self.dump_result(result) 
        return result 

    
    def predictVid(self, all_frames): 
        if all_frames: 
            paths = self.image_handler.image_paths 
        else: 
            paths = [self.image_handler.get_path()] 
        file_len = len(paths)
        result = dict() 
        self.interface._progress_dialog("Finding face") 

        for idx, path in enumerate(paths): 
            if not all_frames: idx = self.image_handler.iter
            try: 
                path = str(path) 
                
                r = self.try_get_from_json(path)
                if r is not None: 
                    result[path] = r
                    continue  
                
                img = self.image_handler.get_frame(idx) 
                scores, boxes = self.detect(img) 
                boxes = boxes[:, 4:8]
                scores = scores[:, 1]
                keep = self.nms(np.hstack([boxes, scores[:, np.newaxis]]).astype(np.float32), self.nms_thresh)
                boxes = boxes[keep, :]
                scores = scores[keep]
                inds = np.where(scores >= self.conf_thresh)[0]
                scores = scores[inds]
                boxes = boxes[inds, :]

                for i in range(scores.shape[0]): 
                    x1, y1, x2, y2 = boxes[i, :].tolist()
                    w = x2 - x1; h = y2 - y1 
                    cx = (x2 + x1) / 2; cy = (y2 + y1) / 2 
                    s = min(w,h) / 2
                    x1 = (cx-s) / img.shape[1]; x2 = (cx+s) / img.shape[1] 
                    y1 = (cy-s) / img.shape[0]; y2 = (cy+s) / img.shape[0]
                    new_result = {"score": float(scores[i]), "bbox": [x1,y1,x2,y2]}
                    try: result[path].append(new_result) 
                    except: result[path] = list(); result[path].append(new_result) 
                self.interface.dialog.progressbar.update_progressbar((idx+1)/(len(paths)))
            except Exception as e: 
                print(str(e))  
                if "closed Session" in str(e): 
                    break  

        self.interface.dialog.progressbar.update_progressbar(1.)
        self.dump_result(result) 
        return result 
        