import os 
import cv2 
import sys
import math 
import pathlib 
import threading
import numpy as np 
from tqdm import tqdm
from time import time 
from tkinter import Tk


endFlag = False 
threadList = list() 

class Thread (threading.Thread):
   def __init__(self, name, function, args=None):
      threading.Thread.__init__(self)
      self.name = name
      self.function = function
      self.args = args
      threadList.append(self)
      
   def run(self):
      print("Starting {}. ".format(self.name))
      self.function(self.args)

   def joinThread(self): 
      self.join()
      threadList.pop(threadList.index(self))


class BuiltIns: 
    def __init__(self): 
        self.button_list = list() 

    def register_button(self, button): 
        self.button_list.append(button) 
    
    def mouse_event_button(self, button, x, y, click): 
        mouse_buttons = list() 
        for registered_button in self.button_list: 
            if x > registered_button.pt1[0] and x < registered_button.pt2[0] and \
               y > registered_button.pt1[1] and y < registered_button.pt2[1]: 
                mouse_buttons.append(registered_button) 
        mouse_buttons = sorted(mouse_buttons, key=lambda i:i.zIndex, reverse=True) 
        if mouse_buttons[0].text == button.text: return True 
        else: return False 

    def unregister_button(self, button): 
        for i, registered_button in enumerate(self.button_list): 
            if registered_button.text == button.text: 
                self.button_list.pop(i)

__buildins__ = BuiltIns() 


class Button: 
    OnHover = 1
    OnClick = 2 
    def __init__(self, org, width, height, text, mouseHandler, onClick=None, args=None, color=(125,125,125), 
                 border=1, border_color=(255,255,255), zIndex=0):
        global __buildins__ 
        self.pt1 = tuple(org) 
        self.pt2 = (self.pt1[0]+width, self.pt1[1]+height) 
        self.text = text 
        self.status = 0 
        self.onClickFunc = onClick
        self.args = args 
        self.color = color 
        self.border = border 
        self.border_color = border_color 
        self.zIndex = zIndex 
        self.mouseHandler = mouseHandler 
        __buildins__.register_button(self) 
        
    def update_status(self): 
        global __buildins__ 
        x = self.mouseHandler.x 
        y = self.mouseHandler.y
        click = self.mouseHandler.click
        if x > self.pt1[0] and x < self.pt2[0] and \
            y > self.pt1[1] and y < self.pt2[1]: 
            if __buildins__.mouse_event_button(self, x, y, click): 
                if not click: 
                    self.status = self.OnHover 
                else: 
                    if not self.status == self.OnClick:  # Make sure call once only. 
                        self.mouseHandler.click = False 
                        self.status = self.OnClick
                        if self.onClickFunc is not None: 
                            if self.args is not None: self.onClickFunc(self.args)
                            else: self.onClickFunc() 
                    self.onFocus = True  
                return self.onFocus   
            else: return not click 
        else: 
            self.status = 0
            if click: self.onFocus = False 
            try: return self.onFocus 
            except: self.onFocus = False; return False 

    def construct_button(self, img): 
        if self.status == self.OnHover: color = (50,50,50) 
        elif self.status == self.OnClick: color = (0,100,200)
        else: color = self.color 
        cv2.rectangle(img, self.pt1, self.pt2, color, -1) 
        if self.border > 0: 
            cv2.rectangle(img, self.pt1, self.pt2, self.border_color, self.border) 
        cv2.putText(img, self.text, (self.pt1[0]+5, int((self.pt2[1]-self.pt1[1])*0.65)+self.pt1[1]), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1) 
    
    def destroy(self): 
        global __buildins__ 
        __buildins__.unregister_button(self) 


class MenuTree: 
    def __init__(self, width, mouseHandler, color=(0,0,0)): 
        self.tree = dict() 
        self.color = color
        self._x = 10 
        self.parentHeight = 30
        self.childWidth = 200
        self.childHeight = 50 
        self.winWidth = width 
        self.mouseHandler = mouseHandler 

    def _func(self, args={}): 
        if args["args"] is None: args["func"]() 
        else: args["func"](args["args"]) 
        self.toggle_parent(args["parentName"]) 

    def toggle_parent(self, parentName): 
        self.tree[parentName]["hidden"] = not self.tree[parentName]["hidden"] 
        if self.tree[parentName]["hidden"] is False: 
            for parent in self.tree: 
                if not parent == parentName: self.tree[parent]["hidden"] = True 

    def addParent(self, parentName): 
        x = self._x 
        w = len(parentName) * 10 + 10 
        self._x += w 
        self.tree[parentName] = {"parent": Button((x,0), w, self.parentHeight, parentName, 
                                 self.mouseHandler, onClick=self.toggle_parent, args=parentName, 
                                 color=self.color, border=0), 
                           "child": list(), 
                           "hidden": True } 
    
    def addChild(self, parentName, childName, onClick=None, args=None): 
        x = self.tree[parentName]["parent"].pt1[0] 
        y = len(self.tree[parentName]["child"]) * self.childHeight + self.parentHeight 
        self.tree[parentName]["child"].append(Button((x,y), self.childWidth, self.childHeight, childName, 
                                        self.mouseHandler, onClick=self._func, 
                                        args={"parentName": parentName, "func": onClick, "args": args}, 
                                        color=self.color, border=1, border_color=(100,100,100), zIndex=9999)) 

    def update_status(self): 
        x = self.mouseHandler.x 
        y = self.mouseHandler.y
        click = self.mouseHandler.click
        for parentName in self.tree: 
            parent_onFocus = self.tree[parentName]["parent"].update_status()
            if self.tree[parentName]["hidden"] is False: 
                for button in self.tree[parentName]["child"]: 
                    button.zIndex = 9999
                    onFocus = button.update_status() 
                    if onFocus: parent_onFocus = onFocus 
                if not parent_onFocus: self.tree[parentName]["hidden"] = True 
            else: 
                for button in self.tree[parentName]["child"]: 
                    button.zIndex = -1 
    
    def construct_menu_tree(self, mat): 
        cv2.rectangle(mat, (0,0), (self.winWidth, self.parentHeight), self.color, -1)
        for parentName in self.tree: 
            self.tree[parentName]["parent"].construct_button(mat) 
            if self.tree[parentName]["hidden"] is False: 
                for button in self.tree[parentName]["child"]: 
                    button.construct_button(mat) 
        cv2.line(mat, (0,self.parentHeight), (self.winWidth, self.parentHeight), (100,100,100), 1) 


