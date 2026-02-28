FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

# Install libmagic for python-magic file type detection
RUN apt-get update && apt-get install -y libmagic1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure playwright browsers are installed
RUN playwright install chromium

COPY . .

CMD ["python", "-u", "index.py"]
