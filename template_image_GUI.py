import tkinter as tk
from tkinter import *
from tkinter import filedialog
from PIL import ImageTk, Image
import glob
import os
import json

from wfc import Tile

class TemplateBuilder_GUI():
    def __init__(self, grid_dims=(15,15), scale=3):
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
        self.canvas_pad = 5
        self.default_img_color = (255, 0, 255)
        self.create_widgets()

        # 2) misc. data
        self.encoded_template = {}
        self.initialize_encoded_template()     

    def grid_to_pixel(self, grid_idx, use_canvas_pad=True):
        return (grid_idx[0] * self.tile_dims[0] + self.canvas_pad*use_canvas_pad, 
                grid_idx[1] * self.tile_dims[1] + self.canvas_pad*use_canvas_pad)
    
    def pixel_to_grid(self, pixel, use_canvas_pad=True):
        return ((pixel[0] - self.canvas_pad*use_canvas_pad) // (self.tile_dims[0]), 
                (pixel[1] - self.canvas_pad*use_canvas_pad) // (self.tile_dims[1]))

    def create_widgets(self):
        self.canvas = None
        self.control_panel = None
        self.tileframe = None
        self.tileframe_canvas = None
        self.selected_tile_view = None
        self.create_canvas()
        self.create_control_panel()
        self.create_tileframe()
        self.create_selected_tile_view()

        self.show_grid = True
        self.draw_grid()

        self.arrange_widgets()

        self.hovered_widget = None
        self.bind_events()

        # Set up member variables
        # 1) selected regions of GUI
        self.selected_grid_idx = None
        self.selected_tile = None
    
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
                                background="white", borderwidth=self.canvas_pad, highlightthickness=0)

        self.img = Image.new("RGB", (self.w, self.h), self.default_img_color)
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)

        self.img_id = self.canvas.create_image(self.canvas_pad, self.canvas_pad, anchor=NW, image=self.tk_img)
        
    def create_control_panel(self):

        if self.control_panel is not None:
            self.control_panel.destroy()

        self.control_panel = tk.Frame(self.root, background="white", borderwidth=0, highlightthickness=0)

        self.grid_toggle_button = tk.Button(self.control_panel, text="Hide Grid", command=self.handle_toggle_grid)
        self.grid_toggle_button.grid(row=0, column=1, padx=self.allpad, pady=self.allpad, sticky=N+S+E+W)

        self.tileset_load_button = tk.Button(self.control_panel, text="Load Tileset", command=self.update_tileset)
        self.tileset_load_button.grid(row=0, column=0, padx=self.allpad, pady=self.allpad, sticky=N+S+E+W)

        self.save_button = tk.Button(self.control_panel, text="Save Template", command=self.handle_save_template)
        self.save_button.grid(row=0, column=4, padx=self.allpad, pady=self.allpad, sticky=E)

        self.load_button = tk.Button(self.control_panel, text="Load Template", command=self.handle_load_template)
        self.load_button.grid(row=1, column=4, padx=self.allpad, pady=self.allpad, sticky=E)

        self.tileset_label = tk.Label(self.control_panel, text=self.tileset_name, bg="white", fg="blue", font=("Calibri", 16))
        self.tileset_label.grid(row=1, column=0, padx=self.allpad, pady=self.allpad, sticky=S, columnspan=2)

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
        i = 0
        for tile in self.tileset.values():
            if tile.rot != 0:
                continue
            image = Image.open(tile.image_path)
            button_image = ImageTk.PhotoImage(image)#, master = self.tileframe_inner)

            button = tk.Button(self.tileframe_inner, image=button_image, command=lambda id=(tile.id, tile.rot): self.handle_tile_button_clicked(id))#, command=lambda tile=tile: self.select_tile(tile))
            button.grid(row=i // 2, column=i%2)
            self.tileframe_buttons.append(button)

            button.image = button_image
            i += 1

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

        self.handle_tile_button_clicked(list(self.tileset.keys())[0])

    def handle_tile_button_clicked(self, tile_id):
        print(f"Selected tile: {tile_id}")
        self.selected_tile = tile_id
        image = Image.open(self.tileset[self.selected_tile].image_path)
        
        w, h = self.selected_tile_canvas.winfo_width(), self.selected_tile_canvas.winfo_height()
        resized_image = image.resize((w, h), resample = Image.NEAREST)
        self.selected_tile_img = ImageTk.PhotoImage(resized_image)

        self.selected_tile_canvas.itemconfig(self.tile_viewimg_id, image=self.selected_tile_img)
        
    def update_tileset(self):
        print(f"\nLoading tileset...")
        # path = filedialog.askdirectory(initialdir = os.getcwd(), title = "Select tileset directory")
        path = filedialog.askdirectory(initialdir = "./", title = "Select tileset directory")
        if path == "":
            print("No tileset selected\n")
            return
        
        folder = os.path.basename(path)
        print(f'selected tileset: {folder}')
        print(f'from: {path}\n')

        self.tileset_name = folder
        self.tileset_label.config(text=self.tileset_name)
        self.load_tileset()
        self.create_widgets()

        self.initialize_encoded_template()
            
    def initialize_encoded_template(self):
        self.encoded_template["tileset_name"] = self.tileset_name
        for x in range(self.grid_dims[0]):
            for y in range(self.grid_dims[1]):
                self.encoded_template[(x, y)] = (-1, 0)

    def insert_tile_image(self, idx, tile_id):
        self.encoded_template[idx] = tile_id
        self.img.paste(self.tileset[tile_id].image, self.grid_to_pixel(idx, use_canvas_pad=False))
        self.refresh_canvas()

    def refresh_canvas(self):
        self.tk_img = ImageTk.PhotoImage(self.img)
        self.canvas.itemconfig(self.img_id, image=self.tk_img)

    def bind_events(self):
        self.canvas.bind("<Button-1>", self.handle_canvas_click)
        self.root.bind("<Escape>", self.handle_close_window)
        self.root.bind("g", self.handle_toggle_grid)
        self.root.bind("q", self.handle_rotate_tile_ccw)
        self.root.bind("e", self.handle_rotate_tile_cw)
        self.canvas.bind("<Motion>", self.handle_mouse_motion)
        self.canvas.bind("<B1-Motion>", self.handle_canvas_drag)
        self.canvas.bind("<Leave>", self.handle_leave_canvas)
        
        self.root.bind("<Control-s>", self.handle_save_template)

    def handle_canvas_click(self, event):
        if self.selected_tile is not None and self.selected_grid_idx is not None:
            self.insert_tile_image(self.selected_grid_idx, self.selected_tile)

    def get_grid_idx_from_event(self, event):
        idx = self.pixel_to_grid((event.x, event.y))
        if min(idx) < 0 or idx[0] >= self.grid_dims[0] or idx[1] >= self.grid_dims[1]:
            return None
        return idx
    
    def handle_canvas_drag(self, event):
        idx = self.get_grid_idx_from_event(event)
        if idx is None:
            return
        self.handle_mouse_motion(event, idx)
        if self.selected_tile is not None:
            self.insert_tile_image(idx, self.selected_tile)
            
    def handle_toggle_grid(self, event=None):
        self.show_grid = not self.show_grid

        grid_button_txt = "Hide Grid" if self.show_grid else "Show Grid"
        self.grid_toggle_button.config(text=grid_button_txt)

        self.draw_grid() if self.show_grid else self.canvas.delete("grid")

    def handle_close_window(self, event):
        self.root.destroy()

    def handle_mouse_motion(self, event, idx=None):
        # idx = self.pixel_to_grid((event.x, event.y))
        # if min(idx) < 0 or idx[0] >= self.grid_dims[0] or idx[1] >= self.grid_dims[1]:
        #     return
        if idx is None:
            idx = self.get_grid_idx_from_event(event)
            
        
        if self.selected_grid_idx != idx and idx is not None:
            self.show_preview_square(idx)
            self.highlight_hovered_square(idx)
            self.selected_grid_idx = idx

    def handle_leave_canvas(self, event):
        self.canvas.delete("square_highlight")
        self.canvas.delete("preview_square")
        self.selected_grid_idx = None

    def handle_rotate_tile_ccw(self, event):
        self.handle_rotate_tile(-1)

    def handle_rotate_tile_cw(self, event):
        self.handle_rotate_tile(1)

    def handle_rotate_tile(self, dir):
        if self.selected_tile is None:
            return
        
        tile = self.tileset[self.selected_tile]

        if tile.num_rotations <= 1:
            print("Tile has no rotations")
            return

        new_rot = (tile.rot + dir) % 4 # square tiles only have 4 possible rotations
        self.selected_tile = (self.selected_tile[0], new_rot)
        while True:
            if self.selected_tile in self.tileset:
                break
            new_rot = (new_rot + dir) % 4
            self.selected_tile = (self.selected_tile[0], new_rot)
        self.handle_tile_button_clicked(self.selected_tile)
        self.update_preview_img()

    def handle_save_template(self, event=None):
        print('\nSaving template...\n')
        f = filedialog.asksaveasfile(initialdir="./assets/"+self.tileset_name, initialfile=f'{self.tileset_name}_template', defaultextension=".json", filetypes=[("JSON File", "*.json")])
        # Need to encode dict keys as strings because JSON doesn't handle tuple keys
        string_keys_encoded_template = {str(k): v for k, v in self.encoded_template.items()}
        f.write(json.dumps(string_keys_encoded_template))

    def handle_load_template(self, event=None):
        print('\nLoading template...')
        f = filedialog.askopenfile(initialdir="./assets", filetypes=[("JSON File", "*.json")])
        if f is None:
            print('No file selected\n')
            return
        
        loaded_template = json.load(f)
        self.tileset_name = loaded_template.pop('tileset_name', None)
        print(self.tileset_name)
        # Need to recreate tuple keys from string keys
        self.encoded_template = {tuple(map(int, k.replace('(','').replace(')','').split(','))): v for k, v in loaded_template.items()}
        self.encoded_template['tileset_name'] = self.tileset_name

        self.tileset_label.config(text=self.tileset_name)
        self.load_tileset()
        self.create_widgets()

        self.draw_from_template()

    def draw_from_template(self):
        for idx, tile in self.encoded_template.items():
            if tile[0] == -1 or idx == 'tileset_name':
                continue
            self.img.paste(self.tileset[tuple(tile)].image, self.grid_to_pixel(idx, use_canvas_pad=False))
        self.refresh_canvas()

    def show_preview_square(self, hover_idx):
        
        if self.selected_tile == None:
            return
        
        self.canvas.delete("preview_square")
        x, y = self.grid_to_pixel(hover_idx, use_canvas_pad=True)
        image = self.tileset[self.selected_tile].image
        image = image.convert("RGBA")
        image.putalpha(200)
        self.preview_img = ImageTk.PhotoImage(image)
        self.preview_id = self.canvas.create_image(x, y, anchor=NW, image=self.preview_img, tag="preview_square")

    def update_preview_img(self):
        image = self.tileset[self.selected_tile].image
        image = image.convert("RGBA")
        image.putalpha(200)
        self.preview_img = ImageTk.PhotoImage(image)
        self.canvas.itemconfig(self.preview_id, image=self.preview_img)

    def highlight_hovered_square(self, hover_idx):
        self.canvas.delete("square_highlight")
        self.selected_grid_idx = hover_idx

        x, y = self.grid_to_pixel(self.selected_grid_idx, use_canvas_pad=True)
        self.canvas.create_rectangle(x, y, x + self.tile_dims[0], y + self.tile_dims[1], 
                                    outline="cyan", tag="square_highlight")

    def draw_grid(self, color="gray"):

        self.canvas.delete("grid")

        x_spacing = self.tile_dims[0]
        y_spacing = self.tile_dims[1]

        for x in range(x_spacing, self.tk_img.width(), x_spacing):
            self.canvas.create_line(x, 0, x, self.tk_img.height(), fill=color, tag="grid")

        for y in range(y_spacing, self.tk_img.height(), y_spacing):
            self.canvas.create_line(0, y, self.tk_img.width(), y, fill=color, tag="grid")

        self.canvas.move("grid", self.canvas_pad, self.canvas_pad)

if __name__ == "__main__":
    gui = TemplateBuilder_GUI()
    gui.root.mainloop()



