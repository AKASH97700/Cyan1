FROM python:3.12-slim

WORKDIR /root/Mikobot

COPY . .

RUN apt-get update && apt-get install -y --no-install-recommends \
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
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    git \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip setuptools

RUN pip3 install -r requirements.txt

CMD ["python3", "-m", "Mikobot"]
