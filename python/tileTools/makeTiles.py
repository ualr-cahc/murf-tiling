#! makeTiles validates/generates output directories, translates files to bytes,
# and generates tile ouputs

from tileTools.translate2bytes import translate2bytes
import os
from tileTools.calcTime import calcTime
from tileTools.writeLeaflet import writeLeaflet
import gdal2tiles
from time import perf_counter



@calcTime
def makeTiles(input_filepaths, tile_output_dir, translate_output_dir, tile_options, title):
    layers = {}
    if not os.path.isdir(tile_output_dir):
        os.makedirs(tile_output_dir)
    if not os.path.isdir(translate_output_dir):
        os.makedirs(translate_output_dir)

    # Translate 
    translate2bytes(input_filepaths, translate_output_dir)
    translated_filepaths = [os.path.join(translate_output_dir, file) for file in os.listdir(translate_output_dir)]

    for filepath in translated_filepaths:
        dirname = os.path.splitext(os.path.split(filepath)[-1])[0]
        dirpath = os.path.join(tile_output_dir, dirname)
        if not os.path.isdir(dirpath):
            os.makedirs(dirpath)
        for zoom_level in range(tile_options['zoom'][0], tile_options['zoom'][1]+1):
            print(f"zoom: {zoom_level} for {filepath}")
            current_tile_options = tile_options.copy()
            current_tile_options['zoom'] = [zoom_level, zoom_level]
            current_tile_options['resume'] = True
            time1 = perf_counter()
            gdal2tiles.generate_tiles(filepath, dirpath, **current_tile_options)
            time2 = perf_counter()
            time = time2-time1
            print("Tile time:", f"{time//60}m {round(time%60)}s")
            if time > 60:
                layers[dirname] = {'zoom_level': zoom_level}
                print()
                print("---------------------------------------------------------------------")
                print()
                break
            print()
            print("---------------------------------------------------------------------")
            print()
    leaflet_text = writeLeaflet(layers, max(layers.values()), title)       
    with open(os.path.join(tile_output_dir, "leaflet.html"), 'w') as file:
        file.write(leaflet_text)