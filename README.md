# W_Measurements-CellProfiler

Batch feature extraction for 2D fluorescence images using **CellProfiler 4.2.6**, designed for datasets that already have three pre-segmented object masks — nuclei, cells, and sub-cellular aggregates or foci.

The workflow runs a headless CellProfiler pipeline (`FullMeasurementsNucleiCellAggregates.cppipe`) and writes per-object CSV tables containing morphology features (area, perimeter, shape descriptors, texture) and per-channel intensity statistics for every detected nucleus, cell, and aggregate. This makes it suitable for studies where you need to relate aggregate or foci counts and intensities back to their parent cells and nuclei.

## What you need

Before running this workflow you must have:

- **Input images** — 2D fluorescence images (TIFF or compatible) placed in the input folder.
- **A Nuclei mask per image** — a greyscale label image where each nucleus is a distinct integer value (e.g. produced by a prior segmentation workflow). The filename must share the same base name as the input image and end with the configured nuclei suffix (default: `_Nuclei_Mask`).
- **A Cell mask per image** — same convention, ending with the configured cells suffix (default: `_Cells_Mask`).
- **An Aggregates/Foci mask per image** — same convention, ending with the configured aggregates suffix (default: `_Aggregates_Mask`).

All four files (original image + three masks) must live in the same input folder. Images may be
TIFF or OME-Zarr (as BIOMERO exports them); OME-Zarr is converted to OME-TIFF for CellProfiler, keeping
the file names, so the suffixes still match.

## Outputs

Per-object CSV files are written to the output folder:

| CSV file | Contents |
|----------|----------|
| `Nuclei.csv` | One row per nucleus — shape, size, texture, intensity per channel |
| `Cells.csv` | One row per cell — shape, size, texture, intensity per channel |
| `Aggregates.csv` | One row per aggregate/focus — shape, size, texture, intensity per channel |
| `Image.csv` | Per-image aggregate statistics |
| `Experiment.csv` | Run-level metadata |
| `*.cppipe` | Copy of the modified pipeline used (for reproducibility) |
| `ro-crate-metadata.json`, `config.yaml` | [Workflow RO-Crate](https://w3id.org/workflowhub/workflow-ro-crate/1.1) describing the run: the workflow spec, the input and every output |

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `nuclei_mask_suffix` | `_Nuclei_Mask` | Filename suffix that identifies nuclei mask images |
| `cells_mask_suffix` | `_Cells_Mask` | Filename suffix that identifies cell mask images |
| `aggregates_mask_suffix` | `_Aggregates_Mask` | Filename suffix that identifies aggregates/foci mask images |
| `metric_channels` | `1,2,3` | Comma-separated list of channel indices (1-based) to include in intensity measurements |

> **`metric_channels` note:** The default assumes a 3-channel RGB image. For a single-channel image use `1`; for a 4-channel image use `1,2,3,4`. Channel indices map directly to the channel order in your source image.

## BIOMERO compatibility

This workflow is a [bilayers](https://github.com/bilayer-containers/bilayers) container for
[BIOMERO](https://github.com/NL-BioImaging/biomero): BIOMERO reads `config.yaml` from this repository
(at a release tag), shows the parameters in OMERO, runs the image on a Slurm cluster and imports the
CSV tables back. Register it in BIOMERO's `slurm-config.ini`:

```ini
[WORKFLOWS]
measurements=measurements
measurements_repo=https://github.com/Cellular-Imaging-Amsterdam-UMC/WB_Measurements-CellProfiler/tree/vX.Y.Z
measurements_image=cellularimagingcf/w_measurements-cellprofiler
```

The release tag must equal `docker_image.tag` in `config.yaml`; publishing the release builds and pushes
the image (`.github/workflows/docker-image.yml`).

Run it locally with Docker, laid out like a BIOMERO job:

```
docker build -t cellularimagingcf/w_measurements-cellprofiler .
docker run --rm -v ./job/data:/data cellularimagingcf/w_measurements-cellprofiler     --infolder=/data/in --outfolder=/data/out --metric_channels=1,2,3
```

## Technical notes (for developers)

Built with [biomero-template-container](https://github.com/NL-BioImaging/biomero-template-container):

- **`config.yaml`** — the bilayers spec: input folder, output folder, parameters, citations, image.
- **`wrapper.py`** — image entrypoint (Python 3.12 environment `/opt/biomero`): resolves the values
  BIOMERO passes, converts OME-Zarr input to OME-TIFF, runs `exec_function.cli_command` and makes the
  output folder a Workflow RO-Crate (fair-metadata-integration).
- **`cellprofiler_run.py`** — the tool, run with CellProfiler's own Python: loads the `.cppipe` via
  `cellprofiler_core`, updates the `NamesAndTypes` mask suffixes and the channel modules to match
  `metric_channels`, runs CellProfiler headless, and prepends a type-hint row to each CSV so OMERO
  tables can infer column types.
- **Container base:** `cellprofiler/cellprofiler:4.2.6`

Development:

```
pip install -r requirements-dev.txt
biomero-template validate config.yaml --biomero
pytest                                   # the container test needs Docker running
python tests/sample_data.py <folder>     # synthetic image + masks (OME-Zarr; --tiff for TIFF)
```
