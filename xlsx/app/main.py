"""
FastAPI application for XLSX generation service
"""

import base64
import datetime as dt
from pathlib import Path
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import io

from app.models import (
    GenerateXLSXRequest,
    GenerateXLSXResponse,
    HealthResponse,
    TemplatesListResponse,
    TemplateInfo,
)
from app.xlsx_generator import XLSXGenerator
from app import __version__

app = FastAPI(
    title="XLSX Generation Service",
    description="Generate Excel files by directly manipulating XML structure of templates",
    version=__version__,
)

# Template directory (mounted as volume in Docker)
TEMPLATE_DIR = Path("/templates")

# Template configuration: maps template names to their settings
TEMPLATE_CONFIG: Dict[str, Dict] = {
    "Template.xlsx": {
        "sheet_name": "Maintenance Template",
        "fields": {
            "msn": "C6",
            "aircraft_type": "C7",
            "lessee": "C9",
            "engine_type": "C10",
        },
    },
    # Add more templates as needed
}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns service status and number of available templates
    """
    templates_count = 0
    if TEMPLATE_DIR.exists():
        templates_count = len(list(TEMPLATE_DIR.glob("*.xlsx")))

    return HealthResponse(
        status="healthy",
        version=__version__,
        templates_available=templates_count,
    )


@app.get("/templates", response_model=TemplatesListResponse)
async def list_templates():
    """
    List all available templates
    Returns template names, sizes, and configured fields
    """
    if not TEMPLATE_DIR.exists():
        return TemplatesListResponse(templates=[], count=0)

    templates = []
    for template_path in TEMPLATE_DIR.glob("*.xlsx"):
        template_name = template_path.name
        config = TEMPLATE_CONFIG.get(template_name, {})

        templates.append(
            TemplateInfo(
                name=template_name,
                size_bytes=template_path.stat().st_size,
                sheet_name=config.get("sheet_name"),
                fields=config.get("fields"),
            )
        )

    return TemplatesListResponse(templates=templates, count=len(templates))


@app.post("/generate-xlsx", response_model=GenerateXLSXResponse)
async def generate_xlsx(request: GenerateXLSXRequest):
    """
    Generate XLSX file from template with provided data

    Args:
        request: Contains template_name, data (cell mappings), return_format, and optional sheet_name

    Returns:
        GenerateXLSXResponse with base64 data or file download

    Example request body:
    {
        "template_name": "Template.xlsx",
        "data": {"B3": "MSN12345", "C4": "ABC Airlines"},
        "return_format": "base64"
    }
    """
    template_path = TEMPLATE_DIR / request.template_name

    # Validate template exists
    if not template_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Template '{request.template_name}' not found"
        )

    # Get template configuration
    config = TEMPLATE_CONFIG.get(request.template_name, {})

    # Determine sheet name
    sheet_name = request.sheet_name or config.get("sheet_name")

    # Check if data uses field names that need mapping
    field_map = config.get("fields", {})
    cell_updates = {}

    for key, value in request.data.items():
        # If key is a field name (exists in field_map), map it to cell reference
        if key in field_map:
            cell_ref = field_map[key]
            cell_updates[cell_ref] = value
        else:
            # Assume it's already a cell reference (e.g., "B3")
            cell_updates[key] = value

    if not cell_updates:
        raise HTTPException(
            status_code=400,
            detail="No valid cell updates provided. Use field names or cell references.",
        )

    # Generate XLSX
    try:
        generator = XLSXGenerator(template_path)
        xlsx_bytes = generator.generate(cell_updates, sheet_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating XLSX: {str(e)}"
        )

    # Generate filename
    file_name = f"generated-{request.template_name.replace('.xlsx', '')}-{int(dt.datetime.utcnow().timestamp())}.xlsx"

    # Return based on format
    if request.return_format == "file":
        # Return as downloadable file
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    else:
        # Return as base64
        b64_data = base64.b64encode(xlsx_bytes).decode("ascii")
        return GenerateXLSXResponse(
            success=True,
            message="XLSX generated successfully",
            file_name=file_name,
            data=b64_data,
        )


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "XLSX Generation Service",
        "version": __version__,
        "endpoints": {
            "health": "GET /health",
            "templates": "GET /templates",
            "generate": "POST /generate-xlsx",
            "docs": "GET /docs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
