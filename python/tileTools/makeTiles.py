#! makeTiles validates/generates output directories, translates files to bytes,
# and generates tile ouputs

from tileTools.translate2bytes import translate2bytes
import os
from tileTools.filterTiffs import filterTiffs
from tileTools.calcTime import calcTime
import gdal2tiles
from time import perf_counter



@calcTime
def makeTiles(input_filepaths, tile_output_dir, translate_output_dir, tile_options):
    if not os.path.isdir(tile_output_dir):
        os.mkdir(tile_output_dir)
    if not os.path.isdir(translate_output_dir):
        os.mkdir(translate_output_dir)

    # Translate 
    translate2bytes(input_filepaths, translate_output_dir)
    translated_filepaths = [os.path.join(translate_output_dir, file) for file in os.listdir(translate_output_dir)]

    for filepath in translated_filepaths:
        dirname = os.path.splitext(os.path.split(filepath)[-1])[0]
        dirpath = os.path.join(tile_output_dir, dirname)
        if not os.path.isdir(dirpath):
            os.mkdir(dirpath)
        for zoom_level in range(tile_options['zoom'][0], tile_options['zoom'][1]+1):
            print(f"zoom: {zoom_level} for {filepath}")
            current_tile_options = tile_options.copy()
            current_tile_options['zoom'] = [zoom_level, zoom_level]
            time1 = perf_counter()
            gdal2tiles.generate_tiles(filepath, dirpath, **current_tile_options)
            time2 = perf_counter()
            time = time2-time1
            print("Tile time:", f"{time//60}m {round(time%60)}s")
            if time//60 > 1:
                break