import numpy as np
import json

import tile      

class Template():
    def __init__(self, tileset_name, height=15, width=15) -> None:
        self.tileset = tile.TileSet(tileset_name)
        self.h            = height         # int: height of template grid
        self.h_max        = 30
        self.w            = width          # int: width  of template grid
        self.w_max        = 30
        self.data_raw     = np.ones((width, height)) # 2D nparray: integer representation of tile grid
        self.data_encoded = {}             # dict: encoded probabilities after analyzing
        self.analyzer = TemplateAnalyzer(self)

        self.tileset.generate()
        self.data_raw *= self.tileset.idANDidx[(-1, 0)]

    def clear_rawdata(self):
        self.data_raw = np.ones((self.w, self.h)) * self.tileset.idANDidx[(-1, 0)]

    def clear_data(self):
        self.clear_rawdata()
        self.data_encoded.clear()
    
    def resize(self, new_w, new_h):
        new_w = min(new_w, self.w_max)
        new_h = min(new_h, self.h_max)
        new_data = np.ones((new_w, new_h)) * self.tileset.idANDidx[(-1, 0)]
        w_slice_idx = min(self.w, new_w)
        h_slice_idx = min(self.h, new_h)
        new_data[0:w_slice_idx, 0:h_slice_idx] = self.data_raw[0:w_slice_idx, 0:h_slice_idx]
        self.data_raw = new_data
        self.w = new_w
        self.h = new_h

    def save(self, file):
        'Saves template to JSON file'
        self.analyze((9,9), False) 
        json_template = {}
        json_template["tileset_name"] = self.tileset.name
        json_template["height"] = self.h
        json_template["width"] = self.w
        json_template["data"] = self.data_raw.astype(int).tolist()
        json_template["analyzed_template"] = {}
        json_template["analyzed_template"]["data"] = self.data_encoded
        json_template["analyzed_template"]["kernel size"] = self.analyzer.kernel_size
        json.dump(json_template, file, indent=2)

    def load(self, filename):
        loaded_template   = json.load(open(filename))
        self.tileset.name = loaded_template["tileset_name"]
        self.h            = loaded_template["height"]
        self.w            = loaded_template["width"]
        self.data_raw     = np.array(loaded_template["data"]).astype(int)
        # self.data_encoded = loaded_template["analyzed_template"]["data"]
        self.data_encoded = {int(float(key)): np.array(val).astype(int) for key, val in loaded_template["analyzed_template"]["data"].items()}
        print(self.data_encoded.keys())
        self.analyzer.set_kernel_size(loaded_template["analyzed_template"]["kernel size"])

        self.tileset.generate()
        print(f'Successfully loaded Template from \n{filename}\n')

    def analyze(self, kernel_size, include_borders):
        self.analyzer.set_kernel_size(kernel_size)
        self.analyzer.include_borders = include_borders
        self.analyzer.run()



class TemplateAnalyzer():
    def __init__(self, template, kernel_size=(5,5), include_borders=False):
        self.template = template # Template instance
        self.set_kernel_size(kernel_size) # tuple: (h,w)
        self.include_borders = include_borders # bool: TODO: add border behavior
        self.relative_neighbor_idxs, self.kernel_idxs = self.get_neighbor_relative_idxs()

    def set_kernel_size(self, size):
        '''overwrites self.kernel_size with input tuple 'size' contents which are raised to nearest odd integer vals'''
        new_size = [size[0], size[1]]
        for i, dim in enumerate(new_size):
            new_size[i] = dim if dim % 2 == 1 else dim + 1

        self.kernel_size = (new_size[0], new_size[1])
        self.relative_neighbor_idxs, self.kernel_idxs = self.get_neighbor_relative_idxs()

    def get_neighbor_relative_idxs(self):
        '''Get the (row, col) coords of neighbors relative to current idx'''
        half_kernel = (self.kernel_size[0] // 2, self.kernel_size[1] // 2)
        idxs = []
        
        for col in range(-half_kernel[0], half_kernel[0] + 1):
            for row in range(-half_kernel[1], half_kernel[1] + 1):
                idxs.append((col, row))

        kernel_idxs = [(i, j) for j in range(self.kernel_size[1]) for i in range(self.kernel_size[0])]

        return idxs, kernel_idxs
    
    def get_neighbor_idxs(self, idx):
        result = []
        for neighbor in self.relative_neighbor_idxs:
            result.append((idx[0] + neighbor[0], idx[1] + neighbor[1]))
        return result

    def is_inbounds(self, idx):
        '''Check (row, col) idx to see if it is in grid bounds'''
        return (idx[0] >= 0 and idx[0] < self.template.w and
                idx[1] >= 0 and idx[1] < self.template.h)
    
    def run(self):
        print('Analyzing template...')

        # relative_neighbor_idxs, kernel_idxs = self.get_neighbor_relative_idxs()
        # kernel_idxs = [(i, j) for j in range(self.kernel_size[1]) for i in range(self.kernel_size[0])]
        self.template.data_encoded.clear()

        for col in range(self.template.w):
            for row in range(self.template.h):
                tile_idx = self.template.data_raw[col, row]
                # BIG TODO: get this working with wfc_fromtemplate2.py
                # currently fails because 

                # for id in self.template.tileset.tiles.keys():
                #     idx = self.template.tileset.idANDidx[id]
                #     self.template.data_encoded[idx] = np.zeros((self.template.tileset.count,
                #                                                 self.kernel_size[0],
                #                                                 self.kernel_size[1]))
                if tile_idx not in self.template.data_encoded.keys():
                    self.template.data_encoded[tile_idx] = np.zeros((self.template.tileset.count,
                                                                     self.kernel_size[0],
                                                                     self.kernel_size[1]))

                neighbor_idxs = self.get_neighbor_idxs((col, row))

                for i, neighbor in enumerate(neighbor_idxs):
                    if not self.is_inbounds(neighbor):
                        continue
                    neighbor_tile_idx = self.template.data_raw[neighbor]
                    # depth, col, row
                    self.template.data_encoded[tile_idx][int(neighbor_tile_idx), 
                                                         self.kernel_idxs[i][0], 
                                                         self.kernel_idxs[i][1]] += 1

        for key in self.template.data_encoded.keys():
            # JSON doesn't support numpy arrays and I don't care to write/use a custom encoder, 
            # so a list will do and I'll convert to numpy in WFC
            self.template.data_encoded[key] = self.template.data_encoded[key].astype(int).tolist()
