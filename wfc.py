import numpy as np
import time

from wfc_GUI import WFC_GUI
from tile import Tile, waveTile


class WFC():
    def __init__(self, grid_size, tiles, tile_ids, patch_ids, win = None):
        self.grid_size = grid_size
        self.tiles = tiles #contains both normal tiles and patch tiles
        self.tile_ids = tile_ids
        self.patch_ids = patch_ids
        self.n_tiles = len(self.tile_ids)

        self.tile_size = self.tiles[self.tile_ids[0]].img_size
        self.win_size = (self.tile_size[0] * self.grid_size[0], self.tile_size[1] * self.grid_size[1])

        if win:
            self.win = win
        else:
            self.win = WFC_GUI.fromTileGrid(self.tiles[self.tile_ids[0]].img_size, self.grid_size)

        self.entropy_map = np.ones((self.win.grid_dims[0], self.win.grid_dims[1])) * self.n_tiles
        self.tile_map    = {}  
        self.start_idx = (0,0)
        self.start_tile = (0,0)
    
    def enforce_region(self, region, tile_id):
        region_ws = range(region[0], region[2])
        region_hs = range(region[1], region[3])
        for w_idx in region_ws:
            for h_idx in region_hs:
                idx = (w_idx, h_idx)
                self.tile_map[idx] = waveTile((tile_id, 0), True)
                self.entropy_map[idx] = self.n_tiles + 1
                self.update_neighbors(idx)


    def update_neighbors(self, idx):
        collapsed_tile = self.tiles[self.tile_map[idx].possible[0]]

        for dir in ["N", "E", "S", "W"]:
            if Tile.directions[dir].is_inbounds(idx, self.win.grid_dims):
                socket  = collapsed_tile.sockets[dir]
                opp     = Tile.directions[dir].opp
                dir_idx = Tile.directions[dir].idx
                neighbor_idx = (idx[0] + dir_idx[0], idx[1] + dir_idx[1])

                if neighbor_idx not in self.tile_map:
                    self.tile_map[neighbor_idx] = waveTile(self.tile_ids, False)

                if not self.tile_map[neighbor_idx].collapsed:
                    self.tile_map[neighbor_idx].possible = [x for x in self.tile_map[neighbor_idx].possible \
                                                            if socket == self.tiles[x].sockets[opp][::-1]]
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

        if min_entropy == self.n_tiles + 1:
            # All tiles have collapsed
            return tile_idx, True
    
        if min_entropy == self.n_tiles:
            # First iteration
            tile_idx = self.start_idx #(0,0)
            self.tile_map[tile_idx] = waveTile([self.start_tile], True)
            self.entropy_map[tile_idx] = self.n_tiles + 1
            self.update_neighbors(tile_idx)
            return tile_idx, False

        # Nominal Case
        options = self.tile_map[tile_idx].possible
        num_options = len(options)
        if num_options != 0:
            # if there is a viable tile, choose one at random from weighted distribution
            prob = [self.tiles[t].weight for t in options] 
            prob /= np.sum(prob)
                
            options_idx = range(len(options))
            chosen_idx = np.random.choice(options_idx, 1, p=prob)[0]
            self.tile_map[tile_idx].possible = [options[chosen_idx]]

        else:
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
                # No viable tiles or patches
                self.tile_map[tile_idx].possible = [(-1, 0)] # -1 is the error tile
            
        self.tile_map[tile_idx].collapsed = True
        self.entropy_map[tile_idx] = self.n_tiles + 1

        self.update_neighbors(tile_idx)
        return tile_idx, False
    
    def draw(self, idx, refresh = False):
        pass
        img = self.tiles[self.tile_map[idx].possible[0]].image
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
    
    def run(self, tileset = None):
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

    village = "village_tile_set2"
    default = "default_tile_set"
    ocean   = "ocean_tile_set"
    seaweed = "seaweed_set"

    Tile.generate_error_tile()
    t1_dict, t1, pt1 = Tile.generate_tiles_JSON(default)
    t2_dict, t2, pt2 = Tile.generate_tiles_JSON(village)
    t3_dict, t3, pt3 = Tile.generate_tiles_JSON(ocean)
    t4_dict, t4, pt4 = Tile.generate_tiles_JSON(seaweed)

    t_dict = {0: (t1_dict, t1, pt1), 
              1: (t2_dict, t2, pt2),
              2: (t3_dict, t3, pt3),
              3: (t4_dict, t4, pt4)}
    
    toggle = 0
    wfc = WFC(grid_dims, t_dict[toggle][0], t_dict[toggle][1], t_dict[toggle][2])   
    first_run = True
    while(True):
        
        wfc = WFC(wfc.grid_size, t_dict[toggle][0], t_dict[toggle][1], t_dict[toggle][2], wfc.win)
        
        if toggle == 3:
            seabed_region = (0, grid_dims[1]-1, grid_dims[0], grid_dims[1])
            wfc.enforce_region(seabed_region, (5,0))

        wfc.run()
        if first_run:
            first_run = False
        else:
            wfc.win.wait_for_keypress()
            time.sleep(0.25)
            # pass
        wfc.draw_all(refresh=run_animated)

        if save_result:
            wfc.win.img.save("output.png")

        toggle = (toggle + 1) % len(t_dict.keys())



