import math
import glob
import PIL
import json
import os
import copy
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
        self.window.setBackground("black")
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

##############################################

class Tile():
    min_dim = 30
    img_size = None
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

    def rotate(self, old, rot):
        rot = rot % 4
        if rot == 1:
            self.sockets["N"] = old.sockets["W"]
            self.sockets["E"] = old.sockets["N"]
            self.sockets["S"] = old.sockets["E"]
            self.sockets["W"] = old.sockets["S"]
        elif rot == 2:
            self.sockets["N"] = old.sockets["S"]
            self.sockets["E"] = old.sockets["W"]
            self.sockets["S"] = old.sockets["N"]
            self.sockets["W"] = old.sockets["E"]
        elif rot == 3:
            self.sockets["N"] = old.sockets["E"]
            self.sockets["E"] = old.sockets["S"]
            self.sockets["S"] = old.sockets["W"]
            self.sockets["W"] = old.sockets["N"]

    @classmethod
    def resize_image(cls, tile, dir):
        pil_img = PIL.Image.open(tile["image"])
        scale = math.ceil( float(cls.min_dim) / float(min(pil_img.size)) )
        pil_img = pil_img.resize((scale*pil_img.size[0], scale*pil_img.size[1]), 
                                  resample = PIL.Image.NEAREST)
        cls.img_size = pil_img.size

        resized_path = f'{dir}/{tile["id"]}_0.png'
        pil_img.save(resized_path)
        
        return resized_path

    @classmethod
    def create_rotated_image(cls, tile, rot, dir):
        pil_img = PIL.Image.open(tile.image)
        rotated_path = f'{dir}/{tile.id}_{rot}.png'
        pil_img.rotate(-90*rot).save(rotated_path)
        return rotated_path

    @classmethod
    def generate_tiles_JSON(cls, json_filename):
        path = f"assets/{json_filename}"
        with open(os.path.join(path, json_filename + ".json")) as file:
            file_contents = file.read()

        path = os.path.join(path, "processed_images")

        tileset = json.loads(file_contents)["tileset"]
        tiles   = []
        for tile in tileset["tiles"]:
            if not tile["ignore"]:
                # TODO: make weight affect selection probability
                # instead of the inefficient method below of adding redundant tiles
                for i in range(tile["weight"]):
                    img = cls.resize_image(tile, path)
                    new_tile = cls(tile["id"], img)
                    new_tile.sockets = tile["sockets"]
                    tiles.append(new_tile)

                    for rot in tile["rotations"]:
                        img = cls.create_rotated_image(new_tile, rot, path)
                        rotated_tile = cls(new_tile.id, img)
                        rotated_tile.sockets = copy.deepcopy(new_tile.sockets)
                        rotated_tile.rot = rot
                        rotated_tile.rotate(new_tile, rot)
                        tiles.append(rotated_tile)

        return tiles

##############################################

class waveTile():
    def __init__(self, possible_tiles = [], collapsed = False):
        self.collapsed = collapsed
        self.possible = possible_tiles
        
##############################################
class WFC():
    def __init__(self, grid_size, tiles, win = None):
        self.grid_size = grid_size
        self.tiles = tiles
        self.n_tiles = len(self.tiles)
        if win:
            self.win = win
        else:
            self.win = GraphicsWindow.fromTileGrid(Tile.img_size, self.grid_size)
        self.entropy_map = np.ones((self.win.grid_dims[0], self.win.grid_dims[1])) * self.n_tiles
        self.tile_map    = {}  
        self.start_idx = (0,0)
    
    def update_neighbors(self, idx):
        collapsed_tile = self.tiles[self.tile_map[idx].possible[0]]

        for dir in ["N", "E", "S", "W"]:
            if Tile.directions[dir].is_valid(idx, self.win.grid_dims):
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
        
        new_tile_img.draw(self.win.window)

    def run(self, tileset = None):
        while True:
                collapsed_idx, terminate = self.collapse()
                self.draw(collapsed_idx)
                # time.sleep(0.00001)
                if terminate:
                    break

##############################################
#############------ MAIN ------###############
##############################################

# TODO LIST #
# - Fix the window size needing to be square
# - Add more sophisticated tile weighting (currently just adds redundant tiles)
# - Add neighbor affinity mechanic to increase probability of certain tiles being neighbors
# - Add patch tile functionality to handle unsolvable cases OR another solution

if __name__ == "__main__":

    village = "village_tile_set"
    default = "default_tile_set"

    Tile.min_dim = 30
    t1 = Tile.generate_tiles_JSON(default)
    t2 = Tile.generate_tiles_JSON(village)
    print("Village tile count: ", len(t2))
    t_dict = {0: t1, 1: t2}

    wfc = WFC((25,25), t1)

    toggle = 0
    while(True):
        wfc.run()

        # time.sleep(2.0)
        wfc.win.window.getMouse()
        
        toggle = (toggle + 1) % 2

        wfc = WFC(wfc.grid_size, t_dict[toggle], wfc.win)

        wfc.win.clear()

        time.sleep(0.25)

    wfc.win.window.getMouse()
    wfc.win.window.close()


