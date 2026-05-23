FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY downloader.py .
COPY ../../src/config.py ./src/config.py

CMD ["python", "downloader.py"]
