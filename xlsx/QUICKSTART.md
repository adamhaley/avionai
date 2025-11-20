# Quick Start Guide

Get the XLSX Generation Service running in 5 minutes.

## Step 1: Add Your Template

```bash
# Copy your Excel template to the templates directory
cp /path/to/your/template.xlsx templates/
```

## Step 2: Analyze Your Template

```bash
# Use the template mapper to see all cells with values
python template_mapper.py templates/template.xlsx

# Or list all sheets first
python template_mapper.py templates/template.xlsx --list-sheets

# Analyze a specific sheet
python template_mapper.py templates/template.xlsx --sheet "Sheet1"
```

This will show you all cell references and suggest field mappings.

## Step 3: Configure Field Mappings

Edit `app/main.py` and add your template configuration:

```python
TEMPLATE_CONFIG: Dict[str, Dict] = {
    "template.xlsx": {
        "sheet_name": "Sheet1",  # Your sheet name
        "fields": {
            # Map your field names to cell references
            "company_name": "B3",
            "date": "D3",
            "amount": "C10",
            # Add more mappings...
        },
    },
}
```

## Step 4: Start the Service

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or using make
make run

# Or run locally for development
make dev
```

## Step 5: Test It

```bash
# Check health
curl http://localhost:8000/health

# List templates
curl http://localhost:8000/templates

# Generate a test XLSX
curl -X POST http://localhost:8000/generate-xlsx \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "template.xlsx",
    "data": {
      "company_name": "Acme Corp",
      "date": "2025-01-19",
      "amount": 50000.00
    },
    "return_format": "file"
  }' \
  --output test-output.xlsx

# Open test-output.xlsx in Excel to verify
```

## Step 6: Integrate with n8n

1. Add HTTP Request node
2. Set URL: `http://xlsx-generator:8000/generate-xlsx`
3. Method: POST
4. Body:
```json
{
  "template_name": "template.xlsx",
  "data": {
    "company_name": "{{ $json.company }}",
    "amount": "{{ $json.total }}"
  },
  "return_format": "base64"
}
```

## Common Commands

```bash
# View logs
make logs

# Restart service
make restart

# Run example script
make example

# Stop service
make stop

# Run tests
make test
```

## Troubleshooting

### Service won't start
```bash
# Check if port 8000 is in use
netstat -tuln | grep 8000

# Check Docker logs
docker-compose logs xlsx-service
```

### Template not found
```bash
# Verify template exists
ls -la templates/

# Check it's mounted in container
docker exec xlsx-generator ls -la /templates
```

### Cell not updating
```bash
# Verify cell reference with template mapper
python template_mapper.py templates/your-template.xlsx

# Make sure cell reference is correct (case-sensitive)
# "B3" is correct, "b3" will not work
```

## Next Steps

- Read [README.md](README.md) for detailed API documentation
- See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Check [example_usage.py](example_usage.py) for more examples
- Run `template_mapper.py` on your templates to map fields

## Support

For issues or questions:
- Check logs: `make logs`
- View docs: http://localhost:8000/docs
- Test health: http://localhost:8000/health
