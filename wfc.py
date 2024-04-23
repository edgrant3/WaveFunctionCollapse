import enum
from PIL import ImageTk, Image
import numpy as np

import tile
import template

# TODO List:
### 1) Implement resolve_error() to recursively fix regions with error tiles
### 2) convert entropy map to heapq structure


class WFCRules(enum.Enum):
    SOCKETS_ONLY   = 1 # use waveTileAdvanced.possible
    TEMPLATES_ONLY = 2 # use waveTileAdvanced.distribution
    BOTH_STRICT    = 3 # use both .possible and .distribution
    BOTH_RELAXED   = 4 # use both, but use only .possible for tiles where .possible and .distribution have no shared options

class WFC():
    seed = None
    def __init__(self, grid_size, template, rules=WFCRules.SOCKETS_ONLY):

        self.template = template
        self.rules = rules
        self.grid_size = grid_size

        self.win_size = (self.template.tileset.tile_px_w * grid_size[0], self.template.tileset.tile_px_h * grid_size[1])
        self.entropy_map = np.full(grid_size, np.inf) # WAS: np.ones((self.win.grid_dims[0], self.win.grid_dims[1])) * self.n_tiles
        self.tile_map    = {}  
        self.start_idx = (0,0)
        self.start_tile = (0,0)
        self.num_uncollapsed = 0 # number of instantiated waveTileAdvanced that have not been collapsed
        self.region_enforced = False

        self.relative_neighbor_idxs, self.kernel_idxs = self.template.analyzer.get_neighbor_relative_idxs()
        self.init_rng()

        self.default_possible     = np.ones(self.template.tileset.count, dtype=np.int0)
        self.default_distribution = np.ones(self.template.tileset.count, dtype=int)
        
    
    @classmethod
    def set_seed(cls, seed):
        cls.seed = seed

    def set_rules(self, rule_int):
        self.rules = WFCRules(rule_int)
        
    def clear_data(self):
        self.entropy_map = np.full(self.grid_size, np.inf) # WAS: np.ones((self.win.grid_dims[0], self.win.grid_dims[1])) * self.n_tiles
        self.tile_map.clear() 

    def init_rng(self):
        if WFC.seed is None:
            self.rng = np.random.default_rng()
        else:
            self.rng = np.random.default_rng(WFC.seed)
    
    def use_template(self, template):
        self.template = template
    
    def enforce_region(self, region, tile_id):
        self.setup_patches()
        self.region_enforced = True
        region_ws = range(region[0], region[2])
        region_hs = range(region[1], region[3])
        for w_idx in region_ws:
            for h_idx in region_hs:
                idx = (w_idx, h_idx)
                self.add_to_tilemap(grid_idx=idx, collapsed=tile_id)
                self.entropy_map[idx] = self.tile_map[idx].entropy

        for w_idx in region_ws:
            for h_idx in region_hs:
                idx = (w_idx, h_idx)
                self.update_neighbors(idx)
        
    def is_inbounds(self, idx):
        return (idx[0] >= 0 and idx[0] < self.grid_size[0] and
                idx[1] >= 0 and idx[1] < self.grid_size[1])

    def add_to_tilemap(self, grid_idx, collapsed=None):
        self.tile_map[grid_idx] = tile.waveTileAdvanced(collapsed=collapsed, 
                                                        distribution=self.default_distribution, 
                                                        possible=self.default_possible)
        if collapsed is None:
            self.num_uncollapsed += 1

    
    def check_neighbors_using_sockets(self, grid_idx, id):
        ''' Used to check if tile of "id" is compatible with location "idx" in tile_map...
            returns True if its socket is compatible with collapsed neighbors' sockets or 
            uncollapsed neighbors' possible sockets '''
        
        candidate_tile_idx = self.template.tileset.idANDidx[id]

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

    def update_neighbors_using_sockets(self, grid_idx):
        collapsed_tile_idx = self.template.tileset.idANDidx[self.tile_map[grid_idx].collapsed]
        for direction in tile.Tile.directions.values(): # ["N", "E", "S", "W"]:
            if not direction.is_inbounds(grid_idx, self.grid_size):
                continue
            self.update_single_neighbor_using_sockets(grid_idx, direction, collapsed_tile_idx)

    def update_single_neighbor_using_sockets(self, grid_idx, neighbor_direction, collapsed_idx=None):
            if collapsed_idx is None:
                collapsed_idx = self.template.tileset.idANDidx[self.tile_map[grid_idx].collapsed]
            dir = neighbor_direction.dir
            dir_idx = neighbor_direction.idx
            neighbor_idx = (grid_idx[0] + dir_idx[0], grid_idx[1] + dir_idx[1])

            if neighbor_idx not in self.tile_map:
                self.add_to_tilemap(neighbor_idx)

            adjacent_possible  = self.template.tileset.socket_matches[collapsed_idx][dir]
            self.tile_map[neighbor_idx].possible = adjacent_possible * self.tile_map[neighbor_idx].possible              
            self.entropy_map[neighbor_idx] = self.tile_map[neighbor_idx].compute_entropy(self.rules)

    def update_neighbors_using_template(self, grid_idx, collapsed_idx):
        neighbor_idxs  = self.template.analyzer.get_neighbor_idxs(grid_idx)
        for i, neighbor_idx in enumerate(neighbor_idxs):
            
            if not self.is_inbounds(neighbor_idx): continue
            if neighbor_idx not in self.tile_map:
                self.add_to_tilemap(neighbor_idx)

            if self.tile_map[neighbor_idx].collapsed is not None: continue
            if not collapsed_idx in self.template.data_encoded:   continue

            k_idx = self.kernel_idxs[i]
            encoded_distribution = self.template.data_encoded[collapsed_idx][:, k_idx[0], k_idx[1]]
            self.tile_map[neighbor_idx].distribution = self.tile_map[neighbor_idx].distribution + encoded_distribution
            exclude_idxs = np.argwhere(encoded_distribution == 0)
            self.tile_map[neighbor_idx].distribution[exclude_idxs] = 0
            self.entropy_map[neighbor_idx] = self.tile_map[neighbor_idx].compute_entropy(self.rules) # returns AND sets entropy for wavetile


    def update_tile_from_neighbors_using_template(self, grid_idx):
        for relative_idx in self.relative_neighbor_idxs:
            neighbor_idx = (grid_idx[0] + relative_idx[0], grid_idx[1] + relative_idx[1])
            print(relative_idx)
            if not self.is_inbounds(neighbor_idx):              continue
            if neighbor_idx not in self.tile_map:               continue

            #debug
            if self.tile_map[neighbor_idx] is None:
                print(f'NONE waveTileAdvanced @ {neighbor_idx}, relative: {relative_idx}')
                continue

            if self.tile_map[neighbor_idx].collapsed is None:   continue

            collapsed_idx = self.tile_map[neighbor_idx].collapsed
            if not collapsed_idx in self.template.data_encoded: continue

            k_idx = (grid_idx[0] - relative_idx[0], grid_idx[1] - relative_idx[1])
            encoded_distribution = self.template.data_encoded[collapsed_idx][:, k_idx[0], k_idx[1]]
            self.tile_map[grid_idx].distribution = self.tile_map[grid_idx].distribution + encoded_distribution
            self.entropy_map[grid_idx] = self.tile_map[grid_idx].compute_entropy(self.rules) # returns AND sets entropy for wavetile
            

    def update_tile_from_neighbors_using_sockets(self, grid_idx):
        for direction in tile.Tile.directions.values(): # ["N", "E", "S", "W"]:
            if not direction.is_inbounds(grid_idx, self.grid_size):
                continue
            
            neighbor_idx = (grid_idx[0] + direction.idx[0], grid_idx[1] + direction.idx[1])
            if self.tile_map[neighbor_idx].collapsed is None:
                continue

            self.update_single_neighbor_using_sockets(neighbor_idx, tile.Tile.directions[direction.opp])
        pass
    
    def reset_tile(self, grid_idx):
        self.tile_map[grid_idx] = self.add_to_tilemap(grid_idx)

    def refresh_neighbors(self, grid_idx):
        ''' reverse the effect of a collapsed tile which is getting changed 
            *imaginging cool effect* - user drawing in tiles they prefer and the image
            updates accordingly in real time'''
        if self.rules != WFCRules.SOCKETS_ONLY:
            for relative_idx in self.relative_neighbor_idxs:
                neighbor_idx = (grid_idx[0] + relative_idx[0], grid_idx[1] + relative_idx[1])
                if not self.is_inbounds(neighbor_idx):            continue
                if neighbor_idx not in self.tile_map:             continue
                self.reset_tile(grid_idx)

                self.update_tile_from_neighbors_using_template(neighbor_idx)

        if self.rules != WFCRules.TEMPLATES_ONLY:
            for direction in tile.Tile.directions.values(): # ["N", "E", "S", "W"]:
                if not direction.is_inbounds(grid_idx, self.grid_size):
                    continue
                neighbor_idx = (grid_idx[0] + direction.idx[0], grid_idx[1] + direction.idx[1])
                self.update_tile_from_neighbors_using_sockets(grid_idx)

    def update_neighbors(self, grid_idx):
        collapsed_tile_idx = self.template.tileset.idANDidx[self.tile_map[grid_idx].collapsed]
        if collapsed_tile_idx not in self.template.data_encoded or self.tile_map[grid_idx].collapsed == (-1, 0):
            return
        
        if self.rules != WFCRules.SOCKETS_ONLY:
            self.update_neighbors_using_template(grid_idx, collapsed_tile_idx)

        if self.rules != WFCRules.TEMPLATES_ONLY:
            self.update_neighbors_using_sockets(grid_idx)

    def resolve_error(self, err_idx):
        '''Recursively re-evaluates neighbors such that a valid tile can be selected in the place of an error tile'''
        print(f'TBD: resolving error originating @ {err_idx}')
        if True:#self.rules == WFCRules.BOTH_RELAXED:#self.allow_offtemplate_matches:
            # TODO: implement "weaker" solution that just tries to get a viable tile
            #       from neighbors' "possible" arrays

            # IDEA: Start with neighbor with highest non-infinte entropy as this will
            #       have the most options. Definitely need to avoid 0-entropy tiles
            #       which either have a single option or are error tiles themselves?


            # 1) itereate through all tiles and select the one which has most agreement among 4-neighbors' sockets
            # 1a) if not unanimous, recurse to errant neighbor 
            neighbors = []
            for direction in tile.Tile.directions.values():
                neighbor_idx = (err_idx[0] + direction.idx[0], err_idx[1] + direction.idx[1])

                if not direction.is_inbounds(err_idx, self.grid_size): continue
                if neighbor_idx not in self.tile_map:                  continue
                if self.tile_map[neighbor_idx].collapsed is None:      continue

                neighbors.append((direction, neighbor_idx, self.tile_map[neighbor_idx].collapsed))

            num_neighbors = len(neighbors)
            neighbor_agreement = np.zeros((num_neighbors, self.template.tileset.count))
            for i, n in enumerate(neighbors):
                collapsed_neighbor_idx = self.template.tileset.idANDidx[n[2]]
                agreement = self.template.tileset.socket_matches[collapsed_neighbor_idx][n[0].opp]
                neighbor_agreement[i,:] = agreement

            votes = np.sum(neighbor_agreement, axis=0)
            possible_idxs = np.argwhere(votes == np.max(votes)).flatten()

            chosen_idx = self.rng.choice(possible_idxs, 1)[0]
            chosen_id  = self.template.tileset.idANDidx[chosen_idx]
            self.tile_map[err_idx].collapse(chosen_id)

            if votes[chosen_idx] == num_neighbors:
                return chosen_id
            
            print(f'{votes[chosen_idx]} neighbors to error need cleaning up...')
            errant_neighbors = [n for i,n in enumerate(neighbors) if neighbor_agreement[i,chosen_idx] == 0]
            for e_n in errant_neighbors:
                self.reset_tile(e_n[1])
                self.refresh_neighbors(e_n[1])
                self.resolve_error(e_n[1])

            return chosen_id

        
            

        elif self.rules == WFCRules.BOTH_STRICT:
            return (-1, 0)
            # TODO: implment more elegant solution that resolves the error with a tile
            #       that an option with compatible "distribution" and "possible" arrays

    def collapse(self, start=False):
        if start and not self.region_enforced: # First iteration
            self.add_to_tilemap(grid_idx=self.start_idx, collapsed=self.start_tile)
            self.entropy_map[self.start_idx] = self.tile_map[self.start_idx].compute_entropy(self.rules)
            self.update_neighbors(self.start_idx)
            return self.start_idx, False
        
        if self.num_uncollapsed == 0:
            return None, True

        min_idx = np.unravel_index(np.argmin(self.entropy_map), self.entropy_map.shape)
        target_tile = self.tile_map[min_idx]
        # min_entropy = self.entropy_map[min_idx]

        if target_tile.collapsed != None:
            # Handles enforced region tiles
            self.num_uncollapsed -= 1
            return min_idx, False

        probs = target_tile.possible * target_tile.distribution
        probs_sum = np.sum(probs)
        chosen_id = (-1, 0)

        if (self.rules == WFCRules.BOTH_RELAXED and probs_sum == 0.0) or self.rules == WFCRules.SOCKETS_ONLY:
            probs = target_tile.possible
            probs_sum = np.sum(probs)

        if self.rules == WFCRules.SOCKETS_ONLY:
            weights = []
            for t_idx in range(len(target_tile.possible)):
                t_id = self.template.tileset.idANDidx[t_idx]
                weights.append(self.template.tileset.tiles[t_id].weight)
                
            if probs_sum != 0.0:
                probs   = weights * target_tile.possible
                probs = probs / np.sum(probs)
            else:
                viable_patches = []
                # print(f'looking for viable patch tiles...')
                for patch_idx in self.patch_tiles_idx:
                    patch_id = self.template.tileset.idANDidx[patch_idx]
                    if self.check_neighbors_using_sockets(min_idx, patch_id):
                        viable_patches.append(patch_id)
                        
                if viable_patches:
                    if len(viable_patches) == 1:
                        chosen_id = viable_patches[0]
                    else:
                        probs = np.zeros_like(probs)
                        for vp in viable_patches:
                            vp_idx = self.template.tileset.idANDidx[vp]
                            probs[vp_idx] = weights[vp_idx]
                        probs = probs / np.sum(probs)

        else:
            if probs_sum != 0.0:
                probs = probs / probs_sum

        if np.sum(probs) != 0.0:
            chosen_idx = self.rng.choice(range(len(probs)), 1, p=probs)[0]
            chosen_id  = self.template.tileset.idANDidx[chosen_idx]

        if chosen_id == (-1, 0):
            chosen_id = self.resolve_error(min_idx)
            # print(f'\nError Tile selected! @ {min_idx}')
        
        target_tile.collapse(chosen_id)
        self.num_uncollapsed -= 1
        self.entropy_map[min_idx] = np.inf

        self.update_neighbors(min_idx)

        return min_idx, False

    def setup_patches(self):
        self.patch_tiles_idx = None
        if self.rules == WFCRules.SOCKETS_ONLY:
            self.patch_tiles_idx = []
            for tile_id, t in self.template.tileset.tiles.items():
                if t.ispatch:
                    self.patch_tiles_idx.append(self.template.tileset.idANDidx[tile_id])
            self.default_possible[self.patch_tiles_idx] = 0

        # mid_kernel = (self.kernel_idxs[-1][0] // 2, self.kernel_idxs[-1][1] // 2)
        # # print(mid_kernel)
        # for idx in range(self.template.tileset.count):
        #     print(f'COUNT: {self.template.data_encoded[idx][idx, mid_kernel[0], mid_kernel[1]]}')
        #     if self.template.data_encoded[idx][idx, mid_kernel[0], mid_kernel[1]] != 0:
        #         self.start_tile = self.template.tileset.idANDidx[idx]
        #         print(f'EVAN: {self.start_tile}')
        #         break

    def run(self):
        self.setup_patches()
        self.init_rng()
        self.collapse(start=True)
        while True:
                collapsed_idx, terminate = self.collapse()
                if terminate:
                    break
    
##############################################
#############------ MAIN ------###############
##############################################

if __name__ == "__main__":

    from wfc_GUI import WFC_GUI

    tile.TileSet.default_scale = 2
    default_rules = WFCRules.SOCKETS_ONLY
    grid_dims = (40, 30)
    template_filenames = {  "default_tile_set",
                            "village_tile_set2",
                            "ocean_tile_set",
                            "seaweed_set"
                            #, "bright_set"
                         }
    
    wfc_templates = template.Template.load_templates(template_filenames)

    # Input your own custom tilesets via the WFC_GUI classmethod below

    wfc_dict   = {i : WFC(grid_dims, t, rules=WFCRules.BOTH_STRICT) for i, t in enumerate(wfc_templates.values())}
    wfc_window = WFC_GUI(wfc_dict, run_animated=False)
    wfc_window.launch()

        



