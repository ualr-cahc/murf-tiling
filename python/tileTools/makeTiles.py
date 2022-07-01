#! makeTiles validates/generates output directories, translates files to bytes,
# and generates tile ouputs

import os
from osgeo_utils import gdal2tiles
from tileTools.calcTime import calcTime
from tileTools.dbConnect import dbConnect
import traceback
from osgeo.gdal import GDT_Byte, Translate
from shutil import rmtree
import logging

logging.basicConfig(level=logging.INFO)

dbKwargs = {
    'password': "POIUpoiu)(*&0987",
    'database': 'murf_tiling'
}

@calcTime
def translate2bytes(translated_file_path, input_filepath):
        Translate(translated_file_path, input_filepath, outputType=GDT_Byte)

@calcTime
def tile(args):
    gdal2tiles.main(args)

class Table:
    """object for inserting, updating, deleting from a table"""

    def __init__(self, table_name):
        self.db = dbConnect(**dbKwargs)
        self.table_name = table_name

    def insert(self, items_to_insert: dict):
        """insert items into table"""
        keys = ", ".join(f"{key}" for key in items_to_insert.keys())
        values = ", ".join(f"%s" for value in range(len(items_to_insert)))
        statement = f"INSERT INTO {self.table_name} ({keys}) VALUES ({values});"
        params = tuple(items_to_insert.values())
        logging.debug(str(params))
        self.execute_statement(statement, params)

    def update(self, to_update: dict, key: dict):
        keys = " AND ".join(f"{key}=%s" for key, value in key.items())
        sets = ", ".join(f"{key}=%s" for key, value in to_update.items())
        statement = f"UPDATE {self.table_name} SET {sets} WHERE {keys};"
        params = tuple(to_update.values()) + tuple(key.values())
        self.execute_statement(statement, params)

    def delete(self, key: dict):
        keys = " AND ".join(f"{key}={value}" for key, value in key.items())
        statement = f"DELETE FROM {self.table_name} WHERE {keys};"
        self.execute_statement(statement)

    
    def execute_statement(self, statement: str, params):
        """handles cursor and commits changes"""
        cursor = self.db.cursor()
        logging.debug(f"{statement, params}")
        cursor.execute(statement, params)
        self.db.commit()
        cursor.close()


