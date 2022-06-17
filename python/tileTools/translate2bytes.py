import os
from osgeo.gdal import GDT_Byte, Translate
from tileTools.calcTime import calcTime

@calcTime
def translate2bytes(input_filepaths: list[str], output_dir: str):
	"""Input a list of .tif filepaths and an output directory, returns list of errors.
	Checks for files in output directory and translates those not yet present."""
	errors = []
	output_dir = os.path.abspath(output_dir)
	if not os.path.isdir(output_dir):
		os.mkdir(output_dir)
	translated_files = [os.path.join(output_dir, file) for file in os.listdir(output_dir)]
	if not isinstance(input_filepaths, list):
		print(input_filepaths)
		raise ValueError("input_filepaths variable must be a list of filepaths")
	for filepath in input_filepaths:
		filename = os.path.split(filepath)[-1]
		translated_filepath = os.path.join(output_dir, filename)
		if translated_filepath not in translated_files:
			try:
				Translate(translated_filepath, filepath, outputType=GDT_Byte)
			except Exception as err:
				errors.append((filepath, err))
				print(err)
	return errors