"""Create XYZ tile layers for a list of GeoTIFFs. 
"""

import os
from shutil import rmtree
import logging
from time import perf_counter_ns
from pathlib import Path
import traceback
from math import log2, cos, radians, ceil

import rasterio

from osgeo_utils import gdal2tiles
from osgeo.gdal import GDT_Byte, Translate

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

def _make_tile_layer(translated_file_path: str|Path, 
                     layer_output_dir: str|Path, 
                     min_zoom: int, 
                     max_zoom: int, 
                     processes=os.processes, 
                     xyz=True):
    
    with rasterio.open(translated_file_path) as raster:
        if isinstance(raster.transform, rasterio.Affine):
            original_pixel_width = (
                (raster.bounds.right + raster.bounds.left) / raster.width
            )
            earth_diameter = 40075016.686
            max_zoom = ceil(log2(earth_diameter * cos(radians(34.74)) / original_pixel_width) - 8)
        else:
            logging.info(f"Non-Affine transform type used: {type(raster.transform)}. Defaulting to supplied max_zoom: {max_zoom}.")
    
    args = ['gdal2tiles.py', '-z', f"{min_zoom}-{max_zoom}", '-e',
            f'--processes={processes}']
    if xyz:
        args.append("--xyz")
    args += [str(translated_file_path), str(layer_output_dir)]
    
    try:

        begin = perf_counter_ns()
        logging.debug(f"tiling: {args}")
        gdal2tiles.main(args)
        # if it takes longer than one minute to render a set,
        # don't move on to the next zoom level for this layer
        end = perf_counter_ns()
        duration = end-begin
        logging.info(f"Zoom {min_zoom}-{max_zoom} tile time: {duration/1000000000} seconds")
        
    except Exception:
        # log error
        error = traceback.format_exc()
        logging.debug(error)

def validate_paths(*paths: Path):
    """if path doesn't exist, make it"""
    for path in paths:
        if not path.exists():
            os.makedirs(path)
        elif path.is_file():
            raise ValueError(f"trying to write output to directory that is actually a file {path}")

def makeTiles(input_filepaths: list[str]|list[Path], base_output_dir: str|Path, min_zoom: int, max_zoom: int):
    """Primary function for the makeTiles module. Takes a list
    of filepaths to TIFFs, the path to an output directory,
    and minimum and maximum zoom values. 
    """

    input_filepaths = [Path(filepath) for filepath in input_filepaths]
    base_output_dir = Path(base_output_dir)
    translate_output_dir = base_output_dir / "translated"
    tile_output_dir = base_output_dir / "tiles"
    validate_paths(tile_output_dir, translate_output_dir)

    translated_file_paths = [
        file for file in translate_output_dir.iterdir()
    ]
    
    for input_filepath in input_filepaths:
        logging.debug(f"Input filepath {input_filepath}")
        
        filename = input_filepath.name
        layer_name = input_filepath.stem
        translated_file_path = translate_output_dir / filename
        layer_output_dir = tile_output_dir / layer_name

        logging.debug(f"input_filepath, filename, layer_name, translated_file_path, layer_output_dir: {input_filepath, filename, layer_name, translated_file_path, layer_output_dir}")
        # only try to translate a file if the 
        # translated file doesn't already exist
        if translated_file_path not in translated_file_paths:
            # Try to translate, and log errors without exiting.
            # Some layers won't translate due to problems with the file.
            try:
                logging.debug(f"translated file path, input file path: {translated_file_path, input_filepath}")
                Translate(translated_file_path, input_filepath, outputType=GDT_Byte)
            except: 
                error = traceback.format_exc()
                logging.debug(error)
                # If an error occurs in translation 
                # stop trying to process this input file
                # and move on to the next
                break
        
        # only try to render layer if it doesn't already exist
        if not layer_output_dir.is_dir():  
            os.makedirs(layer_output_dir)   
            
        try:
            logging.info(f"Making tile layer for {layer_name}")
            makeTileLayer(
                translated_file_path, layer_output_dir, min_zoom,
                max_zoom
            )
        except KeyboardInterrupt:
            rmtree(layer_output_dir)
            raise KeyboardInterrupt
        except:
            error = traceback.format_exc()
            logging.debug(error)
            rmtree(layer_output_dir)
