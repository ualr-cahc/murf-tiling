#! python3.11

import logging
import unittest
from pathlib import Path
import shutil

from tests.setup_logging import root_logger
from tileTools import makeTiles

TESTS = Path("./tests").resolve()
OUTPUT = TESTS / "output"
# TIFFS = TESTS / "TIFFs"
TIFFS = Path("./logs/TIFFs")


root_logger = root_logger()
logger = logging.getLogger(__name__)


class test_makeTiles(unittest.TestCase):

    def setUp(self) -> None:

        if not OUTPUT.exists():
            OUTPUT.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(OUTPUT)

    def test_makeTiles(self):
        makeTiles.make_tiles(
            input_filepaths=list(map(str, TIFFS.iterdir())),
            output_dir=str(OUTPUT),
            database_logging=True
        )
