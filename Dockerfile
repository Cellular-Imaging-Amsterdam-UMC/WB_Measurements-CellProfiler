# Fully qualified, so engines without short-name resolution (Podman) build it as Docker does
FROM docker.io/cellprofiler/cellprofiler:4.2.6

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# >>> tool layer: CellProfiler 4.2.6 (base image) runs the pipeline with its own Python
RUN mkdir -p /app
COPY cellprofiler_run.py FullMeasurementsNucleiCellAggregates.cppipe /app/
# <<< tool layer

# --- BIOMERO layer: spec parsing, OME-Zarr conversion, RO-Crate ---
# biomero_template needs Python >= 3.12, so it gets its own environment next to CellProfiler's;
# the interpreter lives under /opt so it is readable when Singularity runs as another user.
# The base image is Ubuntu 18.04 (glibc 2.27, gcc 7): newer compiled packages only ship wheels
# for glibc >= 2.28 and cannot be built here, so only wheels are used (uv picks the newest versions
# with wheels for this glibc), except for the pure-Python packages that only ship as source.
# openslide-bin has no such wheel at all; biomero-converter only needs OpenSlide for MIRAX slides,
# so it is left out (a uv override that never matches).
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN python -m pip install uv \
    && echo "openslide-bin; sys_platform == 'never'" > /tmp/uv-overrides.txt \
    && uv venv /opt/biomero --python 3.12 \
    && uv pip install --no-cache --python /opt/biomero/bin/python --override /tmp/uv-overrides.txt \
       --only-binary :all: --no-binary biomero-template-container --no-binary bilayers-schema \
       --no-binary pytest-logging \
       "biomero-template-container @ git+https://github.com/NL-BioImaging/biomero-template-container.git" \
    && chmod -R a+rX /opt/biomero /opt/uv-python

COPY config.yaml wrapper.py /app/
RUN mkdir -p /data/in /data/out
WORKDIR /app
ENTRYPOINT ["/opt/biomero/bin/python", "/app/wrapper.py"]

# Example build:
# docker build -t measurements-cellprofiler .

# Example run:
# docker run -v C:/Project/slides:/data -t measurements-cellprofiler --infolder=/data/cells
