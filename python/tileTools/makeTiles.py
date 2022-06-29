#! makeTiles validates/generates output directories, translates files to bytes,
# and generates tile ouputs

import os
from osgeo_utils import gdal2tiles
from tileTools.calcTime import calcTime
from tileTools.dbConnect import dbConnect
import traceback
from osgeo.gdal import GDT_Byte, Translate
from shutil import rmtree


dbKwargs = {
    'password': input("dbpassword: "),
    'database': 'murf_tiling'
}


class Table:
    """object for inserting, updating, deleting from a table"""

    def __init__(self, table_name):
        self.db = dbConnect(**dbKwargs)
        self.table_name = table_name

    def insert(self, items_to_insert):
        keys = ", ".join(f"{key}" for key in items_to_insert.keys())
        values = ", ".join(f"'{value}'" for value in items_to_insert.values())
        statement = f"INSERT INTO {self.table_name} ({keys}) VALUES ({values});"
        self.execute(statement)

    def update(self, update, where):
        sets = ", ".join(f"{key}={value}" for key, value in update.items())
        wheres = " AND ".join(f"{key}={value}" for key, value in where.items())
        statement = f"UPDATE {self.table_name} SET {sets} WHERE {wheres};"
        self.execute(statement)

    def delete(self, where):
        wheres = " AND ".join(f"{key}={value}" for key, value in where.items())
        statement = f"DELETE FROM {self.table_name} WHERE {wheres};"
        self.execute(statement)

    def execute(self, statement):
        print(statement)
        cursor = self.db.cursor()
        cursor.execute(statement)
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


@calcTime
def makeTileLayer(translated_filepath: str, output_dirpath: str, min_zoom: int, max_zoom: int, batch_id, layer_name, tile_sets):
    for zoom_level in range(min_zoom, max_zoom+1):
        args = ['gdal2tiles.py', '-z', f"{zoom_level}-{zoom_level}", '-e',
                '--processes=8', '--xyz', translated_filepath, output_dirpath]
        tile_set_key = {
            'batch_id': batch_id,
            'layer_name': layer_name,
            'zoom': zoom_level
        }
        tile_sets.insert(tile_set_key)
        try:
            duration, _ = calcTime(gdal2tiles.main(args))
            tile_sets.update({'duration': duration}, tile_set_key)
            if duration > 60000000000:
                """layers[dirname] = zoom_level"""
                break
        except Exception as error:
            # log error
            error = traceback.format_exc().replace('\n', '    ')
            tile_sets.update({'error': f"{error}"}, tile_set_key)


@calcTime
def makeTiles(input_filepaths: list[str], base_output_dir: str, min_zoom: int, max_zoom: int):
    """Primary function for the makeTiles module. Takes a list
    of filepaths to TIFFs, the path to an output directory,
    and minimum and maximum zoom values. 
    """
    input_filepaths = [os.path.normpath(filepath)
                       for filepath in input_filepaths]
    base_output_dir = os.path.normpath(base_output_dir)
    translate_output_dir = os.path.normpath(
        os.path.join(base_output_dir, "translated"))
    tile_output_dir = os.path.normpath(os.path.join(base_output_dir, "tiles"))
    if not os.path.isdir(tile_output_dir):
        os.makedirs(tile_output_dir)
    if not os.path.isdir(translate_output_dir):
        os.makedirs(translate_output_dir)
    translated_filepaths = [
        os.path.join(translate_output_dir, file) for file in os.listdir(translate_output_dir)
    ]
    batch = Batch()
    translation = Table('translation')
    tile_sets = Table('tile_sets')
    tile_layers = Table('tile_layers')
    try:
        batch.insert({"output_dir": base_output_dir})
        batch.get_id()
        for input_filepath in input_filepaths:

            input_filepath = os.path.normpath(input_filepath)
            filename = os.path.split(input_filepath)[-1]
            layer_name = os.path.splitext(filename)[0]
            translated_filepath = os.path.join(translate_output_dir, filename)

            if translated_filepath not in translated_filepaths:
                translation_key = {
                    'batch_id': batch.id,
                    'layer_name': layer_name
                }
                translation.insert(translation_key)
                try:
                    duration, _ = calcTime(
                        Translate(translated_filepath, input_filepath, outputType=GDT_Byte)
                    )
                except KeyboardInterrupt:
                    os.remove(translated_filepath)
                    raise KeyboardInterrupt
                except:
                    error = traceback.format_exc()
                    update = {'error': f'"{error}"'}
                    translation.update(update, translation_key)
                    break
                update = {'duration': duration}
                translation.update(update, translation_key)

            output_dirpath = os.path.join(tile_output_dir, layer_name)

            if not os.path.isdir(output_dirpath):
                os.makedirs(output_dirpath)
                tile_layers_key = {
                    'batch_id': batch.id,
                    'layer_name': layer_name
                }
                tile_layers.insert(tile_layers_key)
                try:
                    duration, _ = makeTileLayer(
                        translated_filepath, output_dirpath, min_zoom,
                        max_zoom, batch.id, layer_name, tile_sets
                    )
                except KeyboardInterrupt:
                    rmtree(output_dirpath)
                    where = {
                        'batch_id': batch.id,
                        'layer_name': layer_name
                    }
                    tile_sets.delete(where)
                    raise KeyboardInterrupt
                tile_layers.update({'duration': duration}, tile_layers_key)
            else:
                print("Skipped:", filename)
    except Exception as error:
        batch.db.close()
        translation.db.close()
        tile_sets.db.close()
        tile_layers.db.close()
        raise error
    batch.db.close()
    translation.db.close()
    tile_sets.db.close()
    tile_layers.db.close()

    