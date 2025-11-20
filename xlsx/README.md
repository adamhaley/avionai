# XLSX Generation Service

A FastAPI microservice that generates Excel files by directly manipulating the XML structure of template files, preserving 100% of the original formatting.

## Features

- ✅ **Perfect Fidelity**: Preserves all formatting, formulas, merged cells, conditional formatting, etc.
- ✅ **XML-Based**: Directly manipulates Excel XML instead of using libraries that rewrite files
- ✅ **Fast**: In-memory processing with no temporary files
- ✅ **RESTful API**: Simple JSON-based API
- ✅ **Docker Ready**: Containerized with Docker Compose support
- ✅ **Flexible Output**: Return as base64 or downloadable file
- ✅ **Field Mapping**: Support for both cell references (B3) and named fields (msn, lessee)

## Architecture

```
JSON Input → FastAPI Service → XML Manipulation → XLSX Output
```

The service:
1. Unzips the template XLSX file
2. Modifies only the specific cell XML nodes with new data
3. Preserves all formatting, styles, formulas, and structure
4. Rezips into a valid XLSX file

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Build and start the service
docker-compose up -d

# Check health
curl http://localhost:8000/health

# List available templates
curl http://localhost:8000/templates
```

### Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Usage

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "templates_available": 2
}
```

### List Templates

```bash
GET /templates
```

Response:
```json
{
  "templates": [
    {
      "name": "Template.xlsx",
      "size_bytes": 12345,
      "sheet_name": "Maintenance Template",
      "fields": {
        "msn": "C6",
        "aircraft_type": "C7",
        "lessee": "C9"
      }
    }
  ],
  "count": 1
}
```

### Generate XLSX

```bash
POST /generate-xlsx
Content-Type: application/json

{
  "template_name": "Template.xlsx",
  "data": {
    "B3": "MSN12345",
    "B4": "ABC Airlines",
    "C10": 1500000.00
  },
  "return_format": "base64"
}
```

Or using field names (if configured):

```bash
POST /generate-xlsx
Content-Type: application/json

{
  "template_name": "Template.xlsx",
  "data": {
    "msn": "MSN12345",
    "lessee": "ABC Airlines",
    "aircraft_type": "Boeing 737-800"
  },
  "return_format": "file"
}
```

Response (base64 format):
```json
{
  "success": true,
  "message": "XLSX generated successfully",
  "file_name": "generated-Template-1234567890.xlsx",
  "data": "UEsDBBQABgAIAAAAIQD..."
}
```

Response (file format):
- Returns downloadable XLSX file

### Using curl

```bash
# Generate and save to file
curl -X POST http://localhost:8000/generate-xlsx \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "Template.xlsx",
    "data": {"B3": "MSN12345", "B4": "ABC Airlines"},
    "return_format": "file"
  }' \
  --output generated.xlsx

# Generate as base64
curl -X POST http://localhost:8000/generate-xlsx \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "Template.xlsx",
    "data": {"msn": "MSN12345", "lessee": "ABC Airlines"},
    "return_format": "base64"
  }'
```

## Configuration

### Adding New Templates

1. Place your `.xlsx` template file in the `templates/` directory
2. Update `app/main.py` to add template configuration:

```python
TEMPLATE_CONFIG: Dict[str, Dict] = {
    "YourTemplate.xlsx": {
        "sheet_name": "Sheet1",  # Optional: specific sheet name
        "fields": {              # Optional: field name to cell mapping
            "field1": "B3",
            "field2": "C5",
        },
    },
}
```

3. Restart the service

### Environment Variables

- `TEMPLATE_DIR`: Directory containing templates (default: `/templates`)

## n8n Integration

### HTTP Request Node Configuration

```json
{
  "method": "POST",
  "url": "http://xlsx-service:8000/generate-xlsx",
  "authentication": "none",
  "requestFormat": "json",
  "bodyParameters": {
    "template_name": "Template.xlsx",
    "data": {
      "msn": "{{ $json.msn }}",
      "lessee": "{{ $json.lessee }}"
    },
    "return_format": "base64"
  }
}
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Project Structure

```
/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app and endpoints
│   ├── xlsx_generator.py # Core XML manipulation logic
│   └── models.py         # Pydantic models
├── templates/            # Excel templates directory
├── tests/                # Test suite
│   ├── test_api.py
│   └── test_xlsx_generator.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## How It Works

### XML Manipulation Strategy

Excel `.xlsx` files are actually ZIP archives containing XML files:

```
template.xlsx (ZIP)
├── xl/
│   ├── worksheets/
│   │   └── sheet1.xml       ← Cell data here
│   ├── sharedStrings.xml    ← String values
│   ├── styles.xml           ← Formatting (untouched)
│   └── workbook.xml         ← Structure (untouched)
```

The service:
1. Extracts the ZIP
2. Parses `sheet1.xml` with lxml
3. Updates only `<c>` (cell) elements:
   ```xml
   <c r="B3" t="s"><v>42</v></c>
   ```
4. Maintains shared strings table for text values
5. Preserves formulas (skips cells with `<f>` elements)
6. Recreates the ZIP

### Why Not Use Excel Libraries?

| Library | Issue |
|---------|-------|
| openpyxl | ❌ Rewrites formatting on save |
| XlsxWriter | ❌ Write-only, can't preserve templates |
| pandas | ❌ Loses formatting, merges, formulas |
| ExcelJS | ❌ Incomplete format preservation |

**This approach** = ✅ 100% fidelity

## Troubleshooting

### Service won't start
- Check Docker logs: `docker-compose logs xlsx-service`
- Verify port 8000 is available
- Ensure templates directory exists and is mounted

### Template not found
- Verify template is in `templates/` directory
- Check file permissions (must be readable)
- Confirm exact filename match (case-sensitive)

### Generated file is corrupted
- Verify template is a valid `.xlsx` file (not `.xls`)
- Check that cell references are valid (e.g., "B3" not "B03")
- Ensure no circular formula dependencies

### Formula not calculating
- Excel formulas are preserved but not evaluated
- Open file in Excel to trigger recalculation
- Or set calculation mode in template

## License

MIT

## Support

For issues or questions, contact the development team or open an issue in the repository.
