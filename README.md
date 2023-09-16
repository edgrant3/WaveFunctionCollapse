# WaveFunctionCollapse

## CURRENTLY REFACTORING `wfc.py` AND `wfc_fromtemplate.py`

This is a personal project inspired by a mention of this algorithm in some game dev/ computer graphics videos I stumbled upon. After watching [THIS VIDEO](https://youtu.be/rI_y2GAlQFM "The Coding Train") by The Coding Train, I decided to give it a shot! As a challenge I am currently not referencing any other code or implementation so I can practice my implementation of algorithms with only a high-level understanding of how I want them to work.

The core idea of this algorithm is to procedurally generate a large image from a small set of "tiles" - small, square images which can be assembled together based on a set of rules about edge continuity or adjacency probabilities. 

I have created 4 custom tilesets which can be found in the `assets` directory. Each tile is a 15x15 or 16x16 pixel image (though they may be any desired size greater than 2x2), and has certain user-generated properties recorded in an accompanying JSON file for the tileset (not the JSON with "template" in the name). This data includes an alphabetic string "socket" for each edge of the tile which is a matching key for adjacent tiles with corresponding sockets. The JSON also encodes the number of rotational variants a tile has, the arbitrary "weight" which effects how often that tile will be selected by the algorithm when many tile options are present, whether the tile should only be used to "patch" unsolvable regions of the image (which rarely happens with a well-designed tileset), and an "ignore" flag which allows the user to omit tiles.

V3 Result Images:

![](captures/smallmap1.png)

![](captures/smallmap2.png)

![](captures/smallmap3.png)

![](captures/smallmap4.png)

V3 Video:

[![V3 Wave Function Collapse](captures/V3.PNG)](https://youtu.be/Umz1vGyT-Lg "V3 Wave Function Collapse")

## Current Status and Usage

To implement your own tileset, first create a series of images which can be reasonably assembled. Then, copy a JSON (one without "template" in the name) from an existing tileset's directory and enter the information corrsponding to your specific tiles. Then, add your tileset via the main function at the bottom of `wfc.py`. Finally, execute `wfc.py` (I'm running Python version 3.8.7) and press ESC key to avance through all the tilesets.

NOTES:

* "rotations": `[0]` means that the image will have no rotated versions and the program will not create more tiles. `[0, 1]` means there is a 90-degree clockwise-rotated version in addition to the original and a secondary tile will thus be created. `[0, 1, 2, 3]` is the maximum number of rotations, and 3 additional rotated versions of the tile will be created at 90-degree increments.

* "sockets": These can be arbitrarily-long strings (though more than 3-4 characters gets very difficult to make a complete set for), where each letter corresponds to a color or set of pixels which can match up with the edge of another tile (e.g. sand to sand, grass to grass). Most Importantly, the sockets start with the "North" edge of the tile and should be ordered as if you are moving clockwise around the edges of the tile.


Currently, I'm working on building a GUI to construct template images which will then be processed and used to determine adjacency probabilities for all tiles such that the final result contains better patterns and structure. The GUI produced by the  `TemplateBuilder_GUI` class already has many features implemented and currently looks like this:

![](captures/InputImageGUI_V2.PNG)

## Log (5/9/23 start)

* 5/8/2023: Switch from graphics.py GraphWin to tkinter GUI builder for displaying output (individual draw calls are slower but has better documentation and flexibility for building out this resource as a tool for an artist)

* 5/17/2023: Augment seaweed tileset to be fully solvable. Repair `enforce_region()` function to enable setting a rectangular region of the map to a specific tile. Misc. bugfixes highlighted by trying to implement the seaweed tileset.

* 5/24/2023: Build skeleton for template image GUI in separate tkinter-based class.

* 9/15/2023: Refactored project with better OOP principles. Moved and improved `Tile` class and implemented `TileSet`, `Template`, and `TemplateAnalyzer` classes. Updated`TemplateBuilder_GUI` to offload non-GUI processes to TileSet class and fixed several bugs that improve GUI usage when scaling. Standardized indices convention to be (x,y), (col, row), (horizontal, vertical) everywhere in the project. Improved saving and loading of templates and started using integer IDs for template data dictionaries. Made `WFC` compatible with all the above changes. Next steps: make `wfc_fromtemplate` compatible with above changes and fix bugs. Currently brainstorming more sophisticated algorithm for applying analyzed templates.



TODO:

* Implement a system to analyze example input images which can detect patterns of tile arrangement and thus build more complex adjacency probabilities and more sophisticated structure in the final image

* Fix Tkinter keypress callback to accept other inputs than ESC

## Previous Version Videos:

V2 Video:

[![V2 Wave Function Collapse](captures/V2.PNG)](https://youtu.be/H58Ugvk9nLc "V2 Wave Function Collapse")

V1 Video:

[![V1 Wave Function Collapse](captures/V1.PNG)](https://youtube.com/shorts/JEJoIFABgiQ "V1 Wave Function Collapse")

## Definitions
Tile: an image with encoded information about how it can be assembled

Tileset: the full set of tiles, including all rotational variants

Patch Tile: A tile that will only be inserted into the image if no regular tiles satisfy the constraints at that point in the image. They can address unsolvable regions of the image which occur infrequently



