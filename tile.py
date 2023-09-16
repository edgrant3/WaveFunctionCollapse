import math
import glob
import PIL
import json
import os
import copy
from PIL import ImageTk, Image


class Direction():
    def __init__(self, dir, opp, idx = (0,0)):
        self.dir = dir
        self.opp = opp
        self.idx = idx

    def is_inbounds(self, idx, grid_dims):   
        return (0 <= idx[0] + self.idx[0] < grid_dims[0]) and (0 <= idx[1] + self.idx[1] < grid_dims[1])

##############################################

class Tile():
    min_dim = 15
    # coords: (w, h), top left origin
    directions = {"N": Direction("N", "S", ( 0, -1 )),
                  "E": Direction("E", "W", ( 1,  0 )),
                  "S": Direction("S", "N", ( 0,  1 )),
                  "W": Direction("W", "E", (-1,  0 ))}
    
    def __init__(self, id, source_path, weight = 1, ispatch = False, img_size = None):
        self.id = id
        self.image = None
        self.image_path = None
        self.source_image_path = source_path
        self.image_size = None
        self.rot = 0
        self.num_rotations = 0
        self.weight = weight
        self.ispatch = ispatch
        self.sockets = {}

    def getID(self):
        return (self.id, self.rot)

    def rotate(self, old, rot):
        rot   = rot % 4
        dirs  = ["N", "E", "S", "W"]
        order = [(i - rot) % 4 for i in range(4)]
        for i, dir in enumerate(dirs):
            self.sockets[dir] = old.sockets[dirs[order[i]]]
    
    def resize_image(self, scale):
        img = PIL.Image.open(self.image_path)
        img.resize((scale*img.size[0], scale*img.size[1]),
                           resample = PIL.Image.NEAREST)
        self.image_size = img.size()
        img.save(self.image_path)

    def create_scaled_image(self, scale, source, dir):
        pil_img = PIL.Image.open(source)
        pil_img = pil_img.resize((scale*pil_img.size[0], scale*pil_img.size[1]), 
                                  resample = PIL.Image.NEAREST)

        resized_path = f'{dir}/{self.id}_{self.rot}.png'
        pil_img.save(resized_path)
        return resized_path, pil_img.size
    
    def create_rotated_image(self, rot, dir):
        pil_img = PIL.Image.open(self.image_path)
        rotated_path = f'{dir}/{self.id}_{rot}.png'
        pil_img.rotate(-90*rot).save(rotated_path)
        return rotated_path


##############################################
class TileSet():
    default_scale = 3
    def __init__(self, tileset_name):
        self.name = tileset_name
        self.tiles     = {} # dict: maps tileID (tile, rotation) to corresponding Tile instance
        self.idANDidx  = {} # dict: maps tileID (tile, rotation) to int value
        self.scale     = TileSet.default_scale
        self.tile_px_h = None
        self.tile_px_w = None
        self.count = 0

        self.generate()

    def set_scale(self, scale):
        self.scale = scale
        self.generate()

    def generate_error_tile(self):
        source_image_size = PIL.Image.open(self.tiles[(0, 0)].source_image_path).size
        et_img = PIL.Image.new('RGB', source_image_size, (255, 0, 255))
        et_source_path = f'assets/{self.name}/-1.png'
        et_processed_path = f"assets/{self.name}/processed_images"
        et_img.save(et_source_path)

        et =  Tile(id= -1, source_path= et_source_path)
        p, s = et.create_scaled_image(self.scale, et_source_path, et_processed_path)

        et.source_image_path = et_source_path
        et.image_path = p
        et.image_size = s
        et.image      = PIL.Image.open(p)

        self.tiles[(-1, 0)] = et

    def generate(self, printout=False):
        '''Generates TileSet from JSON with self.name filename in assets folder'''
        dir = f"assets/{self.name}"
        with open(os.path.join(dir, f'{self.name}.json')) as file:
            file_contents = file.read()
        path = os.path.join(dir, "processed_images")

        tileset_JSON = json.loads(file_contents)["tileset"]

        self.tiles.clear()

        for tile in tileset_JSON["tiles"]:
            if not tile["ignore"]:

                new_tile = Tile(tile["id"], tile["image"], tile["weight"], tile["patch_tile"])

                img_path, img_size = new_tile.create_scaled_image(self.scale, tile["image"], path)
                new_tile.image_path = img_path
                new_tile.image_size = img_size

                new_tile.sockets = tile["sockets"]
                new_tile.num_rotations = len(tile["rotations"])
                
                for rot in tile["rotations"]:
                    img_path = new_tile.create_rotated_image(rot, path)

                    rotated_tile = copy.deepcopy(new_tile)
                    rotated_tile.image = PIL.Image.open(img_path)
                    rotated_tile.image_path = img_path
                    rotated_tile.rot = rot
                    rotated_tile.rotate(new_tile, rot)

                    self.tiles[(rotated_tile.id, rotated_tile.rot)] = rotated_tile
        
        self.tile_px_w = self.tiles[(0, 0)].image_size[0]
        self.tile_px_h = self.tiles[(0, 0)].image_size[1]

        self.generate_error_tile()
        # self.tiles[(-1, 0)].sockets = self.tiles[(0, 0)].sockets
        self.count = len(list(self.tiles.keys()))    
        for idx, tileID in enumerate(self.tiles.keys()):
            self.idANDidx[tileID] = idx
            self.idANDidx[idx] = tileID    

        if printout:
            print(f'Tileset Keys (ids) ({self.count}):')
            for tile_id, tile_idx in self.idANDidx.items():
                print(f'{tile_id}: {tile_idx}')


##############################################
class waveTile():
    def __init__(self, possible_tiles = [], collapsed = False):
        self.collapsed = collapsed # a bit redundant, could just check if len(possible_tiles) == 1
        self.possible = possible_tiles # contains tuple tile_ids, initially populated with all tiles
        
##############################################