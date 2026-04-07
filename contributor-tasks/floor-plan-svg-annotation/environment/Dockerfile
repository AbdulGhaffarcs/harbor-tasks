FROM python:3.11-slim
WORKDIR /task
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg-dev libpng-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir Pillow==10.3.0 numpy==1.26.4
COPY data/floorplan.png /task/floorplan.png
CMD ["bash"]
