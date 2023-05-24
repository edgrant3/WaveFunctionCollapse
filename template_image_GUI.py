import tkinter as tk
from tkinter import *
from tkinter import filedialog
from PIL import ImageTk, Image
import glob
import os

from wfc import Tile

class TemplateBuilder_GUI():
    def __init__(self, grid_dims=(12,12), scale=4):
        # Create the root window
        self.root = tk.Tk()
        self.root.title("Template Image Builder")
        self.root.focus_force()
        # self.root.configure(background="#808080")

        self.scale = scale
        self.grid_dims = grid_dims

        # Load tileset
        self.tileset_name = "village_tile_set2"
        self.load_tileset()

        # Create widgets
        self.allpad = 10

        self.default_img_color = (255, 0, 255)
        self.canvas_color = "white"
        self.canvas_pad = 5
        self.canvas = None
        self.create_canvas()

        self.show_grid = True
        self.draw_grid()

        self.control_panel = None
        self.create_control_panel()
        
        self.tileframe = None
        self.tileframe_canvas = None
        self.create_tileframe()

        self.selected_tile_view = None
        self.create_selected_tile_view()

        self.arrange_widgets()

        # Bind events
        self.canvas.bind("<Button-1>", self.handle_canvas_click)


        # Set up member variables
        # 1) selected regions of GUI
        self.selected_grid_idx = None
        self.selected_tile = None

        # 2) misc. data
        self.encoded_template = {}
        self.initialize_encoded_template(self.grid_dims)     

    def grid_to_pixel(self, grid_idx, use_canvas_pad=True):
        return (grid_idx[0] * self.tile_dims[0] + self.canvas_pad*use_canvas_pad, 
                grid_idx[1] * self.tile_dims[1] + self.canvas_pad*use_canvas_pad)
    
    def pixel_to_grid(self, pixel):
        return (pixel[0] // (self.tile_dims[0]), 
                pixel[1] // (self.tile_dims[1]))

    def arrange_widgets(self):
        # Arrange widgets using grid layout manager
        self.canvas.grid(row=1, column=0, padx=self.allpad, pady=self.allpad, sticky=N+S+E+W)
        self.tileframe.grid(row=1, column=1, padx=self.allpad, pady=self.allpad, sticky=N+S+E+W)
        self.control_panel.grid(row=0, column=0, sticky=N+S+E+W) #columnspan=self.root.grid_size()[0]
        self.selected_tile_view.grid(row=0, column=1, sticky=W+E)

    def load_tileset(self):
        Tile.tile_scaling = self.scale
        self.tileset, _, _ = Tile.generate_tiles_JSON(self.tileset_name)
        self.tile_dims = list(self.tileset.values())[0].img_size
    
    def create_canvas(self):

        if self.canvas is not None:
            self.canvas.destroy()

        self.w = self.tile_dims[0] * self.grid_dims[0]
        self.h = self.tile_dims[1] * self.grid_dims[1]

        self.canvas = tk.Canvas(self.root, width = self.w, height = self.h, 
                                background=self.canvas_color, borderwidth=self.canvas_pad, highlightthickness=0)

        self.img = Image.new("RGB", (self.w, self.h), self.default_img_color)
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)

        self.img_id = self.canvas.create_image(self.canvas_pad, self.canvas_pad, anchor=NW, image=self.tk_img)
        
    def create_control_panel(self):

        if self.control_panel is not None:
            self.control_panel.destroy()

        self.control_panel = tk.Frame(self.root, background="white", borderwidth=0, highlightthickness=0)

        self.grid_toggle_button = tk.Button(self.control_panel, text="Hide Grid", command=self.toggle_grid)
        self.grid_toggle_button.grid(row=0, column=0, padx=self.allpad, pady=self.allpad, sticky=N+S+E+W)

        self.tileset_load_button = tk.Button(self.control_panel, text="Load Tileset", command=self.update_tileset)
        self.tileset_load_button.grid(row=1, column=0, padx=self.allpad, pady=self.allpad, sticky=N+S+E+W)

        self.tileset_label = tk.Label(self.control_panel, text=self.tileset_name, bg="white", fg="blue", font=("Calibri", 16))
        self.tileset_label.grid(row=2, column=0, padx=self.allpad, pady=self.allpad, sticky=S, columnspan=2)

    def create_tileframe(self):

        if self.tileframe is not None:
            self.tileframe.destroy()

        w = self.tile_dims[0] * 2 + self.canvas_pad * 2
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
            # resized_image = image.resize((self.tile_dims[0], 
            #                               self.tile_dims[1]), 
            #                               resample = Image.NEAREST)
            button_image = ImageTk.PhotoImage(image)#, master = self.tileframe_inner)

            button = tk.Button(self.tileframe_inner, image=button_image, command=lambda id=(tile.id, tile.rot): self.tile_button_clicked(id))#, command=lambda tile=tile: self.select_tile(tile))
            button.grid(row=i // 2, column=i%2)
            self.tileframe_buttons.append(button)

            button.image = button_image

    def create_selected_tile_view(self):
        
        if self.selected_tile_view is not None:
            self.selected_tile_view.destroy()

        w = self.tile_dims[0] * 2
        h = self.tile_dims[1] * 2
        self.selected_tile_view = tk.Frame(self.root, width=w, height=h, background="white", borderwidth=self.canvas_pad, highlightthickness=0)

        self.selected_tile_canvas = tk.Canvas(self.selected_tile_view, width=w, height=h, borderwidth=0, bg="white")
        self.selected_tile_canvas.grid(row=0, column=0)
        self.selected_tile_img = Image.new("RGB", (w, h), self.default_img_color)
        self.selected_tile_img = ImageTk.PhotoImage(self.selected_tile_img, master = self.selected_tile_canvas)
        self.tile_viewimg_id = self.selected_tile_canvas.create_image(self.canvas_pad, self.canvas_pad, anchor=NW, image=self.selected_tile_img)

        label = tk.Label(self.selected_tile_view, text="Selected Tile", bg="white")
        label.grid(row=1, column=0)

        self.tile_button_clicked(list(self.tileset.keys())[0])

    def tile_button_clicked(self, tile_id):
        print(f"Selected tile: {tile_id}")
        self.selected_tile = tile_id
        image = Image.open(self.tileset[self.selected_tile].image_path)
        
        w, h = self.selected_tile_canvas.winfo_width(), self.selected_tile_canvas.winfo_height()
        resized_image = image.resize((w, h), resample = Image.NEAREST)
        self.selected_tile_img = ImageTk.PhotoImage(resized_image)

        self.selected_tile_canvas.itemconfig(self.tile_viewimg_id, image=self.selected_tile_img)
        
    def draw_grid(self, color="gray"):

        self.canvas.delete("grid")

        x_spacing = self.tile_dims[0]
        y_spacing = self.tile_dims[1]

        for x in range(x_spacing, self.tk_img.width(), x_spacing):
            self.canvas.create_line(x, 0, x, self.tk_img.height(), fill=color, tag="grid")

        for y in range(y_spacing, self.tk_img.height(), y_spacing):
            self.canvas.create_line(0, y, self.tk_img.width(), y, fill=color, tag="grid")

        self.canvas.move("grid", self.canvas_pad, self.canvas_pad)

    def toggle_grid(self):
        self.show_grid = not self.show_grid

        grid_button_txt = "Hide Grid" if self.show_grid else "Show Grid"
        self.grid_toggle_button.config(text=grid_button_txt)

        if self.show_grid:
            self.draw_grid()
        else:
            self.canvas.delete("grid")

    def update_tileset(self):
        print(f"\nLoading tileset...")
        path = tk.filedialog.askdirectory(initialdir = os.getcwd(), title = "Select tileset directory")
        if path == "":
            print("No tileset selected\n")
            return
        
        folder = os.path.basename(path)
        print(f'selected tileset: {folder}')
        print(f'from: {path}\n')

        self.tileset_name = folder
        self.tileset_label.config(text=self.tileset_name)
        self.load_tileset()
        self.create_canvas()
        self.create_tileframe()
        self.create_selected_tile_view()
        self.arrange_widgets()
        self.show_grid = True
        self.draw_grid()

        self.canvas.bind("<Button-1>", self.handle_canvas_click)
        
    def handle_canvas_click(self, event):
        selected = self.pixel_to_grid((event.x, event.y))
        self.highlight_selected_square(selected)
        if self.selected_tile is not None and self.selected_grid_idx is not None:
            self.insert_tile_image(self.selected_grid_idx, self.selected_tile)

    def highlight_selected_square(self, selected):
        self.canvas.delete("square_highlight")
        if selected == self.selected_grid_idx and self.selected_tile == self.encoded_template[selected]:
            self.selected_grid_idx = None
        else:
            self.selected_grid_idx = selected
            print(f"Selected grid index: {self.selected_grid_idx}")

            x, y = self.grid_to_pixel(self.selected_grid_idx, use_canvas_pad=True)
            self.canvas.create_rectangle(x, y, x + self.tile_dims[0], y + self.tile_dims[1], 
                                        outline="cyan", tag="square_highlight")

    def initialize_encoded_template(self, grid_dims):
        for x in range(grid_dims[0]):
            for y in range(grid_dims[1]):
                self.encoded_template[(x, y)] = (-1, 0)

    def insert_tile_image(self, idx, tile_id):
        self.encoded_template[idx] = tile_id
        self.img.paste(self.tileset[tile_id].image, self.grid_to_pixel(idx, use_canvas_pad=False))
        self.refresh_canvas()

    def refresh_canvas(self):
        self.tk_img = ImageTk.PhotoImage(self.img)
        self.canvas.itemconfig(self.img_id, image=self.tk_img)

if __name__ == "__main__":
    gui = TemplateBuilder_GUI()
    gui.root.mainloop()