class ProgressBar: 
    def __init__(self, org, width, height, color=(0,204,0)):
        self.pt1 = tuple(org) 
        self.pt2 = (org[0]+width, org[1]+height) 
        self.color = color 
        self.progress = 0.
        self.starttime = time() 
        self._w = 0 
        self._x = 0 

    def construct_progressbar(self, mat): 
        cv2.rectangle(mat, (self.pt1[0], self.pt1[1]+14), self.pt2, (100,100,100), 1) 
        if self.progress > 0.: 
            prog_width = max(int(round((self.pt2[0]-2 - self.pt1[0]-2) * self.progress)), 1)   
            cv2.rectangle(mat, (self.pt1[0]+2, self.pt1[1]+16), 
                        (self.pt1[0]+2+prog_width, self.pt2[1]-2), self.color, -1) 
            duration = time() - self.starttime 
            eta = (1.-self.progress) * duration / self.progress 
            s = "%.2f%% - ETA %s " % (self.progress*100, self.fmt_time(eta)) 
        else: 
            if self._w < 50: self._w += 2 
            else: self._x += 2
            if self.pt1[0]+2+self._x + self._w >= self.pt2[0]-2: 
                self._w -= self.pt1[0]+2+self._x + self._w - self.pt2[0]+4 
                self._x += 2
            if self.pt1[0]+2+self._x >= self.pt2[0] - 2: self._x = 0; self._w = 0
            cv2.rectangle(mat, (self.pt1[0]+2+self._x, self.pt1[1]+16), 
                        (self.pt1[0]+2+self._x+self._w, self.pt2[1]-2), self.color, -1) 
            s = "Please wait."
        cv2.putText(mat, s, (self.pt1[0], self.pt1[1]-3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)

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

    def update_progressbar(self, progress): 
        self.progress = progress 


class Textbox: 
    def __init__(self, org, width, height, keyHandler, mouseHandler, placeholder=None, default_value=""):
        self.pt1 = tuple(org) 
        self.pt2 = (org[0]+width, org[1]+height) 
        self.placeholder = placeholder
        self.value = default_value 
        self.onFocus = False 
        self.keyHandler = keyHandler 
        self.mouseHandler = mouseHandler 
        self.button = Button(org, width, height, placeholder, self.mouseHandler, onClick=None, zIndex=9999) 

    def update_status(self): 
        self.onFocus = self.button.update_status() 

    def construct_textbox(self, mat): 
        cv2.rectangle(mat, self.pt1, self.pt2, (50,50,50), -1) 
        cv2.rectangle(mat, self.pt1, self.pt2, (200,200,200), 1) 
        if self.onFocus: # Input mode. 
            cv2.putText(mat, self.value + "|", (self.pt1[0]+5, int((self.pt2[1]-self.pt1[1])*0.65)+self.pt1[1]), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1) 
        else: # Placeholder mode. 
            cv2.putText(mat, self.placeholder, (self.pt1[0]+5, int((self.pt2[1]-self.pt1[1])*0.65)+self.pt1[1]), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100,100,100), 1) 

    def _enter_input_mode(self): 
        global endFlag 
        self.keyHandler.set_inputting(True) 
        while self.onFocus and not endFlag: self.value = self.keyHandler.get_input() 
        self.keyHandler.set_inputting(False) 

    def _input_from_clipboard(self): 
        self.keyHandler.string_value = Tk().clipboard_get()
        cv2.waitKey(40) 
        self.onFocus = True 
        self.button.onFocus = True 


