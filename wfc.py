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

    def is_inbounds(self, idx, grid_dims):   
        return (0 <= idx[0] + self.idx[0] < grid_dims[0]) and (0 <= idx[1] + self.idx[1] < grid_dims[1])

##############################################

class Tile():
    min_dim = 30
    # coords: (w, h), top left origin
    directions = {"N": direction("N", "S", ( 0, -1 )),
                  "E": direction("E", "W", ( 1,  0 )),
                  "S": direction("S", "N", ( 0,  1 )),
                  "W": direction("W", "E", (-1,  0 ))}
    
    def __init__(self, id, image, weight = 1, ispatch = False, img_size = None):
        self.id = id
        self.image = image
        self.rot = 0
        self.weight = weight
        self.ispatch = ispatch
        self.sockets = {}
        self.img_size = img_size

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

        resized_path = f'{dir}/{tile["id"]}_0.png'
        pil_img.save(resized_path)
        
        return resized_path, pil_img.size

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
        tiles   = {}
        tile_ids = []
        patch_tile_ids = []
        for tile in tileset["tiles"]:
            if not tile["ignore"]:

                img, img_size = cls.resize_image(tile, path)

                new_tile = cls(tile["id"], img, tile["weight"], tile["patch_tile"], img_size)
                new_tile.sockets = tile["sockets"]
                
                for rot in tile["rotations"]:
                    img = cls.create_rotated_image(new_tile, rot, path)
                    # rotated_tile = cls(new_tile.id, img)
                    rotated_tile = copy.deepcopy(new_tile)
                    rotated_tile.image = img
                    rotated_tile.rot = rot
                    rotated_tile.rotate(new_tile, rot)

                    tiles[(rotated_tile.id, rotated_tile.rot)] = rotated_tile

                    if new_tile.ispatch:
                        patch_tile_ids.append((rotated_tile.id, rotated_tile.rot))
                    else:
                        tile_ids.append((rotated_tile.id, rotated_tile.rot))
                        

        return tiles, tile_ids, patch_tile_ids

##############################################

class waveTile():
    def __init__(self, possible_tiles = [], collapsed = False):
        self.collapsed = collapsed # a bit redundant, could just check if len(possible_tiles) == 1
        self.possible = possible_tiles
        
