FROM python:3.12-slim

WORKDIR /root/Mikobot

COPY . .

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    git

# Upgrade pip and setuptools
RUN pip3 install --upgrade pip setuptools

# Install Python dependencies
RUN pip3 install -r requirements.txt

CMD ["python3", "-m", "Mikobot"]