class Notifier: 
    def __init__(self):
        self.notifiers = list() 

    def new_notifier(self, org, width, height, title, text): 
        pt1 = tuple(org) 
        pt2 = (pt1[0]+width, pt1[1]+height) 
        title = title
        text = text 
        self.notifiers.append({"pt1": pt1, "pt2": pt2, "title": title, "text": text, "color": (0,0,0)})
    
    def construct_notifiers(self, mat): 
        for notifier in self.notifiers: 
            cv2.rectangle(mat, notifier["pt1"], notifier["pt2"], notifier["color"], -1) 
            cv2.rectangle(mat, notifier["pt1"], notifier["pt2"], (255,255,255), 1) 
            cv2.putText(mat, notifier["title"], (notifier["pt1"][0]+ 10, notifier["pt1"][1] + 30), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.75, (255,255,255), 1)
            cv2.putText(mat, notifier["text"], (notifier["pt1"][0]+ 10, notifier["pt1"][1] + 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
            cv2.putText(mat, "Click on this balloon to close.", (notifier["pt1"][0]+ 10, notifier["pt2"][1] - 12), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200,200,200), 1)
    
    def update_status(self, x, y, click=False):  
        for i, notifier in enumerate(self.notifiers): 
            if x > notifier["pt1"][0] and x < notifier["pt2"][0] and \
                y > notifier["pt1"][1] and y < notifier["pt2"][1]: 
                if click: self.notifiers.pop(i); break 
                else: self.notifiers[i]["color"] = (0,100,200) 
            else: self.notifiers[i]["color"] = (0,0,0) 


class Dialog: 
    INFO = 0 
    # YESNO = 1 
    PROGRESS = 2 
    INPUT = 3 

    def __init__(self, org, name, mouseHandler, dialog_type=INFO, textbox_default_value=""): 
        global keyHandler 
        width = 350 if dialog_type == self.INPUT else 250 
        self.name = name 
        self.pt1 = (org[0]-width, org[1]-75) 
        self.pt2 = (org[0]+width, org[1]+75) 
        self.color = (10,10,10)
        self.mouseHandler = mouseHandler 
        self.destroyFlag = False 
        self.dialog_type = dialog_type 
        if self.dialog_type == self.PROGRESS: 
            self.progressbar = ProgressBar((self.pt1[0]+10, org[0]), width*2-20, 30) 
        if self.dialog_type == self.INPUT: 
            self.textbox = Textbox((self.pt1[0]+10, org[0]), width*2-20, 30, keyHandler, self.mouseHandler, name) 
    
    def construct_dialog(self, mat): 
        cv2.rectangle(mat, self.pt1, self.pt2, self.color, -1) 
        cv2.rectangle(mat, self.pt1, self.pt2, (100,100,100), 1) 
        if self.dialog_type == self.INFO: self._construct_info_dialog(mat) 
        elif self.dialog_type == self.PROGRESS: self._construct_progress_dialog(mat) 
        elif self.dialog_type == self.INPUT: self._construct_input_dialog(mat)

    def _construct_std_dialog(self, mat, df_name): 
        title = self.name 
        if self.dialog_type in [self.INFO, self.INPUT]: title = df_name 
        cv2.putText(mat, title, (self.pt1[0]+ 10, self.pt1[1] + 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 1)
        if self.dialog_type == self.INFO: 
            cv2.putText(mat, self.name, (self.pt1[0]+ 10, self.pt1[1] + 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100,100,100), 1) 

    def _construct_info_dialog(self, mat): 
        self._construct_std_dialog(mat, "Info")
        try: 
            for button in self.buttons: button.construct_button(mat)  
        except: 
            OKbutton = Button((self.pt2[0]-85, self.pt2[1]-40), 75, 30, "OK", 
                               self.mouseHandler, onClick=self.destroy_dialog) 
            self.buttons = [OKbutton] 
            for button in self.buttons: button.construct_button(mat) 
        
    def _construct_input_dialog(self, mat): 
        self._construct_std_dialog(mat, "Input") 
        self.textbox.construct_textbox(mat) 
        try: 
            for button in self.buttons: button.construct_button(mat)  
        except: 
            OKbutton = Button((self.pt2[0]-85, self.pt2[1]-40), 75, 30, "OK", 
                               self.mouseHandler, onClick=self.destroy_dialog) 
            pastebutton = Button((self.pt2[0]-190, self.pt2[1]-40), 100, 30, "Paste", 
                               self.mouseHandler, onClick=self.textbox._input_from_clipboard) 
            self.buttons = [OKbutton, pastebutton] 
            for button in self.buttons: button.construct_button(mat) 

    def _construct_progress_dialog(self, mat): 
        self._construct_std_dialog(mat, "Progress") 
        self.progressbar.construct_progressbar(mat)
        if self.progressbar.progress >= 1.: 
            self.destroy_dialog()

    def destroy_dialog(self): 
        try:
            for button in self.buttons: 
                button.destroy() 
        except: pass 
        try: self.textbox.onFocus = False 
        except: pass 
        self.destroyFlag = True 
    
    def update_status(self):  
        try: self.textbox.update_status()
        except: pass 
        try: 
            for button in self.buttons: button.update_status()
        except: pass 


class MouseHandler: 
    def __init__(self):
        self.x = 0; self.y = 0
        self.click = False 

    def onMouseHandle(self, event, x, y, flags, param): 
        self.x = x; self.y = y 
        if event == cv2.EVENT_LBUTTONDOWN: self.click = True 
        elif event == cv2.EVENT_LBUTTONUP: self.click = False 


class KeyHandler: 
    def __init__(self):
        self.keys = dict() 
        self.args = dict() 
        self.inputting = False 
        self.string_value = ""
    
    def add_action(self, key, function, args=None): 
        self.keys[key] = function 
        self.args[key] = args

    def handle_key(self, timeout): 
        key = cv2.waitKey(timeout) 
        if not self.inputting: 
            for k in self.keys: 
                if key == k: 
                    if self.args[k] is None: self.keys[k]() 
                    else: self.keys[k](self.args[k])
        else:
            if key >= 32 and key <= 126: 
                self.string_value += chr(key) 
            elif key == 8: 
                self.string_value = self.string_value[:-1] 

    def set_inputting(self, value): 
        self.inputting = value
        if not value: self.string_value = ""

    def get_input(self): 
        return self.string_value 


class ImageHandler: 
    def __init__(self): 
        self.image_paths = None 
        self.iter = 0 
        self.deleted = 0 
        self.img = None 
        self._orig_img = None 

    def load_from_directory(self, dir_path, interface=None): 
        self.interface = interface 
        self.path = pathlib.Path(dir_path) 
        if not os.path.isdir(dir_path): # Video mode. 
            self._video_mode = True 
            self.cap = cv2.VideoCapture(dir_path) 
            length = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) 
            self.image_paths = [f"{dir_path}-{i}" for i in range(length)] 
        else: # Image directory mode. 
            self._video_mode = False 
            self.image_paths = list(self.path.glob("*.jpg"))  
            for path in list(self.path.glob("*.png")): self.image_paths.append(path) 
            print(f"{len(self.image_paths)} images found.") 
            # Restore iter from file. 
            if os.path.exists(os.path.join(dir_path, "_iter.txt")): 
                with open(os.path.join(dir_path, "_iter.txt"), "r") as f: 
                    self.iter = int(f.read()) - 1
                    if self.iter >= len(self.image_paths): 
                        self.iter = 0 
                        self._check_square(interface) 

    def _check_square(self, interface=None): 
        print("Final checking...") 
        remove_list = list() 
        for i, path in tqdm(enumerate(self.image_paths)): 
            if interface is not None: 
                interface.dialog.progressbar.update_progressbar(i/(len(self.image_paths)-1))
            try: 
                img = cv2.imread(str(path)) 
                width = img.shape[1]; height = img.shape[0] 
                if abs(width / height - 1) < 0.1: 
                    remove_list.append(i)
                    if width != height: 
                        s = max(width, height) 
                        cv2.imwrite(str(path), cv2.resize(img, (s,s))) 
            except Exception as e: 
                print(e, str(path)) 
                remove_list.append(i)
        remove_list = sorted(remove_list, reverse=True) 
        for i in remove_list: self.image_paths.pop(i) 
        print(f"After final check: {len(self.image_paths)} images.") 

    def get_path(self): 
        return str(self.image_paths[self.iter-1]) 

    def get_formatted_info(self): 
        return "[{}/{}] {}".format(self.iter, len(self.image_paths), self.get_path()) 

    def is_video_mode(self): 
        try: return self._video_mode
        except: return False 

    def get_orig_img(self): 
        return self._orig_img  

    def get_frame(self, i): 
        backup_i = self.cap.get(cv2.CAP_PROP_POS_FRAMES) 
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, i) 
        _, img = self.cap.read() 
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, backup_i) 
        return img 

    def next(self, save_checkpoint=False): 
        global endFlag
        if self.iter >= len(self.image_paths): 
            print("No more image to process.") 
            return None 
        # Read image data. 
        if not self._video_mode: 
            self.img = cv2.imread(str(self.image_paths[self.iter])) 
        else: 
            _, self.img = self.cap.read() 
        # Update iter count.  
        self.iter += 1 
        # Resize if oversized. 
        self._orig_img = self.img.copy() 
        if self.img.shape[0] >= self.interface._winsize or self.img.shape[1] >= self.interface._winsize: 
            ratio = self.interface._winsize / max(self.img.shape) 
            self.img = cv2.resize(self.img, (int(self.img.shape[1]*ratio), int(self.img.shape[0]*ratio))) 
        # Save checkpoint if needed. 
        if save_checkpoint and not self._video_mode: 
            try: os.remove(os.path.join(str(self.path), "_iter.txt")) 
            except: pass 
            with open(os.path.join(str(self.path), "_iter.txt"), "w") as f: 
                f.write(str(self.iter-self.deleted)) 
        return self.img 

    def delete(self): 
        try: 
            os.remove(self.image_paths[self.iter - 1]) 
            self.deleted += 1 
        except Exception as e: print(e) 
    
    def reset_iter(self): 
        if not self._video_mode: 
            try: os.remove(os.path.join(str(self.path), "_iter.txt")) 
            except: pass 
            with open(os.path.join(str(self.path), "_iter.txt"), "w") as f: 
                f.write(str(0)) 
        else: self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) 
        self.iter = 0 


