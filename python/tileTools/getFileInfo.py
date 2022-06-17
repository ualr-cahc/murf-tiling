#! python3.10
#  getFileInfo.py returns dictionary of raster file info

import os
import string
from numpy import iterable
import rasterio

"""class getFileInfo:
    Input a directory of raster files and get an object with 
    methods for creating information about the files.
    infoPaths: file_info = {filepath: {"size": size, "height": height, "width": width, "bounds": bounds}, ...}
    infoLists: file_info = {"size": (filepath, size), "height": (filepath, height), "width": (filepath, width), "bounds": (filepath, bounds)} """
    
"""        def __init__(self, parentDir, keys):
        default_keys = set(["paths", "lists", "height", "width", "bounds", "filesize", "pxsize", "coordsize", "pxpercoord"])
        key_error_message = f"keys must be a list, tuple, or set containing any of the following: {self.default_keys}"
        if not isinstance(keys, list) and not isinstance(keys, tuple) and not isinstance(keys, set):
            raise ValueError(key_error_message)
        for key in keys:
            if not isinstance(key, str):
                raise ValueError(key_error_message)
        if len(keys) == 0:
            self.function_keys = ["lists", "paths"]
            self.info_keys = self.default_keys.difference(set(["lists", "paths"]))
        else:
            self.keys = set(keys)
            for key in self.keys:
                key = key.lower()
                if key in self.default_keys:
                    self.keys.add(key)
                else:
                    raise KeyError(f"{key} is not a valid key")
                keys = set(self.keys)
                self.function_keys = keys.intersection(["lists", "paths"])
            if "lists" in self.function_keys and not (True in (v in self.info_keys for v in default_keys.difference(set(["paths", "lists"])))):
                for key in self.default_keys[2:]:
                    self.keys.append(key)
        self.parentDir = parentDir
        if "paths" in self.keys:
            self.infoPaths = self._make_infoPaths(parentDir)
        if "lists" in self.keys:
            self.infoLists = self._make_infoLists(parentDir)"""
        
        
    
def make_infoPaths(parentDir):
    infoPaths = {}
    parentDir = os.path.normpath(parentDir)
    for filename in os.listdir(parentDir):
        filepath = os.path.join(parentDir, filename)
        infoPaths[filepath] = {}
        current = infoPaths[filepath]
        current["size"] = os.path.getsize(filepath)
        with rasterio.open(filepath) as raster:
            current["height"] = raster.height
            current["width"] = raster.width
            current["bounds"] = raster.bounds
            current["lnglat"] = raster.lnglat
    return infoPaths

def make_infoLists(parentDir):
    parentDir = os.path.normpath(parentDir)
    infoLists = {
        "filesize": [],
        "height": [],
        "width": [],
        "bounds": [],
        "pxsize": [],
        "coordsize": [],
        "resolution": [],
        "lnglat": []
    }
    for filename in os.listdir(parentDir):
        filepath = os.path.join(parentDir, filename)
        infoLists["filesize"].append((filepath, os.path.getsize(filepath)))
        with rasterio.open(filepath) as raster:
            infoLists["height"].append((filepath, raster.height))
            infoLists["width"].append((filepath, raster.width))
            infoLists["bounds"].append((filepath, raster.bounds))
            try:
                infoLists["lnglat"].append((filepath, raster.lnglat()))
            except Exception as err:
                infoLists["lnglat"].append((filepath, err))
            pxsize = (raster.height*raster.width)
            infoLists["pxsize"].append((filepath, pxsize))
            coordsize = (raster.bounds.right-raster.bounds.left)*(raster.bounds.top-raster.bounds.bottom)
            infoLists["coordsize"].append((filepath, coordsize))
            resolution = pxsize/coordsize
            infoLists["resolution"].append((filepath, resolution))
            
    for key in infoLists:
        try:
            infoLists[key].sort(key=lambda x: x[1])
        except Exception as err:
            print(f"infoLists sorting error for {key}:", err)
    return infoLists