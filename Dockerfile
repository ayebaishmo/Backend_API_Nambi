FROM python:3.10-slim

# System dependencies — ffmpeg for Whisper, gcc for building packages,
# chromium for Playwright scraping, postgresql client for psycopg2
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    make \
    libpq-dev \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install build tools first
RUN pip install --upgrade pip setuptools wheel pkgutil-resolve-name

# Install PyTorch CPU (required by Whisper — install before requirements.txt)
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install Whisper — use --no-build-isolation so it sees our setuptools
RUN pip install --no-build-isolation openai-whisper==20231117

# Copy requirements and install everything else
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Expose port
EXPOSE 9300

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:9300", "--workers", "2", "--timeout", "300", "--preload", "wsgi:app"]
