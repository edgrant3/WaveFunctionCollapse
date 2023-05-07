# WaveFunctionCollapse

V1 Video:

[![V1 Wave Function Collapse](V1.PNG)](https://youtube.com/shorts/JEJoIFABgiQ "V1 Wave Function Collapse")

This is a personal project inspired by a mention of this algorithm in some game dev/ computer graphics videos I stumbled upon. After watching [THIS VIDEO](https://youtu.be/rI_y2GAlQFM "The Coding Train") by The Coding Train, I decided to give it a shot! As a challenge I am currently not referencing any other code or implementation so I can practice my implementation of algorithms with only a high-level understanding of how I want them to work.

### Current Status and Usage
The final images are constructed from a small subset of images which I will call a "tileset". Small, pixel-perfect, and square images comprise the tileset and the user defines parameters such as sockets (strings respresenting a joining "key" along each edge of the tile), weighting, rotated variants, etc. in JSON files accompanying each tileset. `wfc.py` reads these JSON files to construct the tilset which the Wave Function Collapse then procedurally assembles into a larger image using matching rules between adjacent tile sockets.

### Definitions
Tile: an image with encoded information about how it can be assembled
Tileset: the full set of tiles, including all rotational variants
Patch Tile: A tile that will only be inserted into the image if no regular tiles satisfy the constraints at that point in the image. They can address unsolvable regions of the image which occur infrequently

