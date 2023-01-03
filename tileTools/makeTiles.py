# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false,
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Create XYZ tile layers for a list of GeoTIFFs.
"""

import logging
import os
import traceback
from math import ceil, cos, log2, radians
from pathlib import Path
from shutil import rmtree
from time import perf_counter_ns
from typing import Optional

import rasterio
from osgeo.gdal import GDT_Byte, Translate
from osgeo_utils import gdal2tiles

from tileTools.database import Database, NewColumn

logger = logging.getLogger(__name__)


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

            original_pixel_width = abs(raster.transform[0])
            earth_diameter = 40075016.686
            latitude = raster.lnglat()[1]
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
            logger.error(f"Non-Affine transform type used: "
                         f"{type(raster.transform)}. ")
            raise ValueError("Non-Affine transform type used. A value for "
                             "max_zoom must be supplied.")
    return max_zoom


def _make_tile_layer(translated_file_path: str,
                     layer_output_dir: str,
                     min_zoom: int = 8,
                     max_zoom: int | None = None,
                     processes: int | None = None,
                     xyz: bool = True,
                     database: Optional[Database] = None):
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

    if processes is None:
        processes = os.cpu_count()

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

    logger.debug(f"Begin tiling. Args: {gdal2tile_args}")

    begin = perf_counter_ns()
    gdal2tiles.main(gdal2tile_args)
    # if it takes longer than one minute to render a set,
    # don't move on to the next zoom level for this layer
    end = perf_counter_ns()
    duration = end-begin

    if database is not None:
        database.insert(
            table_name='make_tile_layer',
            items_to_insert={
                'layer_name': Path(translated_file_path).stem,
                'min_zoom': min_zoom,
                'max_zoom': max_zoom,
                'tile_time_ns': duration,
                'processes': processes,
                'xyz_tiles': 1 if xyz is True else 0,
                'translated_file_size': os.stat(translated_file_path).st_size
            }
        )

    logger.info(f"Zoom {min_zoom}-{max_zoom} tile time: "
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
            raise ValueError("Trying to write output to directory "
                             f"that is actually a file {path}")


def _is_color_mapped(raster_location: str) -> bool:  # type: ignore
    """Determine if the raster is color mapped"""

    raster = rasterio.open(raster_location)
    for band in range(raster.count):  # type: ignore
        try:
            band += 1
            if isinstance(raster.colormap(band), dict):  # type: ignore
                return True

        except ValueError as err:
            if str(err) == "NULL color table":
                return False
            else:
                raise err


def make_tiles(input_filepaths: list[str],
               output_dir: str,
               min_zoom: int = 8,
               max_zoom: int | None = None,
               xyz: bool = True,
               processes: int | None = None,
               database_logging: bool = False
               ):
    """Make raster tiles for all GeoTIFFs in a directory.

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

    if database_logging is True:
        logger.debug("Initializing database 'tiling.db'")
        database = Database("tiling.db")

        make_tile_layer_columns = [
            NewColumn('layer_name', 'text', 'NOT NULL'),
            NewColumn('min_zoom', 'integer', 'NOT NULL'),
            NewColumn('max_zoom', 'integer', 'NOT NULL'),
            NewColumn('tile_time_ns', 'integer', 'NOT NULL'),
            NewColumn('processes', 'integer', 'NOT NULL'),
            NewColumn('xyz_tiles', 'integer', 'DEFAULT 0'),
            NewColumn('translated_file_size', 'integer', 'NOT NULL')
        ]

        database.add_table('make_tile_layer',
                           make_tile_layer_columns)
    else:
        database = None

    logger.debug("Beginning make_tiles. "
                 f"args: {locals()}")

    # Convert the output directory to a Path object
    output_dir_path = Path(output_dir)
    # Create output directory for translated files
    # and for tile layers.
    translate_output_dir = output_dir_path / "translated"
    tile_output_dir = output_dir_path / "tiles"
    # Make sure the folders exist.
    _validate_paths(tile_output_dir, translate_output_dir)

    logger.debug("Looping through input_filepaths.")
    for input_filepath in map(Path, input_filepaths):
        logger.debug(f"Processing input filepath {input_filepath}")

        filename = input_filepath.name
        layer_name = input_filepath.stem
        translated_file_path = translate_output_dir / filename
        layer_output_dir = tile_output_dir / layer_name

        logger.debug(f"input_filepath: {input_filepath}, "
                     f"filename: {filename}, "
                     f"layer_name: {layer_name}, "
                     f"translated_file_path: {translated_file_path}, "
                     f"layer_output_dir: {layer_output_dir}")
        # only try to translate a file if the
        # translated file doesn't already exist
        if translated_file_path not in translate_output_dir.iterdir():
            # Try to translate, and log errors without exiting.
            # Some layers won't translate due to problems with the file.
            if _is_color_mapped(str(input_filepath)):
                rgbExpand = "rgb"
            else:
                rgbExpand = None

            try:
                logger.debug(f"Translating {translated_file_path} to bytes.")

                Translate(str(translated_file_path),
                          str(input_filepath),
                          outputType=GDT_Byte,
                          rgbExpand=rgbExpand)

            except Exception:
                # If an error occurs in translation, log it,
                # stop trying to process this input file,
                # and move on to the next
                error = traceback.format_exc()
                logger.debug(error)

                break

        # ensure layer output directory exists
        if not layer_output_dir.is_dir():
            os.makedirs(layer_output_dir)

        # Try to make the current tile layer,
        # but remove it if an error is raised before it completes.
        try:
            logger.info(f"Making tile layer for {layer_name}")
            _make_tile_layer(
                str(translated_file_path),
                str(layer_output_dir),
                min_zoom,
                max_zoom,
                xyz=xyz,
                processes=processes,
                database=database
            )

        # If the user raises a KeyboardInterrupt log it,
        # remove the incomplete layer, and exit.
        except KeyboardInterrupt:
            rmtree(layer_output_dir)
            raise KeyboardInterrupt
        # If an unexpected error occurs, log it, remove the incomplete layer,
        # and exit.
        except Exception as err:
            error = traceback.format_exc().replace("\n", ";")
            logger.error(error)
            rmtree(layer_output_dir)
            raise err
