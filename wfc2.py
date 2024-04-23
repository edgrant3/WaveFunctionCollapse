from enum import Enum
from PIL import ImageTk, Image
import numpy as np

import tile
import template

import heapq as hq

from warnings import warn

# TODO List:
### 1) Implement resolve_error() to recursively fix regions with error tiles
### 2) convert entropy map to heapq structure


class WFCRules(Enum):
    SOCKETS_ONLY   = 1 # use waveTileAdvanced.possible
    TEMPLATES_ONLY = 2 # use waveTileAdvanced.distribution
    BOTH_STRICT    = 3 # use both .possible and .distribution
    BOTH_RELAXED   = 4 # use both, but use only .possible for tiles where .possible and .distribution have no shared options

class WFC():
    seed = None
    def __init__(self, grid_size, template, rules=WFCRules.SOCKETS_ONLY, start_idx=(0,0), start_id=(0,0)):
        self.rules = rules        # establishses edge matching requirements

        self.template = template  # template which may or may not be filled out, owns a tileset to use
        self.i2i = self.template.tileset.idANDidx

        self.grid_size = grid_size  
        self.win_size  = self.compute_win_size()
        
        self.tile_map   = {}    # Holds all waveTileAdv, in order of creation (ideally want this order of collapse)
        # To store by order of collapse rather than creation, but keep uncollapsed tiles in the map so they can be
        # easily influenced by tiles that collapse near them, when collapsing tiles I will simultaneously 
        # pop and re-insert the entry via (a[key] = a.pop(key))

        self.start_idx  = start_idx # Point in grid to first arbitrarily collapse
        self.start_tile = start_id  # Arbitrary Tile ID to collapse the first tile down to

        # heap queue struct to hold all visited but uncollapsed tiles (lowest entropy pops off first)
        self.entropy_heapq = [] # [(entropy, idx), ...]
        # len(self.entropy_heapq) replaces self.num_uncollapsed

        self.kernel_rel_idxs, self.kernel_idxs = self.template.analyzer.get_neighbor_relative_idxs()

        self.init_rng()

        self.is_start = True

    @classmethod
    def set_seed(cls, seed):
        cls.seed = seed

    def compute_win_size(self):
        return (self.template.tileset.tile_px_w * self.grid_size[0], \
                self.template.tileset.tile_px_h * self.grid_size[1])

    def init_rng(self):
        if WFC.seed is None:
            self.rng = np.random.default_rng()
        else:
            self.rng = np.random.default_rng(WFC.seed)

    def set_rules(self, rule_int):
        self.rules = WFCRules(rule_int)

    def clear_data(self):
        self.entropy_heapq.clear()
        self.tile_map.clear()
        self.is_start = True

    def use_template(self, template):
        self.clear_data()
        self.template = template
        self.win_size = self.compute_win_size()

    def is_inbounds(self, grid_idx):
        return (grid_idx[0] >= 0 and grid_idx[0] < self.grid_size[0] and \
                grid_idx[1] >= 0 and grid_idx[1] < self.grid_size[1])
    
    def create_waveTileAdvanced(self, collapsed=None, distribution=None, possible=None):
        
        if distribution is None:
            distribution = np.copy(self.template.tileset.default_distribution)
        if possible is None:
            possible = np.copy(self.template.tileset.default_possible)

        return tile.waveTileAdvanced(distribution, possible, collapsed) 

    def add_to_tilemap(self, grid_idx, collapsed=None):
        # Creates a new waveTileAdv and inserts it into the tile_map
        # if not collapsed, push this instance's info onto the entropy queue
        # if tis collapsed, update neighbors
        self.tile_map[grid_idx] = self.create_waveTileAdvanced(collapsed)

        # self.tile_map[grid_idx] = tile.waveTileAdvanced(collapsed=collapsed, 
        #                                                 distribution=self.template.tileset.default_distribution, 
        #                                                 possible=self.template.tileset.default_possible)
        if collapsed is None:
            hq.heappush(self.entropy_heapq, (np.inf, grid_idx))

    def update_neighbors(self, grid_idx, collapsed_id=None):
        if collapsed_id is None:
            collapsed_id = self.tile_map[grid_idx].collapsed

        collapsed_idx = self.i2i[collapsed_id]

        # TODO: consider changing how data_encoded is stored so no id->idx conversion is needed here
        if collapsed_idx not in self.template.data_encoded or collapsed_id == (-1, 0):
            warn('Attempted to update neighbors with invalid or Error tile_id')
            return
        
        if self.rules is not WFCRules.SOCKETS_ONLY:
            self.update_neighbors_using_template(grid_idx, collapsed_id)
            return

        if self.rules is not WFCRules.TEMPLATES_ONLY:
            self.update_neighbors_using_sockets(grid_idx, collapsed_id)
        
    def update_neighbors_using_sockets(self, grid_idx, collapsed_id):
        # Sockets only apply to the 4 neighbors around the collapsed tile
        for dir in tile.Tile.directions.values(): # ["N", "E", "S", "W"]:
            if not dir.is_inbounds(grid_idx, self.grid_size):
                continue
            self.update_neighbor_using_sockets(grid_idx, dir, collapsed_id)

    def update_neighbor_using_sockets(self, grid_idx, neighbor_dir, collapsed_id):
        
        neighbor_idx = (grid_idx[0] + neighbor_dir.idx[0], 
                        grid_idx[1] + neighbor_dir.idx[1])

        if neighbor_idx not in self.tile_map:
            self.add_to_tilemap(neighbor_idx)

        possible_mask  = self.template.tileset.socket_matches[self.i2i[collapsed_id]][neighbor_dir.dir]

        self.tile_map[neighbor_idx].possible *= possible_mask #* self.tile_map[neighbor_idx].possible

        new_entropy = self.tile_map[neighbor_idx].compute_entropy(self.rules)

        # Add neighbor to heapq. Note: if already in heapq this will create a duplicate entry,
        # but this is fine as the data is small and we can ignore duplicates that are popped after
        # their corresponding tile has collapsed
        hq.heappush(self.entropy_heapq, (new_entropy, neighbor_idx))
    
    def check_neighbors_using_sockets(self, grid_idx, candidate_tile_idx):
        ''' Used to check if tile of "id" is compatible with location "idx" in tile_map...
            returns True if its socket is compatible with collapsed neighbors' sockets or 
            uncollapsed neighbors' possible sockets '''

        for direction in tile.Tile.directions.values(): # ["N", "E", "S", "W"]
            if not direction.is_inbounds(grid_idx, self.grid_size):
                continue

            opp = direction.opp
            dir_idx = direction.idx
            neighbor_idx = (grid_idx[0] + dir_idx[0], grid_idx[1] + dir_idx[1])

            if neighbor_idx not in self.tile_map:
                continue

            # neighbor is a waveTileAdvanced
            neighbor = self.tile_map[neighbor_idx]
            if neighbor.collapsed is not None:
                collapsed_neighbor_idx = self.template.tileset.idANDidx[neighbor.collapsed]
                allowed_by_neighbor = self.template.tileset.socket_matches[collapsed_neighbor_idx][opp]
                if not allowed_by_neighbor[candidate_tile_idx]:
                    return False

            else:
                # Check if id is invalid for all possible tiles which neighbor can become
                nonzero_idxs = np.where(neighbor.possible != 0)[0]
                allowed = False
                for possible_neighbor_idx  in nonzero_idxs:
                    allowed_by_neighbor = self.template.tileset.socket_matches[possible_neighbor_idx][opp]
                    if allowed_by_neighbor[candidate_tile_idx]:
                        allowed = True
                if not allowed:
                    return False
                
        return True
    
    def collapse_tile(self, grid_idx, collapsed_id):

        if grid_idx not in self.tile_map:
            self.add_to_tilemap(grid_idx, collapsed_id)
        else:
            self.tile_map[grid_idx].collapse(collapsed_id)

        # pop and re-insert collapsed item to capture it's collapse order in dict for later utility
        # TODO: test if this method is efficient enought to warrant not just storing another array for collapse order
        self.tile_map[grid_idx] = self.tile_map.pop(grid_idx)

        self.update_neighbors(grid_idx, collapsed_id)
        
    def collapse(self):

        if self.is_start: # First iteration
            self.collapse_tile(self.start_idx, self.start_tile)
            self.is_start = False
            return self.start_idx, False
        
        while len(self.entropy_heapq):
            min_idx = hq.heappop(self.entropy_heapq)[1]
            target_tile = self.tile_map[min_idx] # min_idx guranteed to be in map

            if target_tile.collapsed is None:
                # entry popped from entropy queue is NOT a duplicate and we can continue
                break

        # catch the terminal case of empty entropy priority queue (no more tiles to collapse)
        if not self.entropy_heapq:
            return None, True

        probs = target_tile.possible * target_tile.distribution
        probs_sum = np.sum(probs)

        chosen_id = self.template.tileset.error_id

        # If rule is relaxed with no available possible/distribution or rule is sockets-only, default to not using distribution
        if (self.rules == WFCRules.BOTH_RELAXED and probs_sum == 0.0) or self.rules == WFCRules.SOCKETS_ONLY:
            probs = target_tile.possible
            probs_sum = np.sum(probs)

        # if only using sockets, we WILL apply the weights specified in the tileset JSONs
        # and additionally will use patch tiles if any exist to cover errors
        if self.rules == WFCRules.SOCKETS_ONLY:
            weights = self.template.tileset.get_weights()
                
            if probs_sum != 0.0:
                probs = weights * target_tile.possible
            else:
                viable_patch_idxs = []
                for patch_idx in self.template.tileset.patch_idxs:
                    if self.check_neighbors_using_sockets(min_idx, patch_idx):
                        viable_patch_idxs.append(patch_idx)
                        
                if viable_patch_idxs:
                    if len(viable_patch_idxs) == 1:
                        chosen_id = viable_patch_idxs[0]
                    else:
                        probs = np.zeros_like(probs)
                        for vp in viable_patch_idxs:
                            probs[vp] = weights[vp]
        

        probs_sum = np.sum(probs)
        if probs_sum != 0.0:
            probs = probs / probs_sum
            chosen_idx = self.rng.choice(range(len(probs)), 1, p=probs)[0]
            chosen_id  = self.template.tileset.idANDidx[chosen_idx]

        # if no solution found... try to resolve error (TODO)
        if chosen_id == self.template.tileset.error_id:
            # chosen_id = self.resolve_error(min_idx)
            print(f'\nError Tile selected! @ {min_idx}')
        
        self.collapse_tile(min_idx, chosen_id)

        return min_idx, False

    def enforce_region(self, region, tile_id):
        print(f'enforcing region')
        self.region_enforced = True
        region_ws = range(region[0], region[2])
        region_hs = range(region[1], region[3])
        for w_idx in region_ws:
            for h_idx in region_hs:
                idx = (w_idx, h_idx)
                self.collapse_tile(idx, tile_id)
        self.is_start = False

    def run(self):
        print("\nRunning WFC")
        self.init_rng()
        self.collapse()
        while True:
                collapsed_grid_idx, terminate = self.collapse()
                if terminate:
                    print('No tiles left in priority queue... Terminating')
                    break

    def run_step(self):
        if self.is_start:
            self.init_rng()
        idx, terminate = self.collapse()
        print(f'\n{idx} collapsed')
    
##############################################
#############------ MAIN ------###############
##############################################

if __name__ == "__main__":

    from wfc_GUI import WFC_GUI
    
    tile.TileSet.default_scale = 1
    grid_dims = (100, 80)

    template_filenames = {  "default_tile_set",
                            "village_tile_set2",
                            "ocean_tile_set",
                            "seaweed_set"
                         }

    # Input your own custom tilesets via the WFC_GUI classmethod below
    wfc_templates = template.Template.load_templates(template_filenames)
    wfc_dict   = {i : WFC(grid_dims, t, rules=WFCRules.SOCKETS_ONLY) for i, t in enumerate(wfc_templates.values())}
    wfc_window = WFC_GUI(wfc_dict, run_animated=False)
    wfc_window.launch()

        



