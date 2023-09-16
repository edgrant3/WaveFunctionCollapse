import numpy as np
import time

from wfc_GUI import WFC_GUI
from tile import Tile, TileSet, waveTile

# NOTE: All indices in this project are (x, y), (col, row), (horizontal, vertical)
####### if not specified in separate width, height vars

class WFC():
    
    def __init__(self, grid_size, tileset, win = None):

        self.tileset = tileset
        self.tile_ids, self.patch_ids = self.extract_tileset_IDs()
        self.n_tiles = len(self.tile_ids)

        self.win_size = (self.tileset.tile_px_w * grid_size[0], self.tileset.tile_px_h * grid_size[1])

        if win:
            self.win = win
        else:
            self.win = WFC_GUI.fromTileGrid((self.tileset.tile_px_w, self.tileset.tile_px_h), grid_size)

        self.entropy_map = np.ones(grid_size) * self.n_tiles
        self.tile_map    = {}  
        self.start_idx   = (0,0)
        self.start_tile  = (0,0)
    
    def extract_tileset_IDs(self):
        tile_ids  = []
        patch_ids = []
        for t in self.tileset.tiles.values():
            if t.ispatch:
                patch_ids.append(t.getID())
            elif t.id != -1:
                tile_ids.append(t.getID())

        return tile_ids, patch_ids
    
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
        ''''''
        collapsed_tile = self.tileset.tiles[self.tile_map[idx].possible[0]]

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
                                                            if socket == self.tileset.tiles[x].sockets[opp][::-1]]
                    self.entropy_map[neighbor_idx] = len(self.tile_map[neighbor_idx].possible)

    def check_neighbors(self, idx, id):
        ''' Used to check if tile of "id" is compatible with location "idx" in tile_map...
            returns True if its socket is compatible with collapsed neighbors' sockets or 
            uncollapsed neighbors' possible sockets '''
        candidate_tile = self.tiles[id]

        for dir in ["N", "E", "S", "W"]:
            if not Tile.directions[dir].is_inbounds(idx, self.win.grid_dims):
                continue

            socket  = candidate_tile.sockets[dir]
            opp     = Tile.directions[dir].opp
            dir_idx = Tile.directions[dir].idx
            neighbor_idx = (idx[0] + dir_idx[0], idx[1] + dir_idx[1])

            if neighbor_idx not in self.tile_map:
                continue

            if self.tile_map[neighbor_idx].collapsed:
                if socket != self.tileset.tiles[self.tile_map[neighbor_idx].possible[0]].sockets[opp]:
                    return False
            else:
                if socket not in [self.tileset.tiles[x].sockets[opp] for x in self.tile_map[neighbor_idx].possible]:
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
            prob = [self.tileset.tiles[t].weight for t in options] 
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
                    prob = [self.tileset.tiles[t].weight for t in viable_patches] 
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
        img = self.tileset.tiles[self.tile_map[idx].possible[0]].image
        size = self.tileset.tiles[self.tile_ids[0]].image_size
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
    grid_dims = (80, 55) # < 1s per solve
    # grid_dims = (45, 30)
    TileSet.default_scale = 6
    run_animated = False
    save_result = False

    default = "default_tile_set"
    village = "village_tile_set2"
    ocean   = "ocean_tile_set"
    seaweed = "seaweed_set"
    
    defaultSet = TileSet(default)
    villageSet = TileSet(village)
    oceanSet   = TileSet(ocean)
    seaweedSet = TileSet(seaweed)

    t_dict = {0: defaultSet, 
              1: villageSet,
              2: oceanSet,
              3: seaweedSet}
    
    toggle = 0

    wfc = WFC(grid_dims, t_dict[toggle]) 
    wfc.run()
    wfc.draw_all(refresh=run_animated)
    
    while(True):
        toggle = (toggle + 1) % len(t_dict.keys())
        wfc = WFC(wfc.win.grid_dims, t_dict[toggle], wfc.win)
        
        if toggle == 3:
            seabed_region = (0, grid_dims[1]-1, grid_dims[0], grid_dims[1])
            wfc.enforce_region(seabed_region, (5,0))

        wfc.run()
        wfc.win.wait_for_keypress()
        wfc.draw_all(refresh=run_animated)

        if save_result:
            wfc.win.img.save("output.png")



