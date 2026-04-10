FROM python:3.11-slim
WORKDIR /task
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpng-dev libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir Pillow==10.3.0 numpy==1.26.4
COPY data/sorting_network.png /task/sorting_network.png
CMD ["bash"]
