# hal_agent runtime image.
#
# The image provides only the Python environment (pinned deps). At run time the
# whole repo is bind-mounted at /app (see scripts/docker_run.sh), so code edits
# on the host take effect without a rebuild and all outputs land on the host.
# The COPY below is a fallback so the image also works standalone (no mount).
FROM python:3.13-slim

# libgomp1: required by onnxruntime (pulled in by fastembed / flashrank).
# git: some tooling shells out to it. No build-essential — every pinned dep
# ships a manylinux wheel for 3.13.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first so the layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Fallback copy of the source (overlaid by the bind mount during normal runs).
COPY . .

# Persist downloaded embedding / reranker models on a mounted cache volume
# instead of re-downloading every container start.
ENV HF_HOME=/cache/hf \
    FASTEMBED_CACHE_PATH=/cache/fastembed \
    PYTHONUNBUFFERED=1

CMD ["python", "core/s0_run_full_analysis.py", "--help"]
