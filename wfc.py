import math
import glob
import PIL
from PIL import Image
import numpy as np
import time

import graphics
from graphics import *


##############################################
class GraphicsWindow():
    max_width = 2000
    max_height = 2000
    min_width = 500
    min_height = 500

    def __init__(self, pix_width, pix_height, grid_dims = None):
        self.width  = pix_width
        self.height = pix_height
        self.window = GraphWin("Wave Function Collapse", self.width, self.height)
        self.window.setBackground("red")
        self.grid_dims = grid_dims

    @classmethod
    def fromTileGrid(cls, tile_dims, grid_dims):
        return cls(tile_dims[0] * grid_dims[0], tile_dims[1] * grid_dims[1], grid_dims)
    
    def clear(self):
        for item in self.window.items[:]:
            item.undraw()
        self.window.update()

##############################################

class direction():
    def __init__(self, dir, opp, idx = (0,0)):
        self.dir = dir
        self.opp = opp
        self.idx = idx

    def is_valid(self, idx, grid_dims):        
        return (0 <= idx[0] + self.idx[0] < grid_dims[0]) and (0 <= idx[1] + self.idx[1] < grid_dims[1])


class Tile():
    min_dim = 30
    img_size = None
    rotate_idxs = [1]
    directions = {"N": direction("N", "S", (-1, 0)),
                  "E": direction("E", "W", ( 0, 1)),
                  "S": direction("S", "N", ( 1, 0)),
                  "W": direction("W", "E", ( 0,-1))}
    
    def __init__(self, id, image, img_size = None):
        self.id = id
        self.image = image
        self.img_size = img_size
        self.rot = 0
        self.sockets = {}

    def rotate(self, rot):
        rot = rot % 4
        new_Tile = Tile(self.id, f"assets/resized_assets/{self.id}_{rot}.png")
        new_Tile.rot = rot
        
        if rot == 1:
            new_Tile.sockets["N"] = self.sockets["W"]
            new_Tile.sockets["E"] = self.sockets["N"]
            new_Tile.sockets["S"] = self.sockets["E"]
            new_Tile.sockets["W"] = self.sockets["S"]
        elif rot == 2:
            new_Tile.sockets["N"] = self.sockets["S"]
            new_Tile.sockets["E"] = self.sockets["W"]
            new_Tile.sockets["S"] = self.sockets["N"]
            new_Tile.sockets["W"] = self.sockets["E"]
        elif rot == 3:
            new_Tile.sockets["N"] = self.sockets["E"]
            new_Tile.sockets["E"] = self.sockets["S"]
            new_Tile.sockets["S"] = self.sockets["W"]
            new_Tile.sockets["W"] = self.sockets["N"]
        
        return new_Tile
        
    @classmethod
    def load_images(cls):
        cls.resize_images()
        cls.create_rotated_images()
        return glob.glob("assets/resized_assets/*.png")
    
    @classmethod
    def resize_images(cls):
        files = glob.glob("assets/*.png")
        pil_img = None
        for i, img in enumerate(files):
            pil_img = PIL.Image.open(img)
            scale = math.ceil( float(Tile.min_dim) / float(min(pil_img.size)) )
            pil_img = pil_img.resize((scale*pil_img.size[0], scale*pil_img.size[1]))
            pil_img.save(f"assets/resized_assets/{i}_0.png")

        cls.img_size = pil_img.size
        return pil_img.size
    
    @classmethod
    def create_rotated_images(cls):
        files = glob.glob("assets/resized_assets/*.png")
        pil_img = None
        for i, img in enumerate(files):
            if i in cls.rotate_idxs:
                pil_img = PIL.Image.open(img)
                pil_img.rotate(-90).save(f"assets/resized_assets/{i}_1.png")
                pil_img.rotate(-180).save(f"assets/resized_assets/{i}_2.png")
                pil_img.rotate(-270).save(f"assets/resized_assets/{i}_3.png")
    
    @classmethod    
    def generate_tiles(cls):
        images = cls.load_images()
        tiles = []
        for i, img in enumerate(images):
            new_tile = cls(i, img)
            if i == 0:
                new_tile.sockets["N"] = "AAA"
                new_tile.sockets["E"] = "AAA"
                new_tile.sockets["S"] = "AAA"
                new_tile.sockets["W"] = "AAA"
                tiles.append(new_tile)
            elif i == 1:
                new_tile.sockets["N"] = "ABA"
                new_tile.sockets["E"] = "ABA"
                new_tile.sockets["S"] = "AAA"
                new_tile.sockets["W"] = "ABA"
                tiles.append(new_tile)

                for k in range(1, 4):
                    rotated_tile = new_tile.rotate(k)
                    tiles.append(rotated_tile)
            
        return tiles
    