class Interface: 
    def __init__(self, refresh_rate=80): 
        self.refresh_rate = refresh_rate 
        self._winsize = 900 
        cv2.namedWindow("Crop Image", cv2.WINDOW_NORMAL) 
        cv2.resizeWindow("Crop Image", self._winsize, self._winsize) 
        self.dialog = None
        self.image_handler = ImageHandler() 
        self.crop_tool = Crop_Tool(self, self.image_handler) 
        self.pluginManager = Plugins(self, self.image_handler, self.crop_tool) 
        self.mouseHandler = MouseHandler()
        cv2.setMouseCallback("Crop Image", self.mouseHandler.onMouseHandle) 
        self.menuTree = MenuTree(self._winsize, self.mouseHandler) 
        self.menuTree.addParent("File") 
        self.menuTree.addChild("File", "Load image folder", onClick=self._load_img_thr) 
        self.menuTree.addChild("File", "Load video", onClick=self._load_img_thr, args=True) 
        self.menuTree.addChild("File", "Exit", onClick=self.close) 
        self.menuTree.addParent("Edit") 
        self.menuTree.addChild("Edit", "Reset checkpoint", onClick=self.reset_checkpoint) 
        self.menuTree.addParent("Plugins") 
        self.menuTree.addChild("Plugins", "animeFace", onClick=self._load_plugin_thr, args=Plugins.ANIMEFACE)
        self.buttons = list() 
        self.buttons.append(Button(( 10,40), 70, 30, "Reset", self.mouseHandler, onClick=self.reset)) 
        self.buttons.append(Button((90,40), 80, 30, "Delete", self.mouseHandler, onClick=self.delete)) 
        self.buttons.append(Button((180,40), 90, 30, "Zoom In", self.mouseHandler, onClick=self.zoom_in)) 
        self.buttons.append(Button((280,40), 100, 30, "Zoom Out", self.mouseHandler, onClick=self.zoom_out)) 
        self.buttons.append(Button((390,40), 50, 30, "Next", self.mouseHandler, onClick=self.next)) 
        self.buttons.append(Button((450,40), 120, 30, "Crop & Next", self.mouseHandler, onClick=self.next, args=True)) 
        self.notifier = Notifier() 
        self.notifier.new_notifier((590,10), 300, 100, "Notification", "Press ESC or File > Exit to exit.")
        self.dir_path = None 

    def _load_plugin_thr(self, pluginName): 
        loadThread = Thread("loadThread", self._load_plugin, args=pluginName)
        loadThread.start() 

    def _load_plugin(self, pluginName): 
        self.dialog = Dialog((int(self._winsize/2), int(self._winsize/2)), "Loading plugin", 
                             self.mouseHandler, Dialog.PROGRESS) 
        status = self.pluginManager.importPlugin(pluginName) 
        self.dialog.destroyFlag = True 
        self.dialog = None 
        msg = "Plugin import success." if type(status) is not str else status 
        self.dialog = Dialog((int(self._winsize/2), int(self._winsize/2)), msg, self.mouseHandler) 

    def _load_img_thr(self, video=False): 
        loadThread = Thread("loadThread", self._load_images_dialog, video) 
        loadThread.start() 

    def _load_images_dialog(self, video): 
        global endFlag 
        self.dialog = Dialog((int(self._winsize/2), int(self._winsize/2)), "Image directory path", 
                             self.mouseHandler, Dialog.INPUT) 
        while not endFlag: 
            if self.dialog.textbox.onFocus: self.dialog.textbox._enter_input_mode() 
            try: 
                if self.dialog.destroyFlag: dir_path = self.dialog.textbox.value; self.dialog = None; break 
            except: pass 
        print(dir_path)
        self.load_images(dir_path)  
        if video: self._put_video_navigate() 
        
    def load_images(self, dir_path): 
        self.dir_path = dir_path 
        self.dialog = Dialog((int(self._winsize/2), int(self._winsize/2)), "Final checking", 
                             self.mouseHandler, Dialog.PROGRESS) 
        self.factor = 1
        self.image_handler.load_from_directory(dir_path, self) 
        try: self.dialog = None
        except: pass
        self.img = self.image_handler.next()
        if self._image_list_end_handler():  
            self.ori_img = self.img 
            self.crop_tool.new_crop(self.img, self.image_handler.get_path()) 
        
    def _put_video_navigate(self): 
        self.buttons.append(Button((self._winsize - 80, self._winsize - 40), 30, 30, "|>", 
                            self.mouseHandler, onClick=self._play_video)) 
        self.buttons.append(Button((self._winsize - 40, self._winsize - 40), 30, 30, "| |", 
                            self.mouseHandler, onClick=self._stop_video)) 

    def _play_video(self): 
        try: t = self.playVid
        except: t = False 
        if not t:  
            videoThread = Thread("videoThread", self._play_video_thr) 
            videoThread.start() 
    
    def _stop_video(self): self.playVid = False 
    
    def _play_video_thr(self, nothing): 
        self.playVid = True 
        while not endFlag and self.playVid: 
            self.next() 
            cv2.waitKey(30)

    def reset_checkpoint(self): 
        try: 
            if self.image_handler.image_paths is not None: 
                self.image_handler.reset_iter() 
                self.next() 
            else: self._info_dialog("No directory opened yet.")
        except Exception as e: print(e)

    def _image_list_end_handler(self): 
        if self.img is None: 
            self.dialog = Dialog((int(self._winsize/2), int(self._winsize/2)), "No more image to process.", 
                                self.mouseHandler) 
            deathThread = Thread("deathThread", self._death_thread)
            deathThread.start() 
            return False 
        else: return True 

    def _death_thread(self, nothing): 
        global endFlag 
        while not endFlag: 
            try: 
                if self.dialog.destroyFlag: endFlag = True; self.close(); exit(0); return False  
            except: pass 

    def _progress_dialog(self, text): 
        self.dialog = Dialog((int(self._winsize/2), int(self._winsize/2)), text, 
                             self.mouseHandler, Dialog.PROGRESS) 
    
    def _info_dialog(self, text): 
        self.dialog = Dialog((int(self._winsize/2), int(self._winsize/2)), text, 
                             self.mouseHandler) 

    def _win_img(self): 
        def _format_coor(): 
            s = str((self.mouseHandler.x, self.mouseHandler.y)) 
            s = " " * (10 - len(s)) + s 
            return s

        # Show curent frame. 
        mat = np.ones((self._winsize,self._winsize,3), dtype=np.uint8) * 27 
        try:  
            pt1 = (int((self._winsize-self.img.shape[1])/2), int((self._winsize-self.img.shape[0])/2)) 
            pt2 = (pt1[0] + self.img.shape[1], pt1[1] + self.img.shape[0])
            mat[pt1[1]:pt2[1], pt1[0]:pt2[0]] = self.img 
        except: pass  

        # Show crop box. 
        self.crop_tool.show_crop_box(mat, pt1, self.mouseHandler.x, self.mouseHandler.y, self.mouseHandler.click)

        # Show buttons. 
        try: 
            for button in self.buttons: 
                button.update_status()
                button.construct_button(mat) 
        except: pass 

        # Show cursor coordinate. 
        try: 
            cv2.putText(mat, _format_coor(), (self._winsize-90, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100,100,100), 1) 
            cv2.putText(mat, self.image_handler.get_formatted_info(), (3, self._winsize-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100,100,100), 1) 
        except: pass 

        # Show menuTree. 
        try: 
            self.menuTree.update_status() 
            self.menuTree.construct_menu_tree(mat) 
        except: pass 

        # Update crop box. 
        try: self.crop_tool.action(mat, pt1, self.mouseHandler.x, self.mouseHandler.y, self.mouseHandler.click) 
        except: pass 

        # Show notifier. 
        try: 
            self.notifier.update_status(self.mouseHandler.x, self.mouseHandler.y, self.mouseHandler.click)
            self.notifier.construct_notifiers(mat)
        except: pass 

        # Show dialog. 
        try: 
            self.dialog.update_status() 
            self.dialog.construct_dialog(mat) 
            try: 
                if self.dialog.destroyFlag and not self.dialog.dialog_type == Dialog.INPUT: self.dialog = None 
            except: pass
        except: pass 
        return mat 

    def _zoom(self): 
        new_size = (int(self.ori_img.shape[1]*self.factor), int(self.ori_img.shape[0]*self.factor))
        if new_size[0] <= self._winsize and new_size[1] <= self._winsize: 
            self.img = cv2.resize(self.ori_img, new_size) 
            self.crop_tool.new_crop(self.img, self.image_handler.get_path()) 
        cv2.waitKey(50)  # Wait mouseup. 

    def zoom_in(self): 
        self.factor += 0.25 
        self._zoom()
    
    def zoom_out(self): 
        self.factor -= 0.25
        self._zoom() 

    def reset(self): 
        self.factor = 1 
        self._zoom() 
        self.crop_tool._square_crop(self.img) 

    def next(self, save=False): 
        if save: self.crop_tool.save_crop(self.img, self.image_handler.get_path())
        self.img = self.image_handler.next(save_checkpoint=True) 
        if self._image_list_end_handler():  
            self.ori_img = self.img 
            self._zoom() 
            self.crop_tool.new_crop(self.img, self.image_handler.get_path()) 

    def delete(self): 
        self.image_handler.delete() 
        self.img = self.image_handler.next() 
        if self._image_list_end_handler(): 
            self.ori_img = self.img 
            self._zoom() 
            self.crop_tool.new_crop(self.img, self.image_handler.get_path()) 

    def refresh(self, nothing): 
        global endFlag
        while not endFlag: 
            cv2.imshow("Crop Image", self._win_img()) 

    def close(self): 
        global endFlag 
        print("Closing.")
        endFlag = True 
        self.pluginManager.close() 
        cv2.destroyAllWindows() 
        cv2.waitKey(1000)
        cv2.destroyAllWindows() 


