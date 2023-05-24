import tkinter as tk
from tkinter import *
from PIL import ImageTk, Image
import glob

from wfc import Tile

class TemplateBuilder_GUI():
    def __init__(self, grid_dims=(12,12), scale=3):
        self.root = tk.Tk()
        self.root.title("Template Image Builder")
        self.root.focus_force()
        # self.root.configure(background="#808080")

        self.tileset_name = "village_tile_set"
        Tile.tile_scaling = 1
        self.tileset, _, _ = Tile.generate_tiles_JSON(self.tileset_name)

        self.grid_dims = grid_dims
        self.tile_dims = list(self.tileset.values())[0].img_size
        self.scale = scale

        self.default_img_color = (255, 0, 255)
        self.canvas_color = "white"
        self.canvas_pad = 5
        self.canvas = None
        self.create_canvas(self.tile_dims, self.grid_dims)

        self.show_grid = True
        self.draw_grid()

        self.control_panel = None
        self.create_control_panel()
        
        self.tileframe = None
        self.tileframe_canvas = None
        self.create_tileframe()

        # Arrange widgets using grid layout manager
        allpad = 10
        self.canvas.grid(row=1, column=0, padx=allpad, pady=allpad, sticky=N+S+E+W)
        self.tileframe.grid(row=1, column=1, padx=allpad, pady=allpad, sticky=N+S+E+W)
        self.control_panel.grid(row=0, column=0, columnspan=self.root.grid_size()[0], sticky=E+W)

        self.encoded_template = {}

    def create_canvas(self, tile_dims, grid_dims):

        if self.canvas is not None:
            self.canvas.destroy()

        self.w = tile_dims[0] * grid_dims[0] * self.scale
        self.h = tile_dims[1] * grid_dims[1] * self.scale

        self.canvas = tk.Canvas(self.root, width = self.w, height = self.h, 
                                background=self.canvas_color, borderwidth=self.canvas_pad, highlightthickness=0)

        self.img = Image.new("RGB", (self.w, self.h), self.default_img_color)
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)

        self.img_id = self.canvas.create_image(self.canvas_pad, self.canvas_pad, anchor=NW, image=self.tk_img)
        
    def create_control_panel(self):

        if self.control_panel is not None:
            self.control_panel.destroy()

        self.control_panel = tk.Frame(self.root, height=100, background="white", borderwidth=0, highlightthickness=0)

        self.grid_toggle_button = tk.Button(self.control_panel, text="Toggle Grid", command=self.toggle_grid)
        self.grid_toggle_button.grid(row=0, column=0, sticky=N+S+E+W)


    def create_tileframe(self):

        if self.tileframe is not None:
            self.tileframe.destroy()

        w = 100
        h = self.tk_img.height()
        self.tileframe = tk.Frame(self.root, width=w, height=h, background="white", borderwidth=self.canvas_pad, highlightthickness=0)
        
        self.tileframe_canvas = tk.Canvas(self.tileframe, width=w, height=h, borderwidth=0, bg="white")
        
        scroll = tk.Scrollbar(self.tileframe, orient=VERTICAL, command=self.tileframe_canvas.yview)
        self.tileframe_canvas.configure(yscrollcommand=scroll.set)
        self.tileframe_canvas.bind("<Configure>", lambda e: self.tileframe_canvas.configure(scrollregion=self.tileframe_canvas.bbox("all")))

        self.tileframe_inner = tk.Frame(self.tileframe_canvas, background="grey")

        self.tileframe_canvas.grid(row=0, column=0)
        scroll.grid(row=0, column=1, sticky=N+S)

        # self.tileframe_canvas.create_window((0,0), window=self.tileframe_inner, anchor="nw", tags="self.frame")
        self.tileframe_canvas.create_window((0, 0), window=self.tileframe_inner, anchor="nw")
        
        self.populate_tileframe()

    def populate_tileframe(self):
        self.tileframe_buttons = []
        # if images have been loaded
        for i, tile in enumerate(self.tileset.values()):
            image = Image.open(tile.image_path)
            resized_image = image.resize((self.tile_dims[0] * self.scale, 
                                          self.tile_dims[1] * self.scale), 
                                          resample = Image.NEAREST)
            button_image = ImageTk.PhotoImage(resized_image)#, master = self.tileframe_inner)

            button = tk.Button(self.tileframe_inner, image=button_image)#, command=lambda tile=tile: self.select_tile(tile))
            button.grid(row=i // 2, column=i%2)
            self.tileframe_buttons.append(button)

            button.image = button_image

    def draw_grid(self, color="gray"):

        self.canvas.delete("grid")

        x_spacing = self.tile_dims[0] * self.scale
        y_spacing = self.tile_dims[1] * self.scale

        for x in range(x_spacing, self.tk_img.width(), x_spacing):
            self.canvas.create_line(x, 0, x, self.tk_img.height(), fill=color, tag="grid")

        for y in range(y_spacing, self.tk_img.height(), y_spacing):
            self.canvas.create_line(0, y, self.tk_img.width(), y, fill=color, tag="grid")

        self.canvas.move("grid", self.canvas_pad, self.canvas_pad)

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        if self.show_grid:
            self.draw_grid()
        else:
            self.canvas.delete("grid")

if __name__ == "__main__":
    gui = TemplateBuilder_GUI()
    gui.root.mainloop()



