import numpy as np
import json

from wfc import Tile

class TemplateAnalyzer():
    def __init__(self, template = {}, template_path = None, kernel_size=(3,3), include_borders=False):
        self.template_path = template_path
        self.kernel_size = kernel_size
        self.include_borders = include_borders
        self.template = template
        self.tileset = None
        self.result = {}

    def load_template(self, path):
        print('\nLoading template...')
        with open(path) as f:
            loaded_template = json.load(f)

        self.template = loaded_template
        # Need to recreate tuple keys from string keys
        self.template['data'] = {tuple(map(int, k.replace('(','').replace(')','').split(','))): v for k, v in loaded_template['data'].items()}
        self.load_tileset()

    def load_tileset(self, tileset = None):
        if tileset is None:
            self.tileset, _, _ = Tile.generate_tiles_JSON(self.template['tileset_name'])
        else: 
            self.tileset = tileset

        self.tile2idx = {tile_id: idx for idx, tile_id in enumerate(self.tileset.keys())}

        self.num_tiles = len(list(self.tileset.keys()))
        self.num_tiles_w_borders = self.num_tiles + 4

        print(f'Tileset Keys (ids) ({self.num_tiles}):')
        for tile_id, tile_idx in self.tile2idx.items():
            print(f'{tile_id}: {tile_idx}')

    def tile_id2idx(self, tile_id):
        return self.tile2idx[tile_id]

    def tile_idx2id(self, tile_idx):
        return (self.tileset[tile_idx].id, self.tileset[tile_idx].rot)

    def is_inbounds(self, idx):
        return (idx[0] >= 0 and idx[0] < self.template['dims'][0] and
                idx[1] >= 0 and idx[1] < self.template['dims'][1])
    
    def get_neighbor_relative_idxs(self):
        result = []
        half_kernel = (self.kernel_size[0] // 2, self.kernel_size[1] // 2)

        for row in range(-half_kernel[0], half_kernel[0] + 1):
            for col in range(-half_kernel[1], half_kernel[1] + 1):
                    result.append((row, col))

        return result

    def get_valid_neighbor_idxs(self, idx, neighbor_idxs_relative):
        result = []
        result_relative = []
        for neighbor in neighbor_idxs_relative:
            candidate_neighbor = (idx[0] + neighbor[0], idx[1] + neighbor[1])
            if self.is_inbounds(candidate_neighbor):
                result.append(candidate_neighbor)
                result_relative.append(neighbor)

        return result, result_relative
    
    def get_neighbor_idxs(self, idx, neighbor_idxs_relative):
        result = []
        for neighbor in neighbor_idxs_relative:
            result.append((idx[0] + neighbor[0], idx[1] + neighbor[1]))
        return result

    def analyze_template(self):

        print('\nAnalyzing template...')

        if self.tileset is None:
            self.load_tileset()

        self.result = {'dims': self.template['dims'], 
                       'tileset_name': self.template['tileset_name'],
                       'data': {}}

        neighbor_idxs_relative = self.get_neighbor_relative_idxs()
        kernel_idxs = [(i, j) for j in range(self.kernel_size[1]) for i in range(self.kernel_size[0])]

        for idx, tile in self.template['data'].items():
            tile = tuple(tile)
            if tile not in self.result['data'].keys():
                self.result['data'][tile] = np.zeros((self.num_tiles_w_borders, 
                                                     self.kernel_size[0], 
                                                     self.kernel_size[1]), dtype=np.int32)

            neighbor_idxs = self.get_neighbor_idxs(idx, neighbor_idxs_relative)

            for i, neighbor in enumerate(neighbor_idxs):
                if not self.is_inbounds(neighbor):
                    continue
                neighbor_tile = self.template['data'][neighbor]

                # depth, row, col
                self.result['data'][tile][self.tile_id2idx(tuple(neighbor_tile)), kernel_idxs[i][0], kernel_idxs[i][1]] += 1
            
        for key in self.result['data'].keys():
            # JSON doesn't support numpy arrays and I don't care to write/use a custom encoder, 
            # so a list will do and I'll convert to numpy in WFC
            self.result['data'][key] = self.result['data'][key].tolist()
        
