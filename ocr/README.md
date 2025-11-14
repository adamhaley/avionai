# PaddleOCR Microservice

A simple OCR microservice built with PaddleOCR and FastAPI.

## Overview

This project provides two server implementations:
- **server.py**: Lightweight version for basic OCR tasks
- **server-prod.py**: Production version with PDF support, CORS, and environment configuration

## Setup

### Prerequisites
- Python 3.12
- poppler-utils (for PDF processing)

### Installation

1. Create virtual environment:
```bash
python3 -m venv venv
```

2. Install dependencies:
```bash
./venv/bin/pip install -r requirements.txt
```

Note: First run will download OCR models (~16MB) to `~/.paddleocr/`

## Running Locally

### Lightweight Server (server.py)

Start the server:
```bash
./venv/bin/uvicorn server:app --host 0.0.0.0 --port 8080
```

Or use the helper script:
```bash
./start-server.sh
```

### Production Server (server-prod.py)

The production server supports environment variables:
- `PADDLE_LANG`: Language (default: "en")
- `PADDLE_PORT`: Port (default: 6000)
- `PADDLE_HOST`: Host (default: "0.0.0.0")
- `PADDLE_ALLOWED_ORIGINS`: CORS origins (default: "*")

Start with:
```bash
./venv/bin/python server-prod.py
```

Or with custom settings:
```bash
PADDLE_PORT=8080 ./venv/bin/python server-prod.py
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8080/health
```

Response:
```json
{"status": "ok"}
```

### OCR Endpoint (server.py)
```bash
curl -X POST http://localhost:8080/ocr \
  -F "file=@image.jpg"
```

Response:
```json
{
  "file_name": "image.jpg",
  "results": [
    {
      "text": "Hello World",
      "confidence": 0.99
    }
  ]
}
```

### OCR Endpoint (server-prod.py)
Supports both images and PDFs with multi-page processing.

```bash
curl -X POST http://localhost:6000/ocr \
  -F "file=@document.pdf"
```

Response includes bounding boxes and page numbers:
```json
{
  "filename": "document.pdf",
  "pages": [
    {
      "page": 1,
      "results": [
        {
          "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
          "text": "Sample text",
          "confidence": 0.98
        }
      ]
    }
  ]
}
```

## Testing

Test with a simple text file:
```bash
echo "Hello World" | convert label:@- test.png
curl -X POST http://localhost:8080/ocr -F "file=@test.png"
```

## Deployment to Amazon Lightsail

### 1. Prepare Server
```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3 python3-venv python3-pip poppler-utils

# Copy files to server
scp -r . user@your-server:/var/www/html/avionai/ocr/
```

### 2. Install Dependencies
```bash
cd /var/www/html/avionai/ocr
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 3. Create Systemd Service

Create `/etc/systemd/system/paddleocr.service`:
```ini
[Unit]
Description=OCR Microservice
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/html/avionai/ocr
Environment="PATH=/var/www/html/avionai/ocr/venv/bin"
ExecStart=/var/www/html/avionai/ocr/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

Setup on PROD:

```
[Unit]
Description=PaddleOCR Microservice
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/paddleocr
Environment="PATH=/opt/paddleocr/venv/bin"
ExecStart=/opt/paddleocr/venv/bin/uvicorn server:app --host 0.0.0.0 --port 6000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 4. Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable ocr-service
sudo systemctl start ocr-service
sudo systemctl status ocr-service
```

### 5. Configure Firewall
```bash
# Allow port 8080
sudo ufw allow 8080/tcp
```

### 6. Optional: Setup Nginx Reverse Proxy

Create `/etc/nginx/sites-available/ocr`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Increase timeout for OCR processing
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/ocr /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Version Compatibility

This setup uses:
- paddlepaddle==2.6.1
- paddleocr==2.8.1

These versions are compatible with Python 3.12 and avoid known compatibility issues with newer versions.

## Troubleshooting

### Model Download Issues
Models are automatically downloaded on first run to `~/.paddleocr/`. If download fails, check internet connectivity.

### Port Already in Use
Change the port in the uvicorn command:
```bash
./venv/bin/uvicorn server:app --host 0.0.0.0 --port 8081
```

### Memory Issues
OCR processing can be memory-intensive. For large PDFs, consider:
- Using the lightweight server for single images
- Increasing server memory
- Processing PDFs page-by-page

## Documentation

- FastAPI docs: http://localhost:8080/docs
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
