# FastAPI XLSX Generation Service - Implementation Plan

## Overview
Build a FastAPI microservice that accepts JSON input and generates Excel files by directly manipulating the XML structure of template .xlsx files, preserving 100% of the original formatting.

## Architecture
```
JSON Input → FastAPI Service → XML Manipulation → XLSX Output
```

## Implementation Steps

### 1. Project Setup
- [ ] Create Python virtual environment
- [ ] Install dependencies:
  - `fastapi` - Web framework
  - `uvicorn` - ASGI server
  - `lxml` - XML manipulation
  - `pydantic` - Data validation
- [ ] Create project structure:
  ```
  /
  ├── app/
  │   ├── __init__.py
  │   ├── main.py           # FastAPI app
  │   ├── xlsx_generator.py # Core XML manipulation logic
  │   └── models.py         # Pydantic models
  ├── templates/            # Excel templates directory
  ├── requirements.txt
  ├── Dockerfile
  └── docker-compose.yml
  ```

### 2. Core XLSX Generator Module (`xlsx_generator.py`)
- [ ] Create `XLSXGenerator` class with methods:
  - `unzip_xlsx(template_path)` - Extract .xlsx to temp directory
  - `parse_sheet_xml(sheet_path)` - Parse worksheet XML with lxml
  - `update_cell(cell_ref, value, value_type)` - Modify specific cell XML node
  - `update_shared_strings(value)` - Add/update shared strings table
  - `zip_xlsx(temp_dir, output_path)` - Repackage as .xlsx
- [ ] Implement cell reference handling (e.g., "B3" → row/col mapping)
- [ ] Handle different value types:
  - String (t="s") → shared strings reference
  - Number (t="n") → direct value
  - Formula → preserve existing formula nodes

### 3. FastAPI Endpoints (`main.py`)
- [ ] `POST /generate-xlsx` - Main endpoint
  - Accept JSON body with:
    - `template_name` - Template file to use
    - `data` - Dictionary of cell mappings: `{"B3": "MSN12345", "B4": "Airline Corp", ...}`
  - Return XLSX file as StreamingResponse or base64
- [ ] `GET /health` - Health check endpoint
- [ ] `GET /templates` - List available templates
- [ ] Add error handling and validation

### 4. Data Models (`models.py`)
- [ ] Create Pydantic models:
  ```python
  class GenerateXLSXRequest(BaseModel):
      template_name: str
      data: Dict[str, Union[str, int, float]]
      return_format: str = "file"  # or "base64"

  class GenerateXLSXResponse(BaseModel):
      success: bool
      message: str
      file_name: Optional[str]
      data: Optional[str]  # base64 if requested
  ```

### 5. Template Mapping Helper (Optional Enhancement)
- [ ] Create `template_mapper.py` script
- [ ] Scan template and extract cell references with named ranges or comments
- [ ] Generate mapping configuration file:
  ```json
  {
    "invoice_template.xlsx": {
      "msn": "B3",
      "lessee": "B4",
      "aircraft_type": "B5"
    }
  }
  ```

### 6. Docker Configuration
- [ ] Create `Dockerfile`:
  - Use Python 3.10+ base image
  - Install dependencies
  - Copy application code
  - Expose port 8000
  - Run with uvicorn
- [ ] Create `docker-compose.yml`:
  - Define service
  - Mount templates directory as volume
  - Configure ports and networking
  - Add to existing Lightsail setup

### 7. Testing
- [ ] Create test template with various formatting
- [ ] Test endpoints with sample JSON data
- [ ] Verify output preserves:
  - Formatting (fonts, colors, borders)
  - Merged cells
  - Formulas
  - Column widths/row heights
  - Data validation
  - Conditional formatting
- [ ] Test edge cases (missing cells, invalid refs, large files)

### 8. n8n Integration
- [ ] Create n8n HTTP Request node configuration
- [ ] Test JSON → XLSX workflow
- [ ] Document integration steps

## API Usage Example

```bash
curl -X POST http://localhost:8000/generate-xlsx \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "invoice_template.xlsx",
    "data": {
      "B3": "MSN12345",
      "B4": "ABC Airlines",
      "B5": "Boeing 737-800",
      "C10": 1500000.00
    },
    "return_format": "file"
  }' \
  --output generated_invoice.xlsx
```

## Key Technical Details

### XML Structure
- XLSX files are ZIP archives containing XML files
- Main worksheet data: `xl/worksheets/sheet1.xml`
- Shared strings: `xl/sharedStrings.xml`
- Cell format: `<c r="A1" t="s"><v>0</v></c>`
  - `r` = cell reference
  - `t` = type (s=string, n=number, str=formula)
  - `v` = value (index for strings, direct value for numbers)

### String Handling
- Strings stored in shared strings table to reduce file size
- Must update both the cell reference AND the shared strings XML
- Maintain proper indexing

### Preservation Strategy
- NEVER parse with openpyxl/xlsxwriter (they rewrite everything)
- Only modify specific XML nodes for data cells
- Leave all style/formatting XML untouched
- Preserve original ZIP structure and metadata

## Success Criteria
- Template formatting 100% preserved after data injection
- Fast response time (<1 second for typical files)
- Handles multiple concurrent requests
- Integrates seamlessly with n8n workflows
- Easy to add new templates (just drop in templates folder)
