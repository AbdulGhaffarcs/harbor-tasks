FROM ubuntu:22.04

# Add your other instructions here
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip

WORKDIR /app
COPY . .

CMD ["python3", "app.py"]