class Crop_Tool: 
    def __init__(self, interface, imageHandler):
        self.prev_bnd = None 
        self.bnd = None 
        self.bndboxes = dict() 
        self.points = None 
        self.status = -1 
        self.width = None
        self.height = None 
        self.path = None 
        self.interface = interface 
        self.imageHandler = imageHandler 
        self.padding_left = self.padding_right = 0 
        self.padding_top = self.padding_bottom = 0 

    def feed_bndboxes(self, bndboxes): 
        '''
        Feed in bndbox data. 

        Arguments: 
        ------------
            bndboxes: dict 
                Dictionary contains bndbox data corresponds to each image path. 
                See format below. 
        ------------
        Please make sure format as following: \n
        {"IMAGE_PATH_1": {"score": "CONFIDENCE (OPTIONAL)", "bbox": [X1, Y1, X2, Y2] } } \n
        X1...Y2 should be in decimal ratio by image shape. E.g.: ∈ [0., 1.]

        '''
        for i in bndboxes: 
            if i not in self.bndboxes: self.bndboxes[i] = bndboxes[i] 
        print("Fed", len(bndboxes), "bndboxes.") 
        if self.path in self.bndboxes: 
            self._apply_bndbox()
        else: print("Not in data.", self.path, [i for i in self.bndboxes]) 

    def _bnd_8_points(self): 
        self.points = list() 
        self.points.append((self.bnd[0], self.bnd[1]))  # Left top. 
        self.points.append((int((self.bnd[0]+self.bnd[2])/2), self.bnd[1]))  # Top. 
        self.points.append((self.bnd[2], self.bnd[1]))  # Right top. 
        self.points.append((self.bnd[2], int((self.bnd[1]+self.bnd[3])/2)))  # Right. 
        self.points.append((self.bnd[2], self.bnd[3]))  # Right bottom. 
        self.points.append((int((self.bnd[0]+self.bnd[2])/2), self.bnd[3]))  # Bottom. 
        self.points.append((self.bnd[0], self.bnd[3]))  # Left bottom. 
        self.points.append((self.bnd[0], int((self.bnd[1]+self.bnd[3])/2)))  # Left. 

    def _draw_bnd(self, mat, padding): 
        try: 
            color = (0,153,255)
            if self.path in self.bndboxes: 
                color = (255,153,0)
                self._draw_fed_bndboxes(mat, padding) 
            cv2.rectangle(mat, (padding[0]+self.bnd[0], padding[1]+self.bnd[1]), (padding[0]+self.bnd[2], 
                        padding[1]+self.bnd[3]), color, 2) 
        except Exception as e: print(e)
    
    def _draw_fed_bndboxes(self, mat, padding): 
        for bnd in self.bndboxes[self.path]: 
            bnd = bnd["bbox"] 
            cv2.rectangle(mat, (padding[0]+int(bnd[0]*self.width), padding[1]+int(bnd[1]*self.height)), 
                          (padding[0]+int(bnd[2]*self.width), padding[1]+int(bnd[3]*self.height)), 
                          (150,150,150), 2) 

    def _draw_8_points(self, mat, padding, x, y, click): 
        self._bnd_8_points() 
        match = [math.sqrt(math.pow(x-pt[0]-padding[0], 2) + math.pow(y-pt[1]-padding[1], 2)) < 7 
                 for pt in self.points]
        for i, pt in enumerate(self.points): 
            if match[i]: 
                if click: fgColor = (150,150,150)
                else: fgColor = (200,200,200) 
            else: fgColor = (255,255,255) 
            color = (255,153,0) if self.path in self.bndboxes else (0,153,255) 
            cv2.circle(mat, (padding[0]+pt[0], padding[1]+pt[1]), 7, fgColor, -1) 
            cv2.circle(mat, (padding[0]+pt[0], padding[1]+pt[1]), 7, color, 2) 

    def _bnd_padding(self): 
        box_w = self.bndboxes[self.path][0]["bbox"][2] - self.bndboxes[self.path][0]["bbox"][0] 
        box_h = self.bndboxes[self.path][0]["bbox"][3] - self.bndboxes[self.path][0]["bbox"][1] 
        self.padding_left = (self.bnd[0] / self.width - self.bndboxes[self.path][0]["bbox"][0]) / box_w
        self.padding_right = (self.bnd[2] / self.width - self.bndboxes[self.path][0]["bbox"][2]) / box_w 
        self.padding_top = (self.bnd[1] / self.height - self.bndboxes[self.path][0]["bbox"][1]) / box_h 
        self.padding_bottom = (self.bnd[3] / self.height - self.bndboxes[self.path][0]["bbox"][3]) / box_h 

    def _limit_action(self): 
        if not self.status == 8: 
            if self.bnd[0] < 0: self.bnd[0] = 0 
            if self.bnd[1] < 0: self.bnd[1] = 0 
            if self.bnd[2] < 0: self.bnd[2] = 0 
            if self.bnd[3] < 0: self.bnd[3] = 0 
            if self.bnd[0] > self.width: self.bnd[0] = self.width 
            if self.bnd[1] > self.height: self.bnd[1] = self.height 
            if self.bnd[2] > self.width: self.bnd[2] = self.width 
            if self.bnd[3] > self.height: self.bnd[3] = self.height 
            if self.status % 2 == 0: # Corners. 
                w = self.bnd[2] - self.bnd[0] 
                h = self.bnd[3] - self.bnd[1] 
                s = int(min(w, h))  
                self.bnd[3] = self.bnd[1] + s
                self.bnd[2] = self.bnd[0] + s 
            if self.status == 9: 
                w = self.bnd[2] - self.bnd[0] 
                h = self.bnd[3] - self.bnd[1] 
                cx = int((self.bnd[2] + self.bnd[0]) / 2)
                cy = int((self.bnd[3] + self.bnd[1]) / 2) 
                s = int(min(w, h) / 2)  
                self.bnd[0] = cx - s; self.bnd[1] = cy - s
                self.bnd[2] = cx + s; self.bnd[3] = cy + s 
        elif self.status >= 0: 
            dx = 0; dy = 0 
            if self.bnd[0] < 0: dx = abs(self.bnd[0]) 
            if self.bnd[2] > self.width: dx = self.width - self.bnd[2] 
            if self.bnd[1] < 0: dy = abs(self.bnd[1]) 
            if self.bnd[3] > self.height: dy = self.height - self.bnd[3] 
            self.bnd[0] += dx; self.bnd[2] += dx  
            self.bnd[1] += dy; self.bnd[3] += dy  

    def _mouseup(self): 
        if self.bnd[0] > self.bnd[2]: temp = self.bnd[0]; self.bnd[0] = self.bnd[2]; self.bnd[2] = temp 
        if self.bnd[1] > self.bnd[3]: temp = self.bnd[1]; self.bnd[1] = self.bnd[3]; self.bnd[3] = temp 
        self.status = -1 

    def action(self, mat, padding, x, y, click=False): 
        if click: 
            if self.status == -1: 
                for i, pt in enumerate(self.points): 
                    if math.sqrt(math.pow(x-pt[0]-padding[0], 2) + math.pow(y-pt[1]-padding[1], 2)) < 7: 
                        self.status = i; break 
                if self.status == -1: 
                    if x-padding[0] >= self.bnd[0] and x-padding[0] <= self.bnd[2] and \
                       y-padding[1] >= self.bnd[1] and y-padding[1] <= self.bnd[3]: 
                        self.status = 8 
                        self._temp_x = x 
                        self._temp_y = y 
            if self.status == 0 or self.status == 4: # Left top. Right bottom. 
                s = max(x, y)
                if self.status == 0: self.bnd[0] = s-padding[0]; self.bnd[1] = s-padding[1] 
                else: self.bnd[2] = s-padding[0]; self.bnd[3] = s-padding[1] 
            elif self.status == 2 or self.status == 6: # Right top. Left bottom. 
                s = max(mat.shape[1]-x, y) 
                if self.status == 2: self.bnd[1] = s-padding[1]; self.bnd[2] = mat.shape[1]-s-padding[0]
                else: self.bnd[0] = mat.shape[1]-s-padding[0]; self.bnd[3] = s-padding[1] 
            elif self.status == 1 or self.status == 5: # Top. Bottom. 
                if self.status == 1: self.bnd[1] = y-padding[1] 
                else: self.bnd[3] = y-padding[1]
            elif self.status == 3 or self.status == 7: # Right. Left. 
                if self.status == 3: self.bnd[2] = x-padding[0] 
                else: self.bnd[0] = x-padding[0]
            elif self.status == 8: # Box. 
                dx = x - self._temp_x; dy = y - self._temp_y 
                self.bnd[0] += dx; self.bnd[2] += dx 
                self.bnd[1] += dy; self.bnd[3] += dy
                self._temp_x = x; self._temp_y = y 
            self._limit_action()
            if self.path is not None and self.status >= 0 and self.status <= 8: 
                if self.path in self.bndboxes: self._bnd_padding() 
        if not click: self._mouseup()

    def show_crop_box(self, mat, padding, x, y, click=False): 
        self._draw_bnd(mat, padding)  
        self._draw_8_points(mat, padding, x, y, click) 

    def _square_crop(self, img): 
        size = min(img.shape[1], img.shape[0]) 
        self.bnd = [0,0,size,size] 
    
    def _reuse_prev_bnd(self, img): 
        self.prev_bnd = self.bnd
        self.bnd[0] = int(self.prev_bnd[0] / self.width * img.shape[1])
        self.bnd[1] = int(self.prev_bnd[1] / self.height * img.shape[0])
        self.bnd[2] = int(self.prev_bnd[2] / self.width * img.shape[1])
        self.bnd[3] = int(self.prev_bnd[3] / self.height * img.shape[0]) 

    def _apply_bndbox(self, idx=0): 
        bnd = self.bndboxes[self.path][idx]["bbox"] 
        box_w = bnd[2] - bnd[0]; box_h = bnd[3] - bnd[1] 
        self.bnd[0] = int((bnd[0] + self.padding_left * box_w) * self.width)
        self.bnd[1] = int((bnd[1] + self.padding_top * box_h) * self.height)
        self.bnd[2] = int((bnd[2] + self.padding_right * box_w) * self.width) 
        self.bnd[3] = int((bnd[3] + self.padding_bottom * box_h) * self.height) 
        self.status = 9  
        self._limit_action()
        self.status = -1 
    
    def new_crop(self, img, img_path): 
        self.path = img_path 
        if self.path in self.bndboxes: 
            self.width = img.shape[1] 
            self.height = img.shape[0]
            self._apply_bndbox()
        else: 
            if self.bnd is not None: self._reuse_prev_bnd(img)
            else: self._square_crop(img) 
        self.width = img.shape[1] 
        self.height = img.shape[0]

    def save_crop(self, img, img_path): 
        x1 = int(self.bnd[0] / self.width * img.shape[1])
        y1 = int(self.bnd[1] / self.height * img.shape[0])
        x2 = int(self.bnd[2] / self.width * img.shape[1])
        y2 = int(self.bnd[3] / self.height * img.shape[0]) 
        cv2.imwrite(img_path+".jpg", img[min(y1,y2):max(y2,y1), min(x1,x2):max(x2,x1)]) 

    def crop_all_bndboxes(self): 
        processThread = Thread("processThread", self._crop_all_bndboxes_thr) 
        processThread.start() 

    def _crop_all_bndboxes_thr(self, nothing): 
        if len(self.bndboxes) < 1: 
            self.interface._info_dialog("Error: No bndboxes.") 
            return 
        self.interface._progress_dialog("Cropping images.")
        backup_path = self.path 
        backup_width = self.width 
        backup_height = self.height
        for idx, path in enumerate(self.bndboxes): 
            self.path = path 
            self.interface.dialog.progressbar.update_progressbar((idx+1)/(len(self.bndboxes))) 
            output_dir = os.path.join(os.path.split(path)[0], "Output")  
            if not os.path.exists(output_dir): os.makedirs(output_dir) 
            if not self.imageHandler.is_video_mode(): img = cv2.imread(path) 
            else: img = self.imageHandler.get_orig_img() 
            self.width = img.shape[1] 
            self.height = img.shape[0] 
            for i, bnd in enumerate(self.bndboxes[path]): 
                self._apply_bndbox(idx=i) 
                im_path = os.path.join(output_dir, os.path.split(path)[-1].replace(".jpg", "")
                                        .replace(".png", "")+"-"+str(i)+".jpg") 
                cv2.imwrite(im_path, img[self.bnd[1]:self.bnd[3], self.bnd[0]:self.bnd[2]]) 
        self.path = backup_path 
        self.width = backup_width 
        self.height = backup_height 
        self._apply_bndbox() 
        self.interface._info_dialog("Process completed.") 


