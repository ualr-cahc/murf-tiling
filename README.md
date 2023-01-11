# GeoTIFF to XYZ raster tiles

python 3.10

## setup
```
git clone https://github.com/ualr-cahc/murf-tiling
cd murf-tiling
python -m venv env
env\Scripts\activate
pip install .\required_wheels\GDAL-3.4.3-cp310-cp310-win_amd64.whl
pip install .\required_wheels\rasterio-1.2.10-cp310-cp310-win_amd64.whl
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
