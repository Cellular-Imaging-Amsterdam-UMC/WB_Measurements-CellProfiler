"""Checks for this workflow, using biomero_template (pip install -r requirements-dev.txt)."""
import shlex
from pathlib import Path, PurePosixPath

import pytest

from biomero_template import BilayersSpec
from biomero_template.cli import main as biomero_template_cli
from biomero_template.container_test import container_test, detect_runtime
from biomero_template.contract import biomero_argv
from biomero_template.conversion import TIFF, ZARR, normalize_formats

from sample_data import NAME, SUFFIXES, write_sample

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.yaml"
CSV_TABLES = ("Nuclei.csv", "Cells.csv", "Aggregates.csv", "Image.csv", "Experiment.csv")


def test_config_is_valid_for_bilayers_and_biomero():
    assert biomero_template_cli(["validate", str(CONFIG), "--biomero"]) == 0


def test_biomero_arguments_build_the_cellprofiler_command():
    spec = BilayersSpec(CONFIG)
    argv = biomero_argv(CONFIG, PurePosixPath("/"), metric_channels="1,2")
    assert argv == ["--infolder=/data/in", "--outfolder=/data/out", "--metric_channels=1,2"]
    command = spec.command(spec.parse_args(argv))
    assert command[:2] == ["python", "/app/cellprofiler_run.py"]
    assert shlex.join(command[2:]).endswith(
        "--nuclei_mask_suffix _Nuclei_Mask --cells_mask_suffix _Cells_Mask "
        "--aggregates_mask_suffix _Aggregates_Mask --metric_channels 1,2")


def test_sample_data_names_match_the_mask_suffixes(tmp_path):
    names = sorted(path.name for path in write_sample(tmp_path, as_zarr=False))
    assert names == sorted(f"{NAME}{suffix}.ome.tif" for suffix in ("", *SUFFIXES))


def test_config_accepts_ome_tiff_and_ome_zarr():
    assert normalize_formats(BilayersSpec(CONFIG).inputs["infolder"]["format"]) == {TIFF, ZARR}


def _instructions(keyword):
    lines = (ROOT / "Dockerfile").read_text().splitlines()
    return [line.split(None, 1)[1] for line in lines if line.upper().startswith(keyword + " ")]


def test_dockerfile_runs_wrapper_with_biomero_environment():
    assert _instructions("ENTRYPOINT")[-1] == '["/opt/biomero/bin/python", "/app/wrapper.py"]'


def test_dockerfile_is_portable():
    """Fully qualified base image (Podman) and no USER (Singularity runs as the calling user)."""
    assert all("." in base.split()[0].split("/")[0] for base in _instructions("FROM"))
    assert _instructions("USER") == []


def _docker_running():
    try:
        return bool(detect_runtime())
    except RuntimeError:
        return False


@pytest.mark.container
@pytest.mark.skipif(not _docker_running(), reason="Docker is not running")
@pytest.mark.parametrize("as_zarr", [True, False], ids=["ome-zarr", "ome-tiff"])
def test_container_on_sample_job(tmp_path, as_zarr):
    """Build the image and run it like BIOMERO on synthetic images and masks, in each input format."""
    sample = tmp_path / "sample"
    write_sample(sample, as_zarr=as_zarr)
    # the first run builds the image
    outputs = container_test(CONFIG, context=ROOT, sample=sample, keep=tmp_path / "job", build=as_zarr)
    names = {path.name for path in outputs}
    assert set(CSV_TABLES) <= names
    assert "ro-crate-metadata.json" in names and "config.yaml" in names
    assert any(name.endswith(".cppipe") for name in names)
    nuclei_rows = (tmp_path / "job" / "data" / "out" / "Nuclei.csv").read_text().splitlines()
    assert nuclei_rows[0].startswith("# header")  # OMERO.tables type hints
    assert len(nuclei_rows) == 2 + 2  # type hints, header, two nuclei


def test_no_descriptor_shadows_config():
    """BIOMERO reads descriptor.json/descriptor.yaml before config.yaml."""
    assert not [name for name in ("descriptor.json", "descriptor.yaml") if (ROOT / name).exists()]