##############################################
class WFC():
    def __init__(self, grid_size, tiles, tile_ids, patch_ids, win = None):
        self.grid_size = grid_size
        self.tiles = tiles #contains both normal tiles and patch tiles
        self.tile_ids = tile_ids
        self.patch_ids = patch_ids
        self.n_tiles = len(self.tile_ids)

        if win:
            self.win = win
        else:
            self.win = GraphicsWindow.fromTileGrid(self.tiles[self.tile_ids[0]].img_size, self.grid_size)

        self.entropy_map = np.ones((self.win.grid_dims[0], self.win.grid_dims[1])) * self.n_tiles
        self.tile_map    = {}  
        self.start_idx = (0,0)
    

    def update_neighbors(self, idx):
        collapsed_tile = self.tiles[self.tile_map[idx].possible[0]]

        for dir in ["N", "E", "S", "W"]:
            if Tile.directions[dir].is_inbounds(idx, self.win.grid_dims):
                socket  = collapsed_tile.sockets[dir]
                opp     = Tile.directions[dir].opp
                dir_idx = Tile.directions[dir].idx
                neighbor_idx = (idx[0] + dir_idx[0], idx[1] + dir_idx[1])

                if neighbor_idx not in self.tile_map:
                    # self.tile_map[neighbor_idx] = waveTile([*range(self.n_tiles)], False)
                    self.tile_map[neighbor_idx] = waveTile(self.tile_ids, False)

                if not self.tile_map[neighbor_idx].collapsed:
                    self.tile_map[neighbor_idx].possible = [x for x in self.tile_map[neighbor_idx].possible if socket == self.tiles[x].sockets[opp][::-1]]
                    self.entropy_map[neighbor_idx] = len(self.tile_map[neighbor_idx].possible)

    def check_neighbors(self, idx, id):
        candidate_tile = self.tiles[id]

        for dir in ["N", "E", "S", "W"]:
            if Tile.directions[dir].is_inbounds(idx, self.win.grid_dims):

                socket  = candidate_tile.sockets[dir]
                opp     = Tile.directions[dir].opp
                dir_idx = Tile.directions[dir].idx
                neighbor_idx = (idx[0] + dir_idx[0], idx[1] + dir_idx[1])

                if neighbor_idx in self.tile_map:
                    if self.tile_map[neighbor_idx].collapsed:
                        if socket != self.tiles[self.tile_map[neighbor_idx].possible[0]].sockets[opp]:
                            return False
                    else:
                        if socket not in [self.tiles[x].sockets[opp] for x in self.tile_map[neighbor_idx].possible]:
                            return False
        return True

    def collapse(self):
        min_entropy = np.min(self.entropy_map)
        min_idxs = np.where(self.entropy_map == min_entropy)

        r1 = np.random.randint(0, len(min_idxs[0]))
        tile_idx = (min_idxs[0][r1], min_idxs[1][r1])

        if min_entropy == self.n_tiles:
            #first iteration
            tile_idx = self.start_idx #(0,0)
            self.tile_map[tile_idx] = waveTile([(0,0)], True)
            self.entropy_map[tile_idx] = self.n_tiles + 1

        elif min_entropy == self.n_tiles + 1:
            # All tiles have collapsed
            return tile_idx, True
        
        else :
            # print(len(self.tile_map[tile_idx].possible))
            options = self.tile_map[tile_idx].possible
            # print(options)
            num_options = len(options)
            if num_options != 0:
                # if there is a viable tile, choose one at random from weighted distribution
                prob = [self.tiles[t].weight for t in options] 
                prob /= np.sum(prob)
                    
                options_idx = range(len(options))
                chosen_idx = np.random.choice(options_idx, 1, p=prob)[0]
                self.tile_map[tile_idx].possible = [options[chosen_idx]]
                
                # r2 = np.random.randint(0, len(options))
                # self.tile_map[tile_idx].possible = [options[r2]]
            else:
                #never here...
                # print("here")
                viable_patches = []
                for patch_id in self.patch_ids:
                    if self.check_neighbors(tile_idx, patch_id):
                        viable_patches.append(patch_id)

                if viable_patches:
                    if len(viable_patches) == 1:
                        self.tile_map[tile_idx].possible = [viable_patches[0]]
                    else:
                        prob = [self.tiles[t].weight for t in viable_patches] 
                        prob /= np.sum(prob)

                        options_idx = range(len(viable_patches))
                        chosen_idx = np.random.choice(options_idx, 1, p=prob)[0]
                        self.tile_map[tile_idx].possible = [viable_patches[chosen_idx]]
                else:
                    print("\nNo viable patch Tiles: completely unsolvable!!!\n")
                    self.tile_map[tile_idx].possible = [(0, 0)]
                
            self.tile_map[tile_idx].collapsed = True
            self.entropy_map[tile_idx] = self.n_tiles + 1

        self.update_neighbors(tile_idx)
        return tile_idx, False
    
    def draw(self, idx):
        img_path = self.tiles[self.tile_map[idx].possible[0]].image
        size = self.tiles[self.tile_ids[0]].img_size
        new_tile_img = graphics.Image(Point(idx[0]*size[0] + size[0] / 2 - size[0] % 2, 
                                            idx[1]*size[1] + size[1] / 2 - size[0] % 2), 
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
# - Add neighbor affinity mechanic to increase probability of certain tiles being neighbors
# - - possibly through input image analysis

# NOTE: adding more tiles with same sockets increases the entropy of those kind of regions
#       -- meaning in the ocean map, it solves the ocean first and then fills in islands,
#       -- but the island borders in that case may be unsolvable!!!

if __name__ == "__main__":

    village = "village_tile_set2"
    default = "default_tile_set"
    ocean  = "ocean_tile_set"

    Tile.min_dim = 15
    t1_dict, t1, pt1 = Tile.generate_tiles_JSON(default)
    t2_dict, t2, pt2 = Tile.generate_tiles_JSON(village)
    t3_dict, t3, pt3 = Tile.generate_tiles_JSON(ocean)

    t_dict = {0: (t1_dict, t1, pt1), 
              1: (t2_dict, t2, pt2),
              2: (t3_dict, t3, pt3)}

    # self, grid_size, tiles, tile_ids, patch_ids, win = None
    wfc = WFC((45, 45), tiles=t1_dict, tile_ids=t1, patch_ids = pt1)

    toggle = 0
    while(True):
        wfc.run()

        # time.sleep(2.0)
        wfc.win.window.getMouse()
        
        toggle = (toggle + 1) % len(t_dict.keys())

        wfc = WFC(wfc.grid_size, t_dict[toggle][0], t_dict[toggle][1], t_dict[toggle][2], wfc.win)

        wfc.win.clear()

        time.sleep(0.25)

    wfc.win.window.getMouse()
    wfc.win.window.close()


