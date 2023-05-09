import tkinter as tk
from tkinter import *
from PIL import ImageTk, Image

import time

# Creating a tkinter-based GUI for displaying the output of the WFC algorithm
class WFC_GUI():
    canvas_padding = 0.05
    def __init__(self, w, h, grid_dims = None, launch_fullscreen = False):
        self.root = tk.Tk()
        # self.root.title("Wave Function Collapse")
        #self.screen_dims = (self.root.winfo_screenwidth(), self.root.winfo_screenheight())

        if launch_fullscreen:
            self.root.attributes('-fullscreen', True)

        self.create_canvas(w, h)

        self.grid_dims = grid_dims

        self.border_size = (int(w*self.canvas_padding/2), int(h*self.canvas_padding/2))
        self.border_h = int(h*self.canvas_padding)

        self.img = Image.new("RGB", (w, h), (255, 0, 0))
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)

        self.img_id = self.canvas.create_image(self.border_size[0], self.border_size[1], 
                                               anchor=NW, image=self.tk_img)
        self.advance = False
        self.bind_keys()

    @classmethod
    def fromTileGrid(cls, tile_dims, grid_dims):
        return cls(tile_dims[0] * grid_dims[0], tile_dims[1] * grid_dims[1], grid_dims)
    
    def bind_keys(self):
        
        self.root.bind('e', self.advance)
        self.root.bind("<Escape>", self.close_win)
        self.canvas.pack()
    
    def create_canvas(self, w, h):
        canvas_size = (w + int(w*self.canvas_padding), h + int(h*self.canvas_padding))
        self.canvas = tk.Canvas(self.root, width = canvas_size[0], height = canvas_size[1])
        self.canvas.pack()

    def insert_image(self, new_img, x, y):
        self.img.paste(new_img, (x, y))
        # self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)
        # self.refresh_canvas()

    def refresh_canvas(self):
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)
        self.canvas.itemconfig(self.img_id, image=self.tk_img)
        # self.canvas.delete(self.img_id)
        # self.img_id = self.canvas.create_image(self.border_size[0], self.border_size[1], anchor=NW, image=self.tk_img)
    
    def clear_canvas(self):
        self.img = Image.new("RGB", (self.img.width, self.img.height), (255, 0, 0))
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)
        self.refresh_canvas()

    def close_win(self, e):
        self.advance = True
        # self.root.destroy()

    def advance(self, e):
        print("Key pressed")
        # self.advance = True
        self.root.destroy()

    def wait_for_keypress(self):
        # self.canvas.focus_set()
        while self.advance == False:
            pass
            self.root.update()
            self.root.update_idletasks()
        self.advance = False
            

        

if __name__ == "__main__":
    gui = WFC_GUI(500, 500)
    while True:
        # gui.root.mainloop()
        gui.root.update()
        err_image = Image.open("assets/error_tile.png")
        gui.insert_image(err_image, 0, 0)
    
