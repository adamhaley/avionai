"""
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import Dict, Union, Optional, List


class GenerateXLSXRequest(BaseModel):
    """Request model for XLSX generation"""
    template_name: str = Field(..., description="Name of the template file to use")
    data: Dict[str, Union[str, int, float]] = Field(
        ...,
        description="Dictionary of cell mappings (e.g., {'B3': 'value', 'C4': 123})"
    )
    return_format: str = Field(
        default="base64",
        description="Return format: 'base64' or 'file'"
    )
    sheet_name: Optional[str] = Field(
        default=None,
        description="Sheet name to modify (uses template config default if not specified)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "template_name": "invoice_template.xlsx",
                "data": {
                    "B3": "MSN12345",
                    "B4": "ABC Airlines",
                    "C10": 1500000.00
                },
                "return_format": "base64"
            }
        }


class GenerateXLSXResponse(BaseModel):
    """Response model for XLSX generation"""
    success: bool
    message: str
    file_name: Optional[str] = None
    data: Optional[str] = Field(None, description="Base64 encoded XLSX file (if return_format='base64')")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    templates_available: int


class TemplateInfo(BaseModel):
    """Information about a template"""
    name: str
    size_bytes: int
    sheet_name: Optional[str] = None
    fields: Optional[Dict[str, str]] = None


class TemplatesListResponse(BaseModel):
    """List of available templates"""
    templates: List[TemplateInfo]
    count: int