class Batch(Table):
    """object for batch table"""

    def __init__(self):
        self.table_name = 'batch'
        self.db = dbConnect(**dbKwargs)

    def get_id(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT id FROM batch ORDER BY id DESC LIMIT 1;")
        self.id = cursor.fetchone()[0]
        cursor.close()

class DatabaseCloser:
    def __init__(self, *objects):
        self.objects = objects
    
    def close(self):
        for object in self.objects:
            object.db.close()


@calcTime
def makeTileLayer(translated_file_path: str, layer_output_dir: str, min_zoom: int, max_zoom: int, batch_id, layer_name, tile_sets):
    for zoom_level in range(min_zoom, max_zoom+1):
        logging.debug(f"zoom_level: {zoom_level}")
        args = ['gdal2tiles.py', '-z', f"{zoom_level}-{zoom_level}", '-e',
                '--processes=8', '--xyz', translated_file_path, layer_output_dir]
        tile_set_key = {
            'batch_id': batch_id,
            'layer_name': layer_name,
            'zoom': zoom_level
        }
        logging.debug(f"tile_set_key: {tile_set_key}")
        tile_sets.insert(tile_set_key)
        try:
            duration = tile(args)
            tile_sets.update({'duration': duration}, tile_set_key)
            # if it takes longer than one minute to render a set,
            # don't move on to the next zoom level for this layer
            if duration > 60000000000:
                """layers[dirname] = zoom_level"""
                return
        except KeyboardInterrupt:
            connections.close()
            raise KeyboardInterrupt
        except Exception:
            # log error
            error = traceback.format_exc().replace('\n', '    ')
            tile_sets.update({'error': f"{error}"}, tile_set_key)


@calcTime
def makeTiles(input_filepaths: list[str], base_output_dir: str, min_zoom: int, max_zoom: int):
    """Primary function for the makeTiles module. Takes a list
    of filepaths to TIFFs, the path to an output directory,
    and minimum and maximum zoom values. 
    """
    global connections

    input_filepaths = [os.path.normpath(filepath) for filepath in input_filepaths]
    base_output_dir = os.path.normpath(base_output_dir)
    translate_output_dir = os.path.normpath(os.path.join(base_output_dir, "translated"))
    tile_output_dir = os.path.normpath(os.path.join(base_output_dir, "tiles"))
    if not os.path.isdir(tile_output_dir):
        os.makedirs(tile_output_dir)
    if not os.path.isdir(translate_output_dir):
        os.makedirs(translate_output_dir)
    translated_file_paths = [
        os.path.join(translate_output_dir, file) for file in os.listdir(translate_output_dir)
    ]
    
    # if an unhandled exception occurs, close databases
    try:
        batch = Batch()
        translation = Table('translation')
        tile_sets = Table('tile_sets')
        tile_layers = Table('tile_layers')
        connections = DatabaseCloser(batch, translation, tile_sets, tile_layers)
        batch.insert({"output_dir": base_output_dir})
        batch.get_id()
        for input_filepath in input_filepaths:
            logging.debug(input_filepath)
            input_filepath = os.path.normpath(input_filepath)
            filename = os.path.split(input_filepath)[-1]
            layer_name = os.path.splitext(filename)[0]
            translated_file_path = os.path.join(translate_output_dir, filename)
            layer_output_dir = os.path.join(tile_output_dir, layer_name)
            
            translation_key = {
                    'batch_id': batch.id,
                    'layer_name': layer_name
                }
            translation.insert(translation_key)   

            # only try to translate a file if the 
            # translated file doesn't already exist
            if translated_file_path not in translated_file_paths:
                # Try to translate, and log errors without exiting.
                # Some layers won't translate due to problems with the file.
                try:
                    duration = translate2bytes(translated_file_path, input_filepath)
                except KeyboardInterrupt:
                    connections.close()
                    raise KeyboardInterrupt
                except: 
                    error = traceback.format_exc().replace('\n', '    ')
                    update = {'error': f'"{error}"'}
                    translation.update(update, translation_key)
                    # If an error occurs in translation 
                    # stop trying to process this input file
                    # and move on to the next
                    break
                
                # If no translate errors occurred, log the duration
                # and move on to creating the tile layer
                translation.update({'duration': duration}, translation_key)
            else:
                translation.update({'already_exists': 1}, translation_key)
            
            # only try to render layer if it doesn't already exist
            if not os.path.isdir(layer_output_dir):  
                os.makedirs(layer_output_dir)   
                tile_layers_key = {
                    'batch_id': batch.id,
                    'layer_name': layer_name
                }
                logging.debug(f"tile_layers_key {tile_layers_key}")
                tile_layers.insert(tile_layers_key)
                try:
                    logging.debug(f"Trying to make tile layer for {layer_name}")
                    duration = makeTileLayer(
                        translated_file_path, layer_output_dir, min_zoom,
                        max_zoom, batch.id, layer_name, tile_sets
                    )
                except KeyboardInterrupt:
                    connections.close()
                    rmtree(layer_output_dir)
                    raise KeyboardInterrupt
                except:
                    error = traceback.format_exc()
                    tile_layers.update({'error': f"{error}"}, tile_layers_key)
                    rmtree(layer_output_dir)
                    tile_sets_key = {
                        'batch_id': batch.id,
                        'layer_name': layer_name
                    }
                    tile_sets.update({"deleted": 1}, tile_sets_key)
                tile_layers.update({'duration': duration}, tile_layers_key)
            
            # If the file already exists, 
            else:
                print("Skipped:", filename)
    # if an unhandled exception occurs, close databases
    except Exception as error:
        connections.close()
        raise error    
    connections.close()
