#! filterTiffs takes a directory and returns a list of the filepaths
# of all .tif files in the directory. 

import os

def filterTiffs(input_filepaths):
    tiffs = [file for file in input_filepaths if os.path.splitext(file[-1] == '.tif')]
    #tiffs = [os.path.join(raw_inputs, file) for file in os.listdir(raw_inputs) if os.path.splitext(file)[-1] == '.tif']
    print("Number of tiffs:", len(tiffs), "\n")
    return tiffs