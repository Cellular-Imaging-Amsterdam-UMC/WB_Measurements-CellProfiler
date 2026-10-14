"""BIOMERO container entrypoint.

Resolves the values BIOMERO passes (see config.yaml), converts OME-Zarr input to TIFF for
CellProfiler, runs ``exec_function.cli_command`` (cellprofiler_run.py, with CellProfiler's own
Python) and makes the output folder a Workflow RO-Crate; see biomero_template.
"""
from pathlib import Path

from biomero_template import run

CONFIG = Path(__file__).with_name("config.yaml")

if __name__ == "__main__":
    raise SystemExit(run(spec=CONFIG))
