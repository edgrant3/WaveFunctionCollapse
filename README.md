# WaveFunctionCollapse

This is a personal project inspired by a mention of this algorithm in some game dev/ computer graphics videos I stumbled upon. After watching [THIS VIDEO](https://youtu.be/rI_y2GAlQFM "The Coding Train") by The Coding Train, I decided to give it a shot! As a challenge I am currently not referencing any other code or implementation so I can practice my implementation of algorithms with only a high-level understanding of how I want them to work.

V3 Result Images:

![](smallmap1.png)

![](smallmap2.png)

![](smallmap3.png)

![](smallmap4.png)

V3 Video:

[![V3 Wave Function Collapse](V3.PNG)](https://youtu.be/Umz1vGyT-Lg "V3 Wave Function Collapse")

## Current Status and Usage
The final images are constructed from a small subset of images which I will call a "tileset". Small, pixel-perfect, and square images comprise the tileset and the user defines parameters such as sockets (strings respresenting a joining "key" along each edge of the tile), weighting, rotated variants, etc. in JSON files accompanying each tileset. `wfc.py` reads these JSON files to construct the tilset which the Wave Function Collapse algorithm then procedurally assembles into a larger image using matching rules between adjacent tile sockets.

Execute `wfc.py` in terminal (I'm running Python version 3.8.7) and press ESC key to avance through the 4 current tilesets.

Currently, I'm working on building a GUI to construct template images which will then be processed and used to determine adjacency probabilities for all tiles such that the final result contains better patterns and structure. The GUI produced by `template_image_GUI` already has many features implemented and currently looks like this:

![](InputImageGUI_V1.PNG)

TODO:

* Implement a system to analyze example input images which can detect patterns of tile arrangement and thus build more complex adjacency probabilities and more sophisticated structure in the final image

* Fix Tkinter keypress callback to accept other inputs than ESC

## Previous Version Videos:

V2 Video:

[![V2 Wave Function Collapse](V2.PNG)](https://youtu.be/H58Ugvk9nLc "V2 Wave Function Collapse")

V1 Video:

[![V1 Wave Function Collapse](V1.PNG)](https://youtube.com/shorts/JEJoIFABgiQ "V1 Wave Function Collapse")

## Definitions
Tile: an image with encoded information about how it can be assembled

Tileset: the full set of tiles, including all rotational variants

Patch Tile: A tile that will only be inserted into the image if no regular tiles satisfy the constraints at that point in the image. They can address unsolvable regions of the image which occur infrequently

## Log (5/9/23 start)

* 5/8/2023: Switch from graphics.py GraphWin to tkinter GUI builder for displaying output (individual draw calls are slower but has better documentation and flexibility for building out this resource as a tool for an artist)

* 5/17/2023: Augment seaweed tileset to be fully solvable. Repair `enforce_region()` function to enable setting a rectangular region of the map to a specific tile. Misc. bugfixes highlighted by trying to implement the seaweed tileset.



