import tkinter as tk
from tkinter import *
from PIL import ImageTk, Image

# Creating a tkinter-based GUI for displaying the output of the WFC algorithm
class WFC_GUI():
    canvas_padding = 0.05
    def __init__(self, w, h, grid_dims = None, launch_fullscreen = False):
        self.root = tk.Tk()
        self.root.title("Wave Function Collapse")
        self.root.focus_force()
        #self.screen_dims = (self.root.winfo_screenwidth(), self.root.winfo_screenheight())

        self.grid_dims = grid_dims

        if launch_fullscreen:
            self.root.attributes('-fullscreen', True)

        self.border_size = (int(w*self.canvas_padding/2), int(h*self.canvas_padding/2))

        self.background_color = (255, 0, 0)
        self.canvas = None
        self.create_canvas(w, h)

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
        if self.canvas != None:
            self.canvas.destroy()
        canvas_size = (w + int(w*self.canvas_padding), h + int(h*self.canvas_padding))
        self.canvas = tk.Canvas(self.root, width = canvas_size[0], height = canvas_size[1], background="white")
        self.canvas.pack()

        self.img = Image.new("RGB", (w, h), self.background_color)
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)

        self.img_id = self.canvas.create_image(self.border_size[0], self.border_size[1], 
                                               anchor=NW, image=self.tk_img)

    def insert_image(self, new_img, x, y):
        self.img.paste(new_img, (x, y))

    def refresh_canvas(self):
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)
        self.canvas.itemconfig(self.img_id, image=self.tk_img)
    
    def clear_canvas(self):
        self.img = Image.new("RGB", (self.img.width, self.img.height), self.background_color)
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
        while self.advance == False:
            pass
            self.root.update()
            self.root.update_idletasks()
        self.advance = False
    
