import os
from osgeo.gdal import GDT_Byte, Translate

def translate2bytes(filepaths: list[str], output_dir: str):
	"""Input a list of .tif filepaths and an output directory, returns list of errors.
	Checks for files in output directory and translates those not yet present."""
	errors = []
	output_dir = os.path.abspath(output_dir)
	translated_files = [os.path.join(output_dir, file) for file in os.listdir(output_dir)]
	if not isinstance(filepaths, list):
		raise ValueError("filepaths variable must be a list of filepaths")
	for filepath in filepaths:
		filename = os.path.split(filepath)[-1]
		translated_filepath = os.path.join(output_dir, filename)
		if translated_filepath not in translated_files:
			try:
				Translate(translated_filepath, filepath, outputType=GDT_Byte)
			except Exception as err:
				errors.append((filepath, err))
				print(err)
	return errors