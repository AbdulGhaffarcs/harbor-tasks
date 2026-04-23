FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpng-dev libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        Pillow==10.3.0 \
        numpy==1.26.4

WORKDIR /task

# Pre-generated puzzle PNG, meta JSON, and agent helper tools.
# The golden state.json, solution.txt, and the level generator itself
# are NEVER placed in the runtime image — they live only in the archive
# at /tests/solution/ (mounted by Harbor) and environment/generate_level.py
# (outside the Docker COPY path).
COPY data/puzzle.png    /task/puzzle.png
COPY data/meta.json     /task/meta.json
COPY data/tools/       /task/tools/

RUN mkdir -p /output /logs/verifier

CMD ["bash"]
