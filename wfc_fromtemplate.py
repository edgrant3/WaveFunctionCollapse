
import PIL
import json
import os
import copy
from PIL import ImageTk, Image
import numpy as np

import heapq as hq

from wfc_GUI import WFC_GUI

##############################################

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
    tile_scaling = 1
    # coords: (w, h), top left origin
    directions = {"N": Direction("N", "S", ( 0, -1 )),
                  "E": Direction("E", "W", ( 1,  0 )),
                  "S": Direction("S", "N", ( 0,  1 )),
                  "W": Direction("W", "E", (-1,  0 ))}
    
    def __init__(self, id, image_path, weight = 1, ispatch = False, img_size = None):
        self.id = id
        self.image_path = image_path
        self.image = None
        self.rot = 0
        self.num_rotations = 0
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
    def generate_error_tile(cls):
        err_path = "assets/error_tile.png"
        ET =  cls(-1, err_path, 1, False)
        ET.image = PIL.Image.open(ET.image_path)
        ET.image = ET.image.resize((cls.tile_scaling*ET.image.size[0], 
                                    cls.tile_scaling*ET.image.size[1]),
                                    resample = PIL.Image.NEAREST)
        cls.error_tile = ET
    
    @classmethod
    def resize_image(cls, tile, dir):
        pil_img = PIL.Image.open(tile["image"])
        scale = cls.tile_scaling
        pil_img = pil_img.resize((scale*pil_img.size[0], scale*pil_img.size[1]), 
                                  resample = PIL.Image.NEAREST)

        resized_path = f'{dir}/{tile["id"]}_0.png'
        pil_img.save(resized_path)
        
        return resized_path, pil_img.size

    @classmethod
    def create_rotated_image(cls, tile, rot, dir):
        pil_img = PIL.Image.open(tile.image_path)
        rotated_path = f'{dir}/{tile.id}_{rot}.png'
        pil_img.rotate(-90*rot).save(rotated_path)
        return rotated_path

    @classmethod
    def generate_tiles_JSON(cls, json_filename):
        cls.generate_error_tile()

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

                img_path, img_size = cls.resize_image(tile, path)

                new_tile = cls(tile["id"], img_path, tile["weight"], tile["patch_tile"], img_size)
                new_tile.sockets = tile["sockets"]
                new_tile.num_rotations = len(tile["rotations"])
                
                for rot in tile["rotations"]:
                    img_path = cls.create_rotated_image(new_tile, rot, path)
                    # rotated_tile = cls(new_tile.id, img)
                    rotated_tile = copy.deepcopy(new_tile)
                    rotated_tile.image_path = img_path
                    rotated_tile.image = PIL.Image.open(img_path)
                    # rotated_tile.image = ImageTk.PhotoImage(rotated_tile.image)
                    rotated_tile.rot = rot
                    rotated_tile.rotate(new_tile, rot)

                    tiles[(rotated_tile.id, rotated_tile.rot)] = rotated_tile

                    if new_tile.ispatch:
                        patch_tile_ids.append((rotated_tile.id, rotated_tile.rot))
                    else:
                        tile_ids.append((rotated_tile.id, rotated_tile.rot))
                        
        cls.error_tile.sockets = tiles[(0, 0)].sockets
        tiles[(-1, 0)] = cls.error_tile                        

        return tiles, tile_ids, patch_tile_ids

##############################################

class waveTile():
    def __init__(self, distribution=[], possible=[], collapsed = None):
        self.distribution = distribution
        self.collapsed = collapsed # tuple id (id, rot) of collapsed tile when collapsed
        self.possible = possible # to be replaced with np.array distribution OR convert to binary mask
        self.entropy = np.inf

    def compute_entropy(self):
        val_array = self.distribution * self.possible
        sum = np.sum(val_array)

        if sum == 0:
            self.entropy = np.inf
            return np.inf
        
        val_array = val_array / sum
        entropy = 0.0
        for val in val_array:
            if val != 0:
                entropy -= val * np.log(val)

        self.entropy = entropy
        return entropy
        
