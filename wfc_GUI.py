import tkinter as tk
from tkinter import *
from tkinter import filedialog
from PIL import ImageTk, Image

from wfc import WFCRules
# from template import Template

def RGB2HEX(rgbcol):
    return '#%02x%02x%02x' % rgbcol

# Creating a tkinter-based GUI for displaying the output of the WFC algorithm
class WFC_GUI():
    canvas_padding = 0.05
    def __init__(self, wfc_dict, run_animated = False, wfc_toggle=0, launch_fullscreen = False):

        self.wfc_dict = wfc_dict
        self.wfc_toggle = wfc_toggle
        self.wfc = wfc_dict[wfc_toggle]

        self.run_animated = run_animated
        self.run_stepwise = False
        
        self.root = tk.Tk()
        self.root.title("Wave Function Collapse")
        self.root.focus_force()

        if launch_fullscreen:
            self.root.attributes('-fullscreen', True)

        w, h = self.wfc.win_size
        self.border_size = (int(w*self.canvas_padding/2), int(h*self.canvas_padding/2))

        self.background_color = (255, 0, 0)
        self.allpad = 10
        self.canvas_pad = 5
        self.canvas = None
        self.panel  = None
        self.create_widgets()
        self.bind_events()

    def grid_to_pixel(self, grid_idx, use_canvas_pad=True):
        '''grid_idx is in (col, row) format, output is in (x, y) pixels'''
        return (grid_idx[0] * self.wfc.template.tileset.tile_px_w + self.canvas_pad*use_canvas_pad,
                grid_idx[1] * self.wfc.template.tileset.tile_px_h + self.canvas_pad*use_canvas_pad)
    
    def pixel_to_grid(self, pixel, use_canvas_pad=True):
        '''convert (x,y) pixel to grid dims (row, col)'''
        return ((pixel[0] - self.canvas_pad*use_canvas_pad) // (self.wfc.template.tileset.tile_px_w),
                (pixel[1] - self.canvas_pad*use_canvas_pad) // (self.wfc.template.tileset.tile_px_h))

    def get_grid_idx_from_event(self, event):
        idx = self.pixel_to_grid((event.x, event.y))
        if min(idx) < 0 or idx[0] >= self.wfc.grid_size[0] or idx[1] >= self.wfc.grid_size[0]:
            return None
        return idx

    def close_win(self, event=None):
        self.root.destroy()

    def bind_events(self):
        # Window Events
        if self.run_stepwise:
            self.root.bind("<Right>",  self.run_draw_step)
            # self.root.bind("<Left>",   self.handle_advance_tileset)
        else:
            self.root.bind("<Right>",  self.handle_advance_tileset)
            self.root.bind("<Left>",   self.handle_advance_tileset)
        self.root.bind("<Escape>", self.close_win)
        self.root.bind("<space>",  self.run_draw)
        # Canvas Events
        self.canvas.bind("<Button-1>", self.handle_canvas_click)
        self.canvas.bind("<Motion>", self.handle_mouse_motion)
        self.root.bind("<Control-s>", self.save_result)
    
    def create_widgets(self):
        self.create_canvas()
        self.create_panel()
        self.arrange_widgets()

    def arrange_widgets(self):
        self.panel.grid(row=0, column=0, padx=self.allpad, pady=self.allpad, sticky=N+S+E+W)
        self.canvas.grid(row=0, column=1, padx=self.allpad, pady=self.allpad)
    
    def invoke_rule_button(self, rule):
        if rule.value == WFCRules.SOCKETS_ONLY.value:
            self.rules_sockets_only_button.invoke()

        elif rule.value == WFCRules.TEMPLATES_ONLY.value:
            self.rules_templates_only_button.invoke()

        elif rule.value == WFCRules.BOTH_STRICT.value:
            self.rules_both_strict_button.invoke()

        elif rule.value == WFCRules.BOTH_RELAXED.value:
            self.rules_both_relaxed_button.invoke()

    def create_panel(self):
        if self.panel is not None:
            self.control_panel.destroy()

        # Panel Frame 
        self.panel = tk.Frame(self.root, background="white", borderwidth=0, highlightthickness=0)
        panel_cols = 3
        
        # Panel Contents
        ### Label for current template/tileset
        self.tileset_label = tk.Label(self.panel, text=self.wfc.template.tileset.name, bg=RGB2HEX((220,220,220)), 
                                      fg="blue", font=("Calibri", 18), padx=self.allpad)

        ### run_animated checkbox
        self.animboxval = IntVar()
        self.animate_checkbox = tk.Checkbutton(self.panel, text='Animate Solution', variable=self.animboxval, onvalue=1, offvalue=0, command=self.set_animated)

        ### run stepwise checkbox
        self.stepboxval = IntVar()
        self.stepper_checkbox = tk.Checkbutton(self.panel, text='Manual Step Through', variable=self.stepboxval, onvalue=1, offvalue=0, command=self.set_stepwise)

        ### WFC Rules Radiobutton Set
        rf_col = "white" #RGB2HEX((230,230,230))
        self.rules_frame = tk.Frame(self.panel, bg=rf_col, borderwidth=1, highlightthickness=2)
        from wfc import WFCRules
        self.wfc_rules = IntVar()
        self.rules_sockets_only_button   = tk.Radiobutton(self.rules_frame, bg=rf_col, command=self.update_rules, text="Use Only Sockets",              variable=self.wfc_rules, value=WFCRules.SOCKETS_ONLY.value)
        self.rules_templates_only_button = tk.Radiobutton(self.rules_frame, bg=rf_col, command=self.update_rules, text="Use Only Templates",            variable=self.wfc_rules, value=WFCRules.TEMPLATES_ONLY.value)
        self.rules_both_strict_button    = tk.Radiobutton(self.rules_frame, bg=rf_col, command=self.update_rules, text="Use Both, Strict Match",        variable=self.wfc_rules, value=WFCRules.BOTH_STRICT.value)
        self.rules_both_relaxed_button   = tk.Radiobutton(self.rules_frame, bg=rf_col, command=self.update_rules, text="Use Both, Sockets Priority", variable=self.wfc_rules, value=WFCRules.BOTH_RELAXED.value)
        self.rules_sockets_only_button.grid(  row=0, column=0, padx=self.allpad, pady=0, sticky=W)
        self.rules_templates_only_button.grid(row=1, column=0, padx=self.allpad, pady=0, sticky=W)
        self.rules_both_strict_button.grid(   row=2, column=0, padx=self.allpad, pady=0, sticky=W)
        self.rules_both_relaxed_button.grid(  row=3, column=0, padx=self.allpad, pady=0, sticky=W)
        self.invoke_rule_button(self.wfc_dict[0].rules)

        ### left, right, and refresh buttons
        self.control_frame = tk.Frame(self.panel, background="white", borderwidth=0, highlightthickness=0)
        icon_size = (35,35)
        refresh_img = Image.open("./assets/return_icon.png").resize(icon_size)
        r_arrow_img = Image.open("./assets/arrowhead_icon.png").resize(icon_size)
        l_arrow_img = r_arrow_img.rotate(180.0)
        refresh_button_img = ImageTk.PhotoImage(refresh_img)
        r_arrow_button_img = ImageTk.PhotoImage(r_arrow_img)
        l_arrow_button_img = ImageTk.PhotoImage(l_arrow_img)

        self.left_arrow_button  = tk.Button(self.control_frame, image=l_arrow_button_img, command=lambda dir= -1: self.advance_tileset(dir))
        self.right_arrow_button = tk.Button(self.control_frame, image=r_arrow_button_img, command=lambda dir=  1: self.advance_tileset(dir))
        self.refresh_button     = tk.Button(self.control_frame, image=refresh_button_img, command=self.run_draw)
        self.left_arrow_button.image  = l_arrow_button_img
        self.right_arrow_button.image = r_arrow_button_img
        self.refresh_button.image     = refresh_button_img
        self.left_arrow_button.grid( row=1, column=0, padx=10, pady=0, sticky=E)
        self.right_arrow_button.grid(row=1, column=2, padx=10, pady=0, sticky=W)
        self.refresh_button.grid(    row=1, column=1, padx=10, pady=0)

        ### RNG seed checkBox
        self.use_rng_seed_val  = IntVar()
        self.rng_seed_checkbox = tk.Checkbutton(self.panel, text='Use Seed', variable=self.use_rng_seed_val, onvalue=1, offvalue=0, command=self.set_rng_seed)
        
        ### RNG seed entry
        self.rng_seed_entry = tk.Entry(self.panel, width=10, borderwidth=3)
        self.rng_seed_entry.insert(0, str(0))
        self.rng_seed_entry.config(state=DISABLED)
        
        ### RNG seed entry button
        self.rng_seed_entry_button = tk.Button(self.panel, text="Set", command=self.set_rng_seed, height=1)
        
        ### Open TemplateBuilder button
        self.open_TB_button = tk.Button(self.panel, text="Open Template Builder", command=self.open_template_builder)
        
        ### Hovered tile stats set
        self.hovered_tile_frame = tk.Frame(self.panel, bg=rf_col, borderwidth=1, highlightthickness=2)
        self.hovered_tile_label = tk.Label(self.hovered_tile_frame, text="Tile Stats:", bg=RGB2HEX((220,220,220)), 
                                fg="black", font=("Calibri", 12), padx=0)
        self.hovered_tile_label.grid(row=0, column=0, padx=0, pady=self.allpad, sticky=W)
        # Hovered tile collapsed
        self.hovered_tile_collapsed_label = tk.Label(self.hovered_tile_frame, text="Collapsed ID: ", bg="white", fg="black", font=("Calibri", 12))
        self.hovered_tile_collapsed_value = tk.Label(self.hovered_tile_frame, text="", bg="white", fg="black", font=("Calibri", 12))
        self.hovered_tile_collapsed_label.grid(row=1, column=0, padx=0, pady=0, sticky=W)
        self.hovered_tile_collapsed_value.grid(row=1, column=1, padx=0, pady=0, sticky=W)
        # Hovered tile entropy
        self.hovered_tile_entropy_label = tk.Label(self.hovered_tile_frame, text="Entropy: ", bg="white", fg="black", font=("Calibri", 12))
        self.hovered_tile_entropy_value = tk.Label(self.hovered_tile_frame, text="", bg="white", fg="black", font=("Calibri", 12))
        self.hovered_tile_entropy_label.grid(row=2, column=0, padx=0, pady=0, sticky=W)
        self.hovered_tile_entropy_value.grid(row=2, column=1, padx=0, pady=0, sticky=W)

        # ARRANGE THE PANEL WIDGETS
        self.tileset_label.grid(row=0, column=0, padx=self.allpad, pady=(self.allpad, self.allpad), sticky=N, columnspan=panel_cols)
        self.control_frame.grid(row=1, column=0, padx=0, pady=(0, self.allpad), columnspan=panel_cols)
        self.rules_frame.grid(row=2, column=0, padx=0, pady=(0,self.allpad), columnspan=panel_cols)
        self.animate_checkbox.grid(row=3, column=0, padx=self.allpad, pady=0, columnspan=2, sticky=W)
        self.stepper_checkbox.grid(row=3, column=1, padx=self.allpad, pady=0, columnspan=1, sticky=W)
        self.rng_seed_checkbox.grid(row=4, column=0, padx=self.allpad, pady=self.allpad, columnspan=1)
        self.rng_seed_entry.grid(row=4, column=panel_cols-2, padx=self.allpad, pady=self.allpad)
        self.rng_seed_entry_button.grid(row=4, column=panel_cols-1, padx=self.allpad, pady=self.allpad)
        self.open_TB_button.grid(row = 5, column=0, padx=self.allpad, pady=2*self.allpad, columnspan=panel_cols)
        self.hovered_tile_frame.grid(row=7, column=0, padx=self.allpad, pady=2*self.allpad, columnspan=panel_cols)
        
    def create_canvas(self):
        if self.canvas is not None:
            self.canvas.delete('all')
            self.canvas.destroy()

        self.refresh_canvas_size()
        self.canvas = tk.Canvas(self.root, width = self.canvas_w, height = self.canvas_h, 
                                bg=RGB2HEX((220,220,220)), borderwidth=self.canvas_pad, highlightthickness=0)
        self.create_canvas_img()

    def create_canvas_img(self):
        self.img = Image.new("RGB", (self.canvas_w, self.canvas_h), self.background_color)
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)

        self.img_id = self.canvas.create_image(self.canvas_pad, self.canvas_pad, 
                                               anchor=NW, image=self.tk_img)

    def insert_image(self, new_img, x, y):
        self.img.paste(new_img, (x, y))

    def refresh_canvas_size(self):
        self.canvas_w = self.wfc.template.tileset.tile_px_w * self.wfc.grid_size[0]
        self.canvas_h = self.wfc.template.tileset.tile_px_h * self.wfc.grid_size[1]
        if self.canvas is not None:
            self.canvas.config(height=self.canvas_h, width=self.canvas_w)

    def refresh_canvas(self):
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)
        self.canvas.itemconfig(self.img_id, image=self.tk_img)
    
    def clear_canvas(self):
        self.refresh_canvas_size()
        self.create_canvas_img()
        self.img = Image.new("RGB", (self.img.width, self.img.height), self.background_color)
        self.tk_img = ImageTk.PhotoImage(self.img, master = self.canvas)
        self.refresh_canvas()

    def set_rng_seed(self):
        print(f'Setting RNG seed to {self.rng_seed_entry.get()}')
        if self.use_rng_seed_val.get():
            self.rng_seed_entry.config(state=NORMAL)
            self.wfc.set_seed(int(self.rng_seed_entry.get()))
        else:
            self.rng_seed_entry.config(state=DISABLED)
            self.wfc.set_seed(None)

        self.wfc.init_rng()
        print('Running from WFC_GUI.set_rng_seed()')
        self.run_draw()

    def set_wfc_toggle(self, val):
        self.wfc_toggle = val % len(self.wfc_dict.keys())

    def set_active_wfc(self, wfc_idx):
        self.set_wfc_toggle(wfc_idx)
        self.wfc = self.wfc_dict[wfc_idx]

    def set_animated(self):
        self.run_animated = self.animboxval.get() == 1
        self.run_stepwise = False
        self.bind_events()

    def set_stepwise(self):
        self.wfc.clear_data()
        self.run_stepwise = self.stepboxval.get() == 1
        self.run_animated = False
        self.bind_events()

    def update_rules(self):
        for w in self.wfc_dict.values():
            w.set_rules(self.wfc_rules.get())
        print('Running from WFC_GUI.update_rules()')
        self.run_draw()

    def print_tile_stats(self, idx):
        if idx not in self.wfc.tile_map:
            print(f'\nNo tile exists @ {idx}')
            return
        t = self.wfc.tile_map[idx]
        # print(f'\nTile @ {idx} has collapsed ID {t.collapsed}')
        print(f'\nTile @ {idx} has collapsed ID {t.collapsed}, IDX {(t.collapsed if t.collapsed is None else self.wfc.template.tileset.idANDidx[t.collapsed])}\n -possible tile array {t.possible},\n -distribution {t.distribution}')
        print(f' -prob_sum: {sum(t.distribution * t.possible)}\n -entropy: {t.entropy}\n')

    def handle_mouse_motion(self, event):
        idx = self.get_grid_idx_from_event(event)
        self.highlight_hovered_square(idx)
        hovered_tile = self.get_hovered_tile(idx)
        if hovered_tile is not None:
            self.display_hovered_square_stats(hovered_tile)

    def get_hovered_tile(self, idx):
        if idx in self.wfc.tile_map:
            return self.wfc.tile_map[idx]
        # return self.wfc.create_waveTileAdvanced()
        return None

    def display_hovered_square_stats(self, tile):
        self.hovered_tile_entropy_value.config(text=round(tile.entropy, 3))
        if tile.collapsed is None:
            self.hovered_tile_collapsed_value.config(text=f'(None)')
            return

        self.hovered_tile_collapsed_value.config(text=f'({tile.collapsed[0]}, {tile.collapsed[1]})')



    def highlight_hovered_square(self, hover_idx):
        self.canvas.delete("square_highlight")
        if hover_idx is not None:
            x, y = self.grid_to_pixel(hover_idx, use_canvas_pad=True)
            self.canvas.create_rectangle(x, y, x + self.wfc.template.tileset.tile_px_w, y + self.wfc.template.tileset.tile_px_h, 
                                        outline="cyan", tag="square_highlight")

    def handle_canvas_click(self, event):
        idx = self.get_grid_idx_from_event(event)
        self.print_tile_stats(idx)

    def handle_advance_tileset(self, event):
        dir = 0
        if event.keysym == 'Right':
            dir = 1
        elif event.keysym == 'Left':
            dir = -1
        self.advance_tileset(dir)

    def advance_tileset(self, dir):
        self.set_wfc_toggle(self.wfc_toggle + dir)
        self.set_active_wfc(self.wfc_toggle)
        self.tileset_label.config(text=self.wfc.template.tileset.name)
        print("Running from WFC_GUI.advance_tileset()")
        self.run_draw()

    def save_result(self, event):
        print(f'\nSaving...')
        f = filedialog.asksaveasfile(initialdir="./captures/output/"+self.wfc.template.tileset.name, 
                                     initialfile=f'{self.wfc.template.tileset.name}', 
                                     defaultextension=".png", filetypes=[("PNG File", "*.png")])
        self.img.save(f.name)
        print(f'Saved Image: \n{f.name}\n')

    def draw_tile(self, idx, refresh = False):
        # print(f'Drawing tile at {idx} with id {self.tile_map[idx].collapsed}')
        if self.wfc.tile_map[idx].collapsed is None:
            img = self.wfc.template.tileset.tiles[(-1,0)].image
        else:
            img = self.wfc.template.tileset.tiles[self.wfc.tile_map[idx].collapsed].image
        size = (self.wfc.template.tileset.tile_px_w, self.wfc.template.tileset.tile_px_w)
        x = int(idx[0]*size[0])
        y = int(idx[1]*size[1])
        self.insert_image(img, x, y)
        if refresh:
            self.refresh_canvas()
            self.root.update()

    def draw_all(self, refresh = False):
        # self.create_canvas()
        self.clear_canvas()
        for idx in self.wfc.tile_map:
            self.draw_tile(idx, refresh)
        self.refresh_canvas()
        self.root.update()

    def run_draw(self, event=None):
        if self.run_stepwise:
            self.run_draw_step()
            return
        
        self.wfc.clear_data()

        if self.wfc_toggle == 3:
            seabed_region = (0, self.wfc.grid_size[1]-1, self.wfc.grid_size[0], self.wfc.grid_size[1])
            self.wfc.enforce_region(seabed_region, (5,0))

        self.wfc.run()
        self.draw_all(refresh=self.run_animated)

    def run_draw_step(self, event=None):
        if self.wfc_toggle == 3 and self.wfc.is_start:
            seabed_region = (0, self.wfc.grid_size[1]-1, self.wfc.grid_size[0], self.wfc.grid_size[1])
            self.wfc.enforce_region(seabed_region, (5,0))
        self.wfc.run_step()
        self.draw_all()

    def open_template_builder(self):
        from template_builder import TemplateBuilder_GUI
        self.close_win()
        template_GUI = TemplateBuilder_GUI()
        template_GUI.launch()

    def launch(self):
        print('Running from WFC_GUI.launch()')
        self.run_draw()
        self.root.mainloop()
            
    