class waveTile():
    def __init__(self, possible_tiles = [], collapsed = False):
        self.collapsed = collapsed
        self.possible = possible_tiles
        
##############################################
class WFC():
    def __init__(self, window):
        self.tiles  = Tile.generate_tiles()
        self.n_tiles = len(self.tiles)
        self.window = window
        self.entropy_map = np.ones((self.window.grid_dims[0], self.window.grid_dims[1])) * self.n_tiles
        self.tile_map    = {}  
        self.start_idx = (0,0)
    
    def update_neighbors(self, idx):
        collapsed_tile = self.tiles[self.tile_map[idx].possible[0]]

        for dir in ["N", "E", "S", "W"]:
            if Tile.directions[dir].is_valid(idx, self.window.grid_dims):
                socket  = collapsed_tile.sockets[dir]
                opp     = Tile.directions[dir].opp
                dir_idx = Tile.directions[dir].idx
                neighbor_idx = (idx[0] + dir_idx[0], idx[1] + dir_idx[1])

                if neighbor_idx not in self.tile_map:
                    self.tile_map[neighbor_idx] = waveTile([*range(self.n_tiles)], False)

                if not self.tile_map[neighbor_idx].collapsed:
                    self.tile_map[neighbor_idx].possible = [x for x in self.tile_map[neighbor_idx].possible if socket == self.tiles[x].sockets[opp]]
                    self.entropy_map[neighbor_idx] = len(self.tile_map[neighbor_idx].possible)
        

    def collapse(self):
        min_entropy = np.min(self.entropy_map)
        min_idxs = np.where(self.entropy_map == min_entropy)

        r1 = np.random.randint(0, len(min_idxs[0]))
        tile_idx = (min_idxs[0][r1], min_idxs[1][r1])

        if min_entropy == self.n_tiles:
            #first iteration
            tile_idx = self.start_idx #(0,0)
            self.tile_map[tile_idx] = waveTile([1], True)
            self.entropy_map[tile_idx] = self.n_tiles + 1

        elif min_entropy == self.n_tiles + 1:
            return tile_idx, True
        
        else :
            # print(len(self.tile_map[tile_idx].possible))
            if len(self.tile_map[tile_idx].possible) != 0:
                r2 = np.random.randint(0, len(self.tile_map[tile_idx].possible))
                self.tile_map[tile_idx].possible = [self.tile_map[tile_idx].possible[r2]]
            else:
                ### TODO: remove this cheap hack
                self.tile_map[tile_idx].possible = [0]
                
            self.tile_map[tile_idx].collapsed = True
            self.entropy_map[tile_idx] = self.n_tiles + 1

        self.update_neighbors(tile_idx)
        return tile_idx, False
    
    def draw(self, idx):
        img_path = self.tiles[self.tile_map[idx].possible[0]].image
        new_tile_img = graphics.Image(Point(idx[1]*Tile.img_size[1] + Tile.img_size[1] / 2 - 1, 
                                            idx[0]*Tile.img_size[0] + Tile.img_size[0] / 2 - 1), 
                                            img_path)
        
        new_tile_img.draw(self.window.window)

    def run(self):
        while True:
                collapsed_idx, terminate = self.collapse()
                self.draw(collapsed_idx)
                # time.sleep(0.00001)
                if terminate:
                    break

        # self.window.window.getMouse()
        time.sleep(0.5)
        self = WFC(self.window)
        self.window.clear()
        # self.window.window.getMouse()
        time.sleep(0.5)
        self.run()

##############################################
#############------ MAIN ------###############
##############################################

if __name__ == "__main__":

    Tile.min_dim = 15
    new_dims = Tile.resize_images()
    # TODO: fix it needing square dims
    win = GraphicsWindow.fromTileGrid(new_dims, (45,45))

    wfc = WFC(win)
    # wfc.start_idx = wfc.window.grid_dims[0]//2, wfc.window.grid_dims[1]//2
    wfc.run()

    win.window.getMouse()
    win.window.close()


