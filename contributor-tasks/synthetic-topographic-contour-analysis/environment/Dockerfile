FROM python:3.11-slim

# Pin library versions for deterministic rendering
RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    scipy==1.13.1 \
    matplotlib==3.9.2 \
    Pillow==10.4.0 \
    pytest==8.3.3

# Install DejaVu fonts (deterministic text rendering)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /task

# Copy task files
COPY environment/data/ /task/
COPY instruction.md /task/instruction.md
COPY tests/ /task/tests/

# Create outputs directory
RUN mkdir -p /task/outputs

# Set font cache to avoid non-deterministic font discovery
ENV MPLCONFIGDIR=/tmp/matplotlib
RUN python3 -c "import matplotlib.pyplot as plt; plt.figure(); plt.close()"
