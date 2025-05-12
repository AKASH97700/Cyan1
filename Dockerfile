FROM python:3.12

WORKDIR /root/Mikobot

COPY . .

# Install system dependencies (added image libs for Pillow)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjpeg-dev \
    libtiff-dev \
    libwebp-dev \
    tk-dev \
    git \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools
RUN pip3 install --upgrade pip setuptools

# Install Python dependencies
RUN pip3 install -r requirements.txt

CMD ["python3", "-m", "Mikobot"]
