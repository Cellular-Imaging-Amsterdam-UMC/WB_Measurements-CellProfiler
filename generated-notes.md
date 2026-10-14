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

### Still to verify

The image build and a run of the container test (`pytest`, needs Docker running), covering:

- the Python 3.12 environment inside the CellProfiler image;
- CellProfiler reading the OME-TIFF converted from RGB OME-Zarr as a color image;
- the masks pairing correctly with their images after conversion;
- the expected CSVs (with type-hint rows) and `ro-crate-metadata.json` in the output.
