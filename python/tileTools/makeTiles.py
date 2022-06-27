#! makeTiles validates/generates output directories, translates files to bytes,
# and generates tile ouputs

from importlib.resources import path
import os
from pathlib import Path
from typing import Iterable
from osgeo_utils import gdal2tiles
from tileTools.calcTime import calcTime
from tileTools.translate2bytes import translate2bytes
from tileTools.dbConnect import dbConnect
import traceback
from osgeo.gdal import GDT_Byte, Translate
from shutil import rmtree


dbKwargs = {
    'dbpassword': input("dbpassword: "),
    'database': 'tiling',
    'autocommit': True
}

@calcTime
def makeTiles(input_filepaths: list[str], base_output_dir: str, min_zoom: int, max_zoom: int):
    """Primary function for the makeTiles module. Takes a list
    of filepaths to TIFFs, the path to an output directory,
    and minimum and maximum zoom values. 
    """
    input_filepaths = [os.path.normpath(filepath) for filepath in input_filepaths]
    base_output_dir = os.path.normpath(base_output_dir)
    translate_output_dir = os.path.normpath(os.path.join(base_output_dir, "translated"))
    tile_output_dir = os.path.normpath(os.path.join(base_output_dir, "tiles"))
    if not os.path.isdir(tile_output_dir):
        os.makedirs(tile_output_dir)
    if not os.path.isdir(translate_output_dir):
        os.makedirs(translate_output_dir)
    translated_filepaths = [os.path.join(translate_output_dir, file) for file in os.listdir(translate_output_dir)]
    db_batch = dbConnect(**dbKwargs)
    db_insert = dbConnect(**dbKwargs)
    
    cursor_batch = db_batch.cursor()
    cursor_batch.execute(f"INSERT INTO batch (outputdir, minzoom, maxzoom) VALUES ({base_output_dir}, {min_zoom}, {max_zoom});")
    db_batch.commit()
    cursor_batch.execute("SELECT id FROM batch ORDER BY id DESC LIMIT 1;")
    batch_id = cursor_batch.fetchone()[0]
    cursor_batch.close()

    for input_filepath in input_filepaths:
        input_filepath = os.path.normpath(input_filepath)
        cursor_insert = db_insert.cursor()
        filename = os.path.split(input_filepath)[-1]
        layer_name = os.path.splitext(filename)[0]
        translated_filepath = os.path.join(translate_output_dir, filename)
        if translated_filepath not in translated_filepaths:
            cursor_insert.execute(f"INSERT INTO translates (batch_id, layer_name) VALUES ({batch_id}, {layer_name});")
            db_insert.commit()
            try:
                duration, _ = calcTime(Translate(translated_filepath, input_filepath, GDT_Byte))
            except KeyboardInterrupt:
                os.remove(translated_filepath)
                raise KeyboardInterrupt
            except:
                error = traceback.format_exc()
                cursor_insert.execute(f"UPDATE translates SET error={error} WHERE (batch_id={batch_id} AND layer_name={layer_name});")
                db_insert.commit()
                break
            cursor_insert.execute(f"UPDATE translates SET duration={duration} WHERE (batch_id={batch_id} AND layer_name={layer_name});")
            db_insert.commit()

        if not os.path.exists(output_dirpath):
            output_dirpath = os.path.join(tile_output_dir, layer_name)
        if not os.path.isdir(output_dirpath):
            os.makedirs(output_dirpath)
            try:
                duration, _ = makeTileLayer(translated_filepath, output_dirpath, min_zoom, max_zoom, batch_id, layer_name)
            except KeyboardInterrupt:
                rmtree(output_dirpath)
                cursor_insert.execute(f"DELETE FROM tilesets WHERE batch_id={batch_id} AND layer_name={layer_name}")
                db_insert.commit()
                raise KeyboardInterrupt
            cursor_insert.execute(f"INSERT INTO tilelayers (batch_id, layer_name, duration) VALUES ({batch_id}, {layer_name}, {duration}")
            db_insert.commit()
            cursor_insert.close()
        else:
            print("Skipped:", filename)
        

@calcTime
def makeTileLayer(translated_filepath: str, output_dirpath: str, min_zoom: int, max_zoom: int, batch_id, layer_name):
    for zoom_level in range(min_zoom, max_zoom+1):
        args = ['gdal2tiles.py', '-z', f"{zoom_level}-{zoom_level}", '-e', '--processes=8', '--xyz', translated_filepath, output_dirpath]
        db_tileset = dbConnect(dbKwargs)
        cursor_tileset = db_tileset.cursor()
        cursor_tileset.execute(f"INSERT INTO tilesets (batch_id, layer_name, zoom) VALUES ({batch_id}, {layer_name}, {zoom_level}")
        try:
            tiletime, _ = calcTime(gdal2tiles.main(args))
            if tiletime > 60000000000:
                
                """layers[dirname] = zoom_level"""
                break
        except Exception as err:
            # log error
            print(err)
            err = traceback.format_exc()
        
