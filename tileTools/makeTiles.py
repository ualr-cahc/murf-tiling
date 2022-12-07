"""Create XYZ tile layers for a list of GeoTIFFs.
"""

import logging
import os
import traceback
from datetime import datetime
from math import ceil, cos, log2, radians
from pathlib import Path
from shutil import rmtree
from time import perf_counter_ns

import rasterio
from osgeo.gdal import GDT_Byte, Translate
from osgeo_utils import gdal2tiles

logger = logging.getLogger(__name__)
log_file_name = f"tiling_{datetime.now().strftime('%Y-%m-%d_%H_%M_%S')}.log"
log_file_handler = logging.FileHandler(log_file_name)
log_file_handler.setLevel(logging.INFO)
logger.addHandler(log_file_handler)


def _find_max_zoom(translated_file_path: str):
    """Determine the maximum tile zoom level for a single GeoTIFF.
    The result is calculated by finding the floating point 'zoom-level'
    of the original GeoTIFF and rounding up to the next integer zoom value.
    This function uses the equation for determining raster tile width given
    the zoom level, rearranged to input width and output 'zoom level'.

    Args:
        translated_file_path (str): Path to a GeoTIFF that has been converted
        to bytes using osgeo.gdal.Translate()

    Returns:
        int: Maximum zoom level.
    """

    with rasterio.open(translated_file_path) as raster:
        if isinstance(raster.transform, rasterio.Affine):

            original_pixel_width = (
                (raster.bounds.right + raster.bounds.left) / raster.width
            )
            earth_diameter = 40075016.686
            latitude = 34.74
            max_zoom = ceil(
                log2(earth_diameter
                     * cos(radians(latitude))
                     / original_pixel_width
                     )
                - 8
                )

            logger.info(f"original pixel width (m): {original_pixel_width}, "
                        f"earth diameter (m): {earth_diameter}, "
                        f"latitude: {latitude}"
                        f"max zoom: {max_zoom}")
        else:
            logger.info(f"Non-Affine transform type used: "
                        f"{type(raster.transform)}. "
                        f"Defaulting to supplied max_zoom: {max_zoom}.")

    return max_zoom


def _make_tile_layer(translated_file_path: str,
                     layer_output_dir: str,
                     min_zoom: int = 8,
                     max_zoom: int | None = None,
                     processes=os.cpu_count(),
                     xyz=True):
    """Create a raster tile layer from a single GeoTIFF file using
    gdal2tile.

    Args:
        translated_file_path (str): Path to a GeoTIFF that has been converted
        to bytes using osgeo.gdal.Translate
        layer_output_dir (str): location for gdal2tiles to drop files
        min_zoom (int): Minimum zoom level. Defaults to 8.
        max_zoom (int | None, optional): If not supplied, default zoom is
        determined by _find_max_zoom function. Defaults to None.
        processes (_type_, optional): The number of multithreading processes
        to use. Defaults to os.cpu_count() (aka max for machine).
        xyz (bool, optional): True for XYZ tiles, False for TMS.
        Defaults to True.
    """

    logger.debug("Beginning _make_tile_layer for "
                 f"{Path(translated_file_path).name}")
    # Determine optimum max zoom level if max_zoom is not provided
    if max_zoom is None:
        logger.debug("Determining max zoom via _find_max_zoom()")
        max_zoom = _find_max_zoom(translated_file_path)

    # These are the arguments to be used with osgeo_utils.gdal2tiles
    # The argument '-e' aka 'resume mode' picks up where it left off,
    # if tiling progress has already been made.
    gdal2tile_args = ['gdal2tiles.py',
                      '-z',
                      f"{min_zoom}-{max_zoom}",
                      '-e',
                      f'--processes={processes}']
    # add OSM slippy map standard ('--xyz')
    if xyz:
        gdal2tile_args.append("--xyz")
    # add input and output paths last
    gdal2tile_args += [str(translated_file_path), str(layer_output_dir)]

    logging.debug(f"Begin tiling. Args: {gdal2tile_args}")

    begin = perf_counter_ns()
    gdal2tiles.main(gdal2tile_args)
    # if it takes longer than one minute to render a set,
    # don't move on to the next zoom level for this layer
    end = perf_counter_ns()
    duration = end-begin

    logging.info(f"Zoom {min_zoom}-{max_zoom} tile time: "
                 f"{duration/1000000000} seconds")


