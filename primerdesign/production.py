"""Production settings for primerdesign project."""

import os
import json
from pathlib import Path
from .settings import *

DEBUG = False
PRIMER3_DEBUG = False   # Additional logging and file output

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'primers.neoformit.com',
]
