# GeoTIFF to XYZ raster tiles

python >= 3.10.5

## setup
1. clone repository
    ```
    git clone https://github.com/ualr-cahc/murf-tiling
    ```

1. navigate to repository root
    ```
    cd murf-tiling
    ```

1. create and activate a python virtual environment
    ```
    python -m venv env

    env\Scripts\activate
    ```

1. install gdal and rasterio [wheels](https://www.lfd.uci.edu/~gohlke/pythonlibs):
    * via requirements.txt
    ```
    pip install -r requirements.txt
    ```
    OR 
    * install the wheels directly (if there is an issue with requirements.txt)
    ```
    pip install ./wheels/GDAL-3.4.3-cp310-cp310-win_amd64.whl
    pip install ./wheels/rasterio-1.2.10-cp310-cp310-win_amd64.whl
    ```

## run the tool

* Basic implementation
```python
from tileTools.makeTiles import make_tiles

# input_dir is the directory containing the GeoTIFFs to be tiled
# output_dir is the directory where the tool will output folders and files
make_tiles(input_dir="tests/TIFFs",
           output_dir="tests/output")
```

* Output stats to sqlite3 database file (optional):
```python
make_tiles(input_dir="tests/TIFFs",
           output_dir="tests/output",
           database_name='test_tiling.db')
```
