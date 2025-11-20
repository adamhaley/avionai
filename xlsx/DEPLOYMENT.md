# Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Access to server/environment
- Excel template files (.xlsx)

## Quick Deployment

### 1. Clone/Copy Project

```bash
cd /var/www/html/avionai/
git clone <repository> xlsx
cd xlsx
```

### 2. Add Templates

```bash
# Copy your Excel templates to the templates directory
cp /path/to/your/templates/*.xlsx templates/
```

### 3. Configure Templates

Edit `app/main.py` and update `TEMPLATE_CONFIG`:

```python
TEMPLATE_CONFIG: Dict[str, Dict] = {
    "YourTemplate.xlsx": {
        "sheet_name": "Sheet1",  # The sheet to modify
        "fields": {
            "field1": "B3",  # Map field names to cell references
            "field2": "C5",
        },
    },
}
```

**Tip**: Use the template mapper to help identify cells:

```bash
python template_mapper.py templates/YourTemplate.xlsx
```

### 4. Build and Start

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or using Makefile
make build
make run
```

### 5. Verify Deployment

```bash
# Check health
curl http://localhost:8000/health

# List templates
curl http://localhost:8000/templates

# Or use Makefile
make health
make templates
```

## Integration with Existing Docker Setup

If you have an existing Docker network (e.g., for n8n):

### 1. Update docker-compose.yml

```yaml
networks:
  avionai-network:
    external: true
    name: your-existing-network-name
```

### 2. Connect Services

```bash
# Start the service
docker-compose up -d

# Verify it's on the network
docker network inspect your-existing-network-name
```

### 3. Access from Other Services

From other containers on the same network (like n8n):

```
http://xlsx-generator:8000/generate-xlsx
```

## n8n Integration

### HTTP Request Node Setup

1. Create HTTP Request node in n8n
2. Configure:
   - **Method**: POST
   - **URL**: `http://xlsx-generator:8000/generate-xlsx`
   - **Authentication**: None
   - **Body**: JSON

```json
{
  "template_name": "Template.xlsx",
  "data": {
    "field1": "{{ $json.field1 }}",
    "field2": "{{ $json.field2 }}"
  },
  "return_format": "base64"
}
```

3. Add Binary Data node to decode base64 if needed

### Complete n8n Workflow Example

```json
{
  "nodes": [
    {
      "name": "Generate XLSX",
      "type": "n8n-nodes-base.httpRequest",
      "position": [250, 300],
      "parameters": {
        "method": "POST",
        "url": "http://xlsx-generator:8000/generate-xlsx",
        "jsonParameters": true,
        "bodyParametersJson": "={{ {\n  \"template_name\": \"Template.xlsx\",\n  \"data\": $json,\n  \"return_format\": \"base64\"\n} }}",
        "options": {}
      }
    }
  ]
}
```

## Production Considerations

### 1. Environment Variables

Create `.env` file:

```env
# Service configuration
SERVICE_PORT=8000
TEMPLATE_DIR=/templates

# Security (if adding authentication)
API_KEY=your-secret-key
```

Update docker-compose.yml:

```yaml
services:
  xlsx-service:
    env_file: .env
    environment:
      - API_KEY=${API_KEY}
```

### 2. Resource Limits

Add to docker-compose.yml:

```yaml
services:
  xlsx-service:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### 3. Logging

Configure logging in docker-compose.yml:

```yaml
services:
  xlsx-service:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. Monitoring

Add health check monitoring:

```bash
# Add to crontab
*/5 * * * * curl -f http://localhost:8000/health || systemctl restart xlsx-service
```

### 5. Reverse Proxy (Nginx/Caddy)

Caddy configuration:

```caddy
xlsx.yourdomain.com {
    reverse_proxy localhost:8000
}
```

Nginx configuration:

```nginx
server {
    listen 80;
    server_name xlsx.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Updating the Service

### Update Code

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Update Templates

```bash
# Copy new templates
cp /path/to/new/template.xlsx templates/

# Update configuration in app/main.py
# Restart service
docker-compose restart
```

### Zero-Downtime Updates

```bash
# Build new image
docker-compose build

# Start new container
docker-compose up -d --no-deps --build xlsx-service

# Old container will be replaced automatically
```

## Backup and Recovery

### Backup Templates

```bash
# Create backup
tar -czf templates-backup-$(date +%Y%m%d).tar.gz templates/

# Restore from backup
tar -xzf templates-backup-20250119.tar.gz
```

### Export Configuration

```bash
# Backup configuration
cp app/main.py app/main.py.backup
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs xlsx-service

# Check port availability
netstat -tuln | grep 8000

# Check Docker network
docker network ls
docker network inspect avionai-network
```

### Template Not Found

```bash
# Verify templates are mounted
docker exec xlsx-generator ls -la /templates

# Check permissions
ls -la templates/
```

### Memory Issues

```bash
# Check container stats
docker stats xlsx-generator

# Increase memory limit in docker-compose.yml
```

### Connection Refused from n8n

```bash
# Verify network connectivity
docker exec n8n ping xlsx-generator

# Check if service is listening
docker exec xlsx-generator netstat -tuln | grep 8000
```

## Security Hardening

### 1. Add API Key Authentication

Update `app/main.py`:

```python
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

API_KEY = os.getenv("API_KEY", "your-secret-key")
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.post("/generate-xlsx", dependencies=[Depends(verify_api_key)])
async def generate_xlsx(request: GenerateXLSXRequest):
    # ... existing code
```

### 2. Read-Only Template Mount

```yaml
volumes:
  - ./templates:/templates:ro  # Read-only
```

### 3. Run as Non-Root

Update Dockerfile:

```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

## Performance Tuning

### 1. Increase Workers

Update docker-compose.yml:

```yaml
command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2. Add Gunicorn

```bash
# Install
pip install gunicorn

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## Monitoring and Alerts

### Prometheus Metrics

Add prometheus-fastapi-instrumentator:

```python
from prometheus_fastapi_instrumentator import Instrumentator

@app.on_event("startup")
async def startup():
    Instrumentator().instrument(app).expose(app)
```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status')

if [ "$HEALTH" != "healthy" ]; then
    echo "Service unhealthy!" | mail -s "XLSX Service Alert" admin@example.com
    docker-compose restart xlsx-service
fi
```

## Scaling

For high-volume deployments:

```yaml
services:
  xlsx-service:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
```

With load balancer (Nginx):

```nginx
upstream xlsx_backend {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    location / {
        proxy_pass http://xlsx_backend;
    }
}
```
