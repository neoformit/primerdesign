"""Set and assert required app directories."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PRIMER3_PATH = os.path.join(
    BASE_DIR,
    'design',
    'primer3',
    'src',
    'primer3_core'
)
PRIMER3_CONFIG_PATH = os.path.join(
    BASE_DIR,
    'design',
    'primer3',
    'src',
    'primer3_config'
)
PRIMER3_INPUT_DIR = os.path.join(
    BASE_DIR,
    'design',
    'primer3',
    'input_files'
)
PRIMER3_OUTPUT_DIR = os.path.join(
    BASE_DIR,
    'design',
    'primer3',
    'output_files'
)
PROBE_SEQUENCE_PATH = os.path.join(
    BASE_DIR,
    'design',
    'probes',
    'roche_upl_sequences.json'
)
PATHS = [
    ('PRIMER3_PATH', PRIMER3_PATH),
    ('PRIMER3_INPUT_DIR', PRIMER3_INPUT_DIR),
    ('PRIMER3_OUTPUT_DIR', PRIMER3_OUTPUT_DIR),
    ('PROBE_SEQUENCE_PATH', PROBE_SEQUENCE_PATH),
]

for DIR in (PRIMER3_INPUT_DIR, PRIMER3_OUTPUT_DIR):
    if not os.path.exists(DIR):
        try:
            os.mkdir(DIR)
        except Exception:
            raise FileNotFoundError(
                'Failed to create primer3 directory at '
                + DIR
            )

for name, path in PATHS:
    assert os.path.exists(path), (
        f"Path not found at settings.{name}:"
        + f" { path }"
    )