##############################################
class WFC():
    seed = None
    def __init__(self, grid_size, tiles, tile_ids, patch_ids, template=None, win=None, use_sockets=True):

        self.rng = self.init_rng()
        self.use_sockets = use_sockets
        self.num_uncollapsed = 0 # number of instantiated WaveTiles that have not been collapsed

        self.grid_size = grid_size
        self.tiles = tiles #contains both normal tiles and patch tiles
        self.tile_ids = tile_ids
        self.patch_ids = patch_ids
        self.n_tiles = len(list(self.tiles.keys()))

        self.tile2idx = {tile_id: idx for idx, tile_id in enumerate(self.tiles.keys())}
        self.idx2tile = {idx: tile_id for idx, tile_id in enumerate(self.tiles.keys())}

        self.tile_size = self.tiles[self.tile_ids[0]].img_size
        self.win_size = (self.tile_size[0] * self.grid_size[0], self.tile_size[1] * self.grid_size[1])

        if win:
            self.win = win
        else:
            self.win = WFC_GUI.fromTileGrid(self.tiles[self.tile_ids[0]].img_size, self.grid_size)

        self.entropy_map = np.full((self.win.grid_dims[0], self.win.grid_dims[1]), np.inf) # WAS: np.ones((self.win.grid_dims[0], self.win.grid_dims[1])) * self.n_tiles
        self.template = template

        self.relative_neighbor_idxs, self.kernel_idxs = self.get_neighbor_relative_idxs()

        self.tile_map    = {}  
        self.start_idx = (0,0)
        self.start_tile = (0,0)

    def get_neighbor_relative_idxs(self):
        result = []
        kernel_size = self.template['analyzed_template']['kernel_size']
        half_kernel = (kernel_size[0] // 2, kernel_size[1] // 2)

        for row in range(-half_kernel[0], half_kernel[0] + 1):
            for col in range(-half_kernel[1], half_kernel[1] + 1):
                    result.append((row, col))

        kernel_idxs = [(i, j) for j in range(self.template['analyzed_template']['kernel_size'][0]) 
                                   for i in range(self.template['analyzed_template']['kernel_size'][1])]

        return result, kernel_idxs
    
    @classmethod
    def set_seed(cls, seed):
        cls.seed = seed

    def init_rng(self):
        if WFC.seed:
            self.rng = np.random.default_rng(WFC.seed)
        else:
            self.rng = np.random.default_rng()
    
    @staticmethod
    def unstring_keys(dict):
        return {tuple(map(int, k.replace('(','').replace(')','').split(','))): v for k, v in dict.items()}

    @staticmethod
    def list_to_numpy_items(dict):
        return {k: np.array(v) for k, v in dict.items()}

    @classmethod
    def load_template(cls, template_path):
        with open(template_path) as f:
            template = json.load(f)      
            template['data'] =                      cls.unstring_keys(template['data'])
            template['analyzed_template']['data'] = cls.list_to_numpy_items(
                                                    cls.unstring_keys(template['analyzed_template']['data']))
        return template
    
    def use_template(self, template):
        self.template = template
    
    def enforce_region(self, region, tile_id):
        region_ws = range(region[0], region[2])
        region_hs = range(region[1], region[3])
        for w_idx in region_ws:
            for h_idx in region_hs:
                idx = (w_idx, h_idx)
                self.tile_map[idx] = waveTile(collapsed=tile_id)
                self.entropy_map[idx] = np.inf
                self.update_neighbors(idx)
        print('\nEnforced region: ', region)
        
    def is_inbounds(self, idx):
        return (idx[0] >= 0 and idx[0] < self.grid_size[0] and
                idx[1] >= 0 and idx[1] < self.grid_size[1])

    def get_neighbor_idxs(self, idx):
        result = []
        for rel_idx in self.relative_neighbor_idxs:
            neighbor_idx = (idx[0] + rel_idx[0], idx[1] + rel_idx[1])
            result.append(neighbor_idx)
        return result

    def check_sockets(self, idx):
        collapsed_tile = self.tiles[self.tile_map[idx].collapsed]
        for dir in ["N", "E", "S", "W"]:
            if Tile.directions[dir].is_inbounds(idx, self.grid_size):
                socket  = collapsed_tile.sockets[dir]
                opp     = Tile.directions[dir].opp
                dir_idx = Tile.directions[dir].idx
                neighbor_idx = (idx[0] + dir_idx[0], idx[1] + dir_idx[1])

                # Assume already in self.tile_map
                if self.tile_map[neighbor_idx].collapsed == None:
                    self.tile_map[neighbor_idx].possible = [x if socket == self.tiles[self.idx2tile[idx]].sockets[opp][::-1]
                                                              else 0 for idx, x in enumerate(self.tile_map[neighbor_idx].possible)]
                    
                    self.entropy_map[neighbor_idx] = self.tile_map[neighbor_idx].compute_entropy()

    def update_neighbors(self, idx):
        collapsed_tile_id = self.tile_map[idx].collapsed
        neighbor_idxs  = self.get_neighbor_idxs(idx)

        for i, neighbor_idx in enumerate(neighbor_idxs):
            if not self.is_inbounds(neighbor_idx):
                continue

            if neighbor_idx not in self.tile_map:
                self.tile_map[neighbor_idx] = waveTile(distribution=np.zeros(self.n_tiles), possible=np.ones(self.n_tiles))
                self.num_uncollapsed += 1

            if self.tile_map[neighbor_idx].collapsed != None:
                continue

            kernel_idx = self.kernel_idxs[i]

            # if self.use_sockets:
            #     print("\nTODO: integrate sockets into template version!!!\n")
            if not collapsed_tile_id in self.template['analyzed_template']['data']:
                continue
            self.tile_map[neighbor_idx].distribution += self.template['analyzed_template']['data'][collapsed_tile_id][:, kernel_idx[0], kernel_idx[1]]
            self.entropy_map[neighbor_idx] = self.tile_map[neighbor_idx].compute_entropy() # returns AND sets entropy for wavetile

        if self.use_sockets and collapsed_tile_id in self.template['analyzed_template']['data']:
            self.check_sockets(idx)

    def collapse(self, start=False):
        if start: # First iteration
            self.tile_map[self.start_idx] = waveTile(collapsed=self.start_tile)
            self.update_neighbors(self.start_idx)
            return self.start_idx, False
        
        if self.num_uncollapsed == 0:
            print("All tiles collapsed!")
            return None, True

        min_idx = np.unravel_index(np.argmin(self.entropy_map), self.entropy_map.shape)
        target_tile = self.tile_map[min_idx]
        # min_entropy = self.entropy_map[min_idx]

        if target_tile.collapsed != None:
            # Handles enforced region tiles
            #print(f'Already collapsed tile at {min_idx} with id {target_tile.collapsed}: left: {self.num_uncollapsed}')
            self.num_uncollapsed -= 1
            return min_idx, False

        probs = target_tile.distribution * target_tile.possible
        probs_sum = np.sum(probs)
        chosen_idx = 0
        if probs_sum != 0:
            probs = probs / probs_sum
            # print(f'Entropy: {min_entropy}, min_idx: {min_idx}, tiles left: {self.num_uncollapsed}')
            chosen_idx = np.random.choice(range(len(probs)), 1, p=probs)[0]
        else:
            #error tile
            chosen_idx = self.tile2idx[(-1,0)]

        target_tile.collapsed = self.idx2tile[chosen_idx]
        # print('taget_tile.collapsed ', target_tile.collapsed)
        self.num_uncollapsed -= 1
        self.entropy_map[min_idx] = np.inf

        self.update_neighbors(min_idx)

        return min_idx, False
    
    def draw(self, idx, refresh = False):
        # print(f'Drawing tile at {idx} with id {self.tile_map[idx].collapsed}')
        if self.tile_map[idx].collapsed is None:
            img = self.tiles[(-1,0)].image
        else:
            img = self.tiles[self.tile_map[idx].collapsed].image
        size = self.tiles[self.tile_ids[0]].img_size
        x = int(idx[0]*size[0])
        y = int(idx[1]*size[1])
        self.win.insert_image(img, x, y)
        if refresh:
            self.win.refresh_canvas()
            self.win.root.update()

    def draw_all(self, refresh = False):
        self.win.create_canvas(self.win_size[0], self.win_size[1])
        for idx in self.tile_map:
            self.draw(idx, refresh)
        self.win.refresh_canvas()
        self.win.root.update()

    def run(self):
        self.collapse(start=True)
        while True:
                collapsed_idx, terminate = self.collapse()
                if terminate:
                    break
    
##############################################
#############------ MAIN ------###############
##############################################

# TODO LIST #
# - Refactor collapse()
# - Fix GUI keypress callback to accept input other than Esc
# - Add neighbor affinity mechanic to increase probability of certain tiles being neighbors
# - - possibly through input image analysis

# NOTE: adding more tiles with same sockets increases the entropy of those kind of regions
#       -- meaning in the ocean map, it solves the ocean first and then fills in islands,
#       -- but the island borders in that case may be unsolvable!!!


if __name__ == "__main__":

    # grid_dims = (500, 300) # ~ 1min per solve
    # grid_dims = (80, 55) # < 1s per solve
    grid_dims = (45, 30)
    Tile.tile_scaling = 2
    run_animated = False
    save_result = False

    t1_set = "default_tile_set"
    t2_set = "village_tile_set2"
    t3_set  = "ocean_tile_set"
    t4_set  = "seaweed_set"

    Tile.generate_error_tile()
    t1_dict, t1, pt1 = Tile.generate_tiles_JSON(t1_set)
    t2_dict, t2, pt2 = Tile.generate_tiles_JSON(t2_set)
    t3_dict, t3, pt3 = Tile.generate_tiles_JSON(t3_set)
    t4_dict, t4, pt4 = Tile.generate_tiles_JSON(t4_set)

    t1_template = WFC.load_template(f"assets/{t1_set}/{t1_set}_template.json")
    t2_template = WFC.load_template(f"assets/{t2_set}/{t2_set}_template.json")
    t3_template = WFC.load_template(f"assets/{t3_set}/{t3_set}_template.json")
    t4_template = WFC.load_template(f"assets/{t4_set}/{t4_set}_template.json")

    # print(t1_template['analyzed_template']['kernel_size'])

    name_dict = {0: t1_set, 1: t2_set, 2: t3_set, 3: t4_set}
    t_dict = {0: (t1_dict, t1, pt1, t1_template), 
              1: (t2_dict, t2, pt2, t2_template),
              2: (t3_dict, t3, pt3, t3_template),
              3: (t4_dict, t4, pt4, t4_template)}
    
    toggle = 0
    wfc = WFC(grid_dims, t_dict[toggle][0], t_dict[toggle][1], t_dict[toggle][2], template=t_dict[toggle][3])   
    first_run = True
    while(True):
        print(f"\nRunning {name_dict[toggle]}")
        print(f'with kernel size {t_dict[toggle][3]["analyzed_template"]["kernel_size"]}')
        wfc = WFC(wfc.grid_size, t_dict[toggle][0], t_dict[toggle][1], t_dict[toggle][2], template=t_dict[toggle][3], win=wfc.win)
        
        if toggle == 3:
            seabed_region = (0, grid_dims[1]-1, grid_dims[0], grid_dims[1])
            wfc.enforce_region(seabed_region, (5,0))

        wfc.run()
        if first_run:
            first_run = False
        else:
            wfc.win.wait_for_keypress()
            # time.sleep(1.25)
            # pass
        wfc.draw_all(refresh=run_animated)

        if save_result:
            wfc.win.img.save("output.png")

        toggle = (toggle + 1) % len(t_dict.keys())



