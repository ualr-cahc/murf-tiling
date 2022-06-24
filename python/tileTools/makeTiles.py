#! makeTiles validates/generates output directories, translates files to bytes,
# and generates tile ouputs

from tileTools.translate2bytes import translate2bytes
import os
from tileTools.calcTime import calcTime
from osgeo_utils import gdal2tiles
import mysql.connector

def dbConnect(password, database):

    db = mysql.connector.connect(
        host='localhost',
        user="python",
        password=password,
        database=database
    )

    return db

@calcTime
def gdal2tiles_timed(args):
    gdal2tiles.main(args)

@calcTime
def makeTiles(input_filepaths, base_output_dir, tile_options):
    """if title == '':
        title = os.path.split(input_filepaths[0])[1]
    layers = {}"""
    base_output_dir = os.path.normpath(base_output_dir)
    translate_output_dir = os.path.join(base_output_dir, "translated")
    tile_output_dir = os.path.join(base_output_dir, "tiles")
    if not os.path.isdir(tile_output_dir):
        os.makedirs(tile_output_dir)
    if not os.path.isdir(translate_output_dir):
        os.makedirs(translate_output_dir)

    # Translate 
    print(input_filepaths, translate_output_dir)
    translate2bytes(input_filepaths, translate_output_dir)
    translated_filepaths = [os.path.join(translate_output_dir, file) for file in os.listdir(translate_output_dir)]

    for filepath in 


    for filepath in translated_filepaths:
        filepath = os.path.normpath(filepath)
        dirname = os.path.splitext(os.path.split(filepath)[-1])[0]
        output_dirpath = os.path.join(tile_output_dir, dirname)
        time = makeTileLayer(filepath, dirname, output_dirpath, tile_options)

            
    """if len(layers) < 1:
        layers[dirname] = tile_options['zoom'][1]
    leaflet_text = writeLeaflet(layers, max(layers.values()), title) 
    with open(os.path.join(tile_output_dir, "leaflet.html"), 'w') as file:
        file.write(leaflet_text)"""
    

@calcTime
def makeTileLayer(filepath, dirname, output_dirpath, tile_options):
    if not os.path.isdir(output_dirpath):
        os.makedirs(output_dirpath)
    for zoom_level in range(tile_options['zoom'][0], tile_options['zoom'][1]+1):
        print(f"zoom: {zoom_level} for {filepath}")
        current_tile_options = tile_options.copy()
        current_tile_options['zoom'] = [zoom_level, zoom_level]
        args = ['gdal2tiles.py', '-z', f"{zoom_level}-{zoom_level}", '-e', '--processes=8', '--xyz', filepath, output_dirpath]
        time = gdal2tiles_timed(args)
        if time > 60000000000:
            """layers[dirname] = zoom_level"""
            break