Requirements: generate raster tiles for around 1000 GeoTIFFs
Tools: gdal2tiles  from GDAL (Geospatial Data Abstraction Library) included in the OSGeo4W suite (Open Source Geospatial Foundation for Windows). 

This project required that around a thousand GeoTIFFs be rendered into raster tiles for use on a web map. I began by processing files individually with command-line scripts. For each file, I used gdal's Translate tool to translate the file encoding to 8-bit (a prerequisite of the tiling process), and then I used gdal2tiles to render a tile set. In order to speed up the process of running both scripts, I incorporated them into my own Python script, which takes an entire folder of files, extracts the GeoTIFFs, translates them to bytes, and then transforms them into raster tiles. While this saved a considerable amount of time by eliminated the repeated work of manually running both scripts for each file, it also exposed another bottleneck in the process. 

It is required that the minimum and maximum tile zoom levels be specified when running the gdal2tiles script. However, it is not obvious what zoom level is optimum, and the amount of time that it takes to render a zoom level increases exponentially for each level - even if no more detail can be extracted from the original file. So, if you specify a maximum zoom level that is too high, you might end up having to wait hours for a single set of tiles to be created. My initial strategy for managing render depth was to run gdal2tiles once for each zoom level (instead of once for each map), measure how long it took to render the zoom level, and only continue to the next zoom level if the render time was under one minute. I had observed in my tests that the render time could increase from something like 3 minutes for one zoom level to 30 minutes for the next and then hours for the next. If every tile set took 30 minutes to render, the whole process would take over 20 days running non-stop. However, if every map took 3 minutes to render, the process would only take a couple days running non-stop. I knew this was not a perfect solution due to the possibility that fluctuations in my machine's available resources could cause some maps to take longer to render, causing inconsistencies in the resulting amount of detail retained from the original GeoTIFF. However, a random sample of a few hundred maps showed consistent enough results that I was confident most of our maps were rendered appropriately. 

Despite the satisfactory result of the first rendering, I was unable to produce the same result on a smaller set of subsequent GeoTIFFs. For some reason the gdal2tiles script was taking a significant amount of time to initialize the rendering process, which caused my script to abort rendering after only one zoom level. Between the first and second rendering sessions I devised what I believed to be an alternative approach to deciding the optimum maximum zoom level for each tile set. 

Since this project relies on the Open Street Map Slippy Map Tile Standard (aka XYZ tiles), I was able to rearrange the equation for determining the horizontal distance per pixel of a rendered XYZ tile in meters at a given integer zoom level to instead determine the float "zoom level" of a GeoTIFF given its original pixel width in meters, and then simply round up to the next integer zoom level as the maximum zoom level. This ensures that the full spatial resolution of the original GeoTIFF is rendered at the maximum zoom level of its resultant tiles. In other words, all of the available detail in the original GeoTIFF would be accessible in the web-map without wasting (exponentially more) time resampling the image for zoom levels that do not provide any additional visual detail. 

1. Variables:

    $ w = $ pixel width

    $ C = $ equatorial circumference of the earth in meters $= 40,075,016.686$

    $ l = $ latitude of the GeoTIFF in radians

    $ z = $ zoom level

1. [OSM equation for horizontal width per pixel given zoom level](https://wiki.openstreetmap.org/wiki/Zoom_levels#:~:text=Distance%20per%20pixel%20math):

    $ w = \frac{C \times \cos(l)}{2^{z+8}}$

1. Rearrangement of the equation:

    $w \times 2^{z+8} = C \times \cos(l)$

    $2^{z+8} = \frac{C \times \cos(l)}{w}$

    $log_{2}(2^{z+8}) = log_{2}(\frac{C \times \cos(l)}{w})$

    $z+8 = log_{2}(\frac{C \times \cos(l)}{w})$

1. Resultant equation (zoom level given pixel width):

    $z = log_{2}(\frac{C \times \cos(l)}{w}) - 8$


* ran basic scripts
* encapsulated scripts in bulk script
* 