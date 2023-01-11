# GeoTIFF to XYZ raster tiles

python >= 3.10.5

## setup
```
git clone https://github.com/ualr-cahc/murf-tiling
cd murf-tiling
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
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