def _validate_paths(*paths: Path):
    """For each path, create it if it doesn't already exist.

    Raises:
        ValueError: If the path already exists as a file, ValueError is raised.
    """

    for path in paths:
        if not path.exists():
            os.makedirs(path)
        elif path.is_file():
            raise ValueError("trying to write output to directory "
                             f"that is actually a file {path}")


def makeTiles(input_filepaths: list[str],
              output_dir: str,
              min_zoom: int = 8,
              max_zoom: int | None = None,
              xyz=True,
              processes=os.cpu_count()
              ):
    """Make raster tiles from

    Args:
        input_filepaths (list[str]): List of GeoTIFF filepaths.
        output_dir (str): location to drop subfolders "translated" and
        "tiles" containing byte translated versions of the GeoTIFFs and the
        resulting tile sets, respectively.
        min_zoom (int): Minimum zoom level for rendered tile set. Default is 8.
        max_zoom (int | None, optional): Maximum zoom level for rendered tile
        set. If not supplied, max_zoom is calculated via _find_max_zoom()
        xyz (bool, optional): True for XYZ tiles, False for TMS.
        Defaults to True.
        processes (_type_, optional): The number of multithreading processes
        to use. Defaults to os.cpu_count() (aka max for machine).

    Raises:
        KeyboardInterrupt: If KeyboardInterrupt is raised while tiling a layer,
        the incomplete layer is discarded before the program stops. Same goes
        for unexpected errors during tiling.
    """

    # Convert the list of input filepaths to a map of Path objects
    input_filepaths = map(Path, input_filepaths)
    # Convert the output directory to a Path object
    output_dir = Path(output_dir)
    # Create output directory for translated files
    # and for tile layers.
    translate_output_dir = output_dir / "translated"
    tile_output_dir = output_dir / "tiles"
    # Make sure the folders exist.
    _validate_paths(tile_output_dir, translate_output_dir)

    for input_filepath in input_filepaths:
        logging.debug(f"Input filepath {input_filepath}")

        filename = input_filepath.name
        layer_name = input_filepath.stem
        translated_file_path = translate_output_dir / filename
        layer_output_dir = tile_output_dir / layer_name

        logging.debug(f"input_filepath: {input_filepath}, "
                      f"filename: {filename}, "
                      f"layer_name: {layer_name}, "
                      f"translated_file_path: {translated_file_path}, "
                      f"layer_output_dir: {layer_output_dir}")
        # only try to translate a file if the
        # translated file doesn't already exist
        if translated_file_path not in translate_output_dir.iterdir():
            # Try to translate, and log errors without exiting.
            # Some layers won't translate due to problems with the file.
            try:
                logging.debug(f"Translated file path: {translated_file_path}")
                logging.debug(f"Input file path: {input_filepath}")
                Translate(translated_file_path,
                          input_filepath,
                          outputType=GDT_Byte)
            except Exception:
                # If an error occurs in translation, log it,
                # stop trying to process this input file,
                # and move on to the next
                error = traceback.format_exc()
                logging.debug(error)

                break

        # ensure layer output directory exists
        if not layer_output_dir.is_dir():
            os.makedirs(layer_output_dir)

        # Try to make the current tile layer,
        # but remove it if an error is raised before it completes.
        try:
            logging.info(f"Making tile layer for {layer_name}")
            _make_tile_layer(
                translated_file_path, layer_output_dir, min_zoom, max_zoom
            )
        # If the user raises a KeyboardInterrupt log it,
        # remove the incomplete layer, and exit.
        except KeyboardInterrupt:
            rmtree(layer_output_dir)
            raise KeyboardInterrupt
        # If an unexpected error occurrs, log it, remove the incomplete layer,
        # and exit.
        except Exception:
            error = traceback.format_exc()
            logging.debug(error)
            rmtree(layer_output_dir)