class Plugins: 
    
    ANIMEFACE = 0 

    def __init__(self, interface, image_handler, crop_tool): 
        self.active = list() 
        self.buttons = list() 
        self.interface = interface 
        self.image_handler = image_handler 
        self.crop_tool = crop_tool 

    def _plugin_func(self, func): 
        processThread = Thread("processThread", self._plugin_func_thr, func) 
        processThread.start() 
    
    def _plugin_func_thr(self, func): 
        value = func["func"](func["args"]) 
        self.interface.crop_tool.feed_bndboxes(value)

    def importPlugin(self, plugin_name): 
        for plugin in self.active: 
            if plugin.name == plugin_name: 
                return "Plugin already imported."
        if plugin_name == self.ANIMEFACE: 
            if self.image_handler.image_paths is None: 
                return "Error: No directory opened yet" 
            sys.path.append("/animeFace") 
            import animeFace.plugin
            plugin = animeFace.plugin.Plugin(self.interface, self.image_handler)  
            plugin.name = self.ANIMEFACE 
            status = plugin.load(os.getcwd()) 
            print("Load plugin:", status) 
            self.active.append(plugin) 
            self.interface.menuTree.addParent("animeFace") 
            for func in plugin.funcs: 
                self.interface.menuTree.addChild("animeFace", func["name"], onClick=self._plugin_func, 
                                                 args=func)
            if status: 
                if len(self.active) == 1: self._add_output_functions()
                return True 
            else: return "Plugin import failed."
        else: return "No such plugin."  
    
    def _add_output_functions(self): 
        self.interface.menuTree.addParent("Output") 
        self.interface.menuTree.addChild("Output", "Crop all bndboxes", onClick=self.crop_tool.crop_all_bndboxes) 
    
    def close(self): 
        for plugin in self.active: 
            plugin.close()  


win = Interface() 
refreshThread = Thread("refreshThread", win.refresh) 
refreshThread.start() 
# loadThread = Thread("loadThread", win.load_images, "F:/Datasets/VNDB_characters_image") # MAL_characters_image") 
# loadThread.start() 
keyHandler = KeyHandler() 
keyHandler.add_action(27, win.close) 
keyHandler.add_action(13, win.next, True) 
keyHandler.add_action(46, win.zoom_in) 
keyHandler.add_action(44, win.zoom_out) 
keyHandler.add_action(120, win.delete)  
keyHandler.add_action(114, win.reset) 
while not endFlag: keyHandler.handle_key(win.refresh_rate)
