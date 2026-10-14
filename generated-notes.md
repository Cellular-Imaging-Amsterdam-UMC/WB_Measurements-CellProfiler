# Notes

## Conversion to a bilayers / BIOMERO container

This repository was converted in place from a BIAFLOWS workflow (`descriptor.json` +
`BiaflowsJob` wrapper) to a [bilayers](https://github.com/bilayer-containers/bilayers) container
for BIOMERO, following the `create-biomero-container` procedure of
[biomero-template-container](https://github.com/NL-BioImaging/biomero-template-container).

### Tasks performed

| Change | What it does |
|---|---|
| `wrapper.py` → `cellprofiler_run.py` (`git mv`) | Ported off BIAFLOWS: plain arguments instead of `BiaflowsJob`/`prepare_data`. The pipeline editing, CellProfiler run and CSV type-hint step are unchanged. Still runs with CellProfiler's own Python. |
| `descriptor.json` (`git rm`) | Removed: BIOMERO looks for `descriptor.json` before `config.yaml`, so it would keep the old BIAFLOWS mode. Regenerate with `biomero-template to-biaflows config.yaml` if a BIAFLOWS-only deployment needs one. |
| `config.yaml` (new) | The bilayers spec, drafted from the old descriptor (`biomero-template from-biaflows`) and completed: image+masks input as TIFF (OME-Zarr gets converted to OME-TIFF), CSV measurement output, the 4 parameters, citations for this workflow and CellProfiler 4, image tag `v1.0.0`. Valid for both the bilayers schema and BIOMERO's parser. |
| `wrapper.py` (new) | The image entrypoint: `run(spec=CONFIG)` from `biomero_template`, which calls `cellprofiler_run.py` through `config.yaml`'s `cli_command`, converts input formats and writes the Workflow RO-Crate into the output folder. |
| `Dockerfile` | Still `FROM cellprofiler/cellprofiler:4.2.6` (now fully qualified); Cytomine client and biaflows-utilities removed. `biomero_template` is installed from GitHub into a separate Python 3.12 environment (`/opt/biomero`), which is the new entrypoint. |
| `tests/`, `pytest.ini`, `requirements-dev.txt` | Config and BIOMERO checks, Dockerfile checks, a check that no descriptor shadows `config.yaml`, synthetic sample data (an RGB image plus three label masks, as OME-Zarr), and a Docker test running the image like BIOMERO on that sample. |
| `.github/workflows` | New `ci.yml` (validate + tests). `docker-image.yml` replaced by the template's version, which takes the image tag from `config.yaml` instead of the old semver tags. |
| `README.md`, `.gitignore`, `.dockerignore` | README covers bilayers/BIOMERO use, the RO-Crate output, registration, local Docker runs and development. |

### Follow-up fixes found by running the container

| Where | Fix |
|---|---|
| `Dockerfile` | The base image is Ubuntu 18.04 (glibc 2.27, gcc 7): the BIOMERO layer installs wheels only (uv picks versions with wheels for this glibc), except the pure-Python source-only packages, and leaves out `openslide-bin` (only needed for MIRAX slides). |
| `.github/workflows/ci.yml` | pip cache keyed on `requirements-dev.txt`. |
| `tests/test_workflow.py` | Container test builds with the repository root as context. |
| biomero-converter 0.2.1 | 3/4-channel OME-Zarr to OME-TIFF, RGB only for 8-bit, small multi-channel images, names ending in e/m/o, OME-Zarr without omero metadata. |
| fair-metadata-integration 0.2.1, 0.2.2 | File outputs (the CSV tables) were added to the RO-Crate as empty folders; CSV (and other common formats) now get an EDAM format. |
| biomero-template-container | Non-hidden staging folder (CellProfiler skips hidden folders); `container-test` for workflow repositories; requires the two releases above. |

### Verified

CI (`pytest`, including the container test) builds the image and runs it like BIOMERO on a synthetic
OME-Zarr job (an RGB image with nuclei, cell and aggregate label masks), covering:

- the Python 3.12 environment inside the CellProfiler image;
- the OME-Zarr input converted to OME-TIFF and read by CellProfiler (RGB image as color image);
- the masks paired with their image;
- the CSV tables (Nuclei with one row per nucleus, after the type-hint row and header) and
  `ro-crate-metadata.json` + `config.yaml` in the output.

### Still to verify

- A run on real images and masks (only synthetic data so far).
- A run through BIOMERO on Slurm (Singularity) after release `v1.0.0` and registration.
