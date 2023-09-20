
import PIL
import json
import os
import copy
from PIL import ImageTk, Image
import numpy as np

import heapq as hq

from wfc_GUI import WFC_GUI
from tile import Tile, TileSet, waveTileAdvanced
from template import Template


class WFC():
    seed = None
    def __init__(self, grid_size, template, win=None, use_sockets=True, allow_offtemplate_matches=False):

        self.template = template
        self.use_sockets = use_sockets
        self.allow_offtemplate_matches = allow_offtemplate_matches
        self.num_uncollapsed = 0 # number of instantiated WaveTiles that have not been collapsed

        self.grid_size = grid_size
        self.win_size = (self.template.tileset.tile_px_w * grid_size[0], self.template.tileset.tile_px_h * grid_size[1])
        # self.win = win if win else WFC_GUI.fromTileGrid((self.template.tileset.tile_px_w, self.template.tileset.tile_px_h), grid_size)

        self.entropy_map = np.full(grid_size, np.inf) # WAS: np.ones((self.win.grid_dims[0], self.win.grid_dims[1])) * self.n_tiles
        self.tile_map    = {}  
        self.start_idx = (0,0)
        self.start_tile = (0,0)

        self.relative_neighbor_idxs, self.kernel_idxs = self.template.analyzer.get_neighbor_relative_idxs()
        # print(f'EVAN: len of rel neighbors: {len(self.relative_neighbor_idxs)}')
        # print(f'EVAN: len of kernel_idxs  : {len(self.kernel_idxs)}')

        self.init_rng()
        self.region_enforced = False
    
    @classmethod
    def set_seed(cls, seed):
        print('setting seed in WFC')
        cls.seed = seed

    def clear_data(self):
        self.entropy_map = np.full(self.grid_size, np.inf) # WAS: np.ones((self.win.grid_dims[0], self.win.grid_dims[1])) * self.n_tiles
        self.tile_map.clear() 

    def init_rng(self):
        if WFC.seed is not None:
            self.rng = np.random.default_rng(WFC.seed)
        else:
            self.rng = np.random.default_rng()

    @staticmethod
    def list_to_numpy_items(dict):
        return {k: np.array(v) for k, v in dict.items()}
    
    def use_template(self, template):
        self.template = template
    
    def enforce_region(self, region, tile_id):
        self.region_enforced = True
        region_ws = range(region[0], region[2])
        region_hs = range(region[1], region[3])
        for w_idx in region_ws:
            for h_idx in region_hs:
                idx = (w_idx, h_idx)
                self.tile_map[idx] = waveTileAdvanced(collapsed=tile_id)
                self.entropy_map[idx] = np.inf

        for w_idx in region_ws:
            for h_idx in region_hs:
                idx = (w_idx, h_idx)
                self.update_neighbors(idx)
        
    def is_inbounds(self, idx):
        return (idx[0] >= 0 and idx[0] < self.grid_size[0] and
                idx[1] >= 0 and idx[1] < self.grid_size[1])

    def check_sockets(self, idx):
        collapsed_tile = self.template.tileset.tiles[self.tile_map[idx].collapsed]
        for dir in ["N", "E", "S", "W"]:
            if not Tile.directions[dir].is_inbounds(idx, self.grid_size):
                continue

            socket  = collapsed_tile.sockets[dir]
            opp     = Tile.directions[dir].opp
            dir_idx = Tile.directions[dir].idx
            neighbor_idx = (idx[0] + dir_idx[0], idx[1] + dir_idx[1])

            # Assume already in self.tile_map because this is called @ end of update_neighbors()
            if self.tile_map[neighbor_idx].collapsed == None:
                # # Debugging...
                # for idx, x in enumerate(self.tile_map[neighbor_idx].possible):
                #     print(f'EVAN: {self.template.tileset.idANDidx[idx]}: {self.template.tileset.tiles[self.template.tileset.idANDidx[idx]].sockets} \n')
                self.tile_map[neighbor_idx].possible = [x if socket == 
                                                        self.template.tileset.tiles[self.template.tileset.idANDidx[idx]].sockets[opp][::-1]
                                                        else 0 for idx, x in enumerate(self.tile_map[neighbor_idx].possible)]
                
                self.entropy_map[neighbor_idx] = self.tile_map[neighbor_idx].compute_entropy()

    def update_neighbors(self, idx):
        collapsed_tile_idx = self.template.tileset.idANDidx[self.tile_map[idx].collapsed]
        neighbor_idxs  = self.template.analyzer.get_neighbor_idxs(idx)

        for i, neighbor_idx in enumerate(neighbor_idxs):
            if not self.is_inbounds(neighbor_idx):
                continue

            if neighbor_idx not in self.tile_map:
                num_tiles = self.template.tileset.count
                # num_tiles = len(self.template.data_encoded.keys())
                self.tile_map[neighbor_idx] = waveTileAdvanced(distribution=np.zeros(num_tiles), possible=np.ones(num_tiles))
                self.num_uncollapsed += 1

            if self.tile_map[neighbor_idx].collapsed != None:
                continue

            kernel_idx = self.kernel_idxs[i]

            if not collapsed_tile_idx in self.template.data_encoded:
                continue

            self.tile_map[neighbor_idx].distribution += self.template.data_encoded[collapsed_tile_idx][:, kernel_idx[0], kernel_idx[1]]
            # TODO: edit below to produce correct effect
            self.tile_map[neighbor_idx].distribution[np.where(self.template.data_encoded[collapsed_tile_idx][:, kernel_idx[0], kernel_idx[1]] == 0)] = 0
            self.entropy_map[neighbor_idx] = self.tile_map[neighbor_idx].compute_entropy() # returns AND sets entropy for wavetile
            # if self.tile_map[neighbor_idx].entropy == np.inf:
            #     self.tile_map[neighbor_idx].collapsed = (-1,0)
            #     self.num_uncollapsed -= 1

            # print(f'ENTROPY of {neighbor_idx}: {self.tile_map[neighbor_idx].entropy}')

        if self.use_sockets and collapsed_tile_idx in self.template.data_encoded:
            self.check_sockets(idx)

    def resolve_error(self, err_idx):
        '''Recursively re-evaluates neighbors such that a valid tile can be selected in the place of an error tile'''
        print(f'resolving error originating @ {err_idx}')
        if self.allow_offtemplate_matches:
            pass
            # TODO: implement "weaker" solution that just tries to get a viable tile
            #       from neighbors' "possible" arrays

            # IDEA: Start with neighbor with highest non-infinte entropy as this will
            #       have the most options. Definitely need to avoid 0-entropy tiles
            #       which either have a single option or are error tiles themselves?
        else:
            pass
            # TODO: implment more elegant solution that resolves the error with a tile
            #       that an option with compatible "distribution" and "possible" arrays

    def collapse(self, start=False):
        if start and not self.region_enforced: # First iteration
            self.tile_map[self.start_idx] = waveTileAdvanced(collapsed=self.start_tile)
            self.update_neighbors(self.start_idx)
            return self.start_idx, False
        
        if self.num_uncollapsed == 0:
            return None, True

        min_idx = np.unravel_index(np.argmin(self.entropy_map), self.entropy_map.shape)
        target_tile = self.tile_map[min_idx]
        # min_entropy = self.entropy_map[min_idx]

        if target_tile.collapsed != None:
            # Handles enforced region tiles
            # print(f'Already collapsed tile at {min_idx} with entropy {target_tile.entropy} with id {target_tile.collapsed}: left: {self.num_uncollapsed}: Start: {start}')
            self.num_uncollapsed -= 1
            return min_idx, False

        probs = target_tile.distribution * target_tile.possible
        # print(min_idx, probs)
        probs_sum = np.sum(probs)
        chosen_id = (-1, 0)

        if self.allow_offtemplate_matches:
            if probs_sum == 0.0:
                probs = target_tile.possible
                probs_sum = np.sum(probs)

        if probs_sum != 0.0:
            probs = probs / probs_sum
            # print(f'Entropy: {min_entropy}, min_idx: {min_idx}, tiles left: {self.num_uncollapsed}')
            # TODO: why this rng causing wfc to make the same map every time?
            chosen_idx = self.rng.choice(range(len(probs)), 1, p=probs)[0]
            chosen_id  = self.template.tileset.idANDidx[chosen_idx]

        if chosen_id == (-1, 0):
            self.resolve_error(min_idx)
            # print(f'\nError Tile selected! @ {min_idx}')
            

        target_tile.collapsed = chosen_id
        # print('taget_tile.collapsed ', target_tile.collapsed)
        self.num_uncollapsed -= 1
        self.entropy_map[min_idx] = np.inf

        self.update_neighbors(min_idx)

        return min_idx, False

    def run(self):
        self.init_rng()
        self.collapse(start=True)
        while True:
                collapsed_idx, terminate = self.collapse()
                if terminate:
                    break

        # print(len(self.tile_map.keys()))
        # ids = []
        # for w in self.tile_map.values():
        #     ids.append(w.collapsed)
        # print("THIS")
        # print((-1,0) in ids)
    
##############################################
#############------ MAIN ------###############
##############################################

if __name__ == "__main__":

    from wfc_GUI import WFC_GUI

    # Input your own custom tilesets via the WFC_GUI classmethod below
    wfc_dict = WFC_GUI.load_Templates()

    wfc_window = WFC_GUI(wfc_dict, run_animated=False)
    wfc_window.launch()

        



