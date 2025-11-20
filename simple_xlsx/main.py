from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Union
import io
import base64
import zipfile
from lxml import etree
from pathlib import Path
import datetime as dt

app = FastAPI()

# Where templates are mounted inside the container
TEMPLATE_DIR = Path("/templates")

# Namespace constants for Excel XML
NS = {
    "ws": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# 🔧 FIELD → CELL mappings per template
# TODO: update the cell refs to match your actual template layout
TEMPLATE_FIELD_MAP: Dict[str, Dict[str, str]] = {
    "Template.xlsx": {   # file name in /templates
        "msn": "C6",
        "aircraft_type": "C7",
        "lessee": "C9",
        "engine_type": "C10",
        # ... add all the other fields you care about
    },
    # You can add more templates here if needed
}


class GeneratePayload(BaseModel):
    template: str  # e.g. "Template.xlsx"
    fields: Dict[str, Union[str, int, float]]  # {"msn": "000001", ...}


class GenerateResponse(BaseModel):
    file_name: str
    mime_type: str
    data: str  # base64 XLSX


def _find_sheet_path(zf: zipfile.ZipFile, sheet_name: str) -> str:
    """
    Given a sheet name, find the path to its XML inside the .xlsx zip.
    Returns something like 'xl/worksheets/sheet1.xml'.
    """
    workbook_xml = zf.read("xl/workbook.xml")
    wb_root = etree.fromstring(workbook_xml)

    sheets_el = wb_root.find("ws:sheets", namespaces=NS)
    if sheets_el is None:
        raise ValueError("Unable to find <sheets> element in workbook.xml")

    rel_id = None
    for sheet in sheets_el.findall("ws:sheet", namespaces=NS):
        if sheet.get("name") == sheet_name:
            rel_id = sheet.get(f"{{{NS['r']}}}id")
            break

    if rel_id is None:
        raise ValueError(f"Sheet named '{sheet_name}' not found in workbook.xml")

    # Now resolve the rel_id to a target path using workbook.xml.rels
    rels_xml = zf.read("xl/_rels/workbook.xml.rels")
    rels_root = etree.fromstring(rels_xml)

    target = None
    for rel in rels_root.findall("rel:Relationship", namespaces=NS):
        if rel.get("Id") == rel_id:
            target = rel.get("Target")
            break

    if target is None:
        raise ValueError(f"Target for rel id '{rel_id}' not found in workbook.xml.rels")

    # Usually something like 'worksheets/sheet1.xml'
    if not target.startswith("xl/"):
        target = f"xl/{target}"
    return target


def _update_cells(sheet_xml: bytes, cell_updates: Dict[str, Union[str, int, float]]) -> bytes:
    """
    Update specific cells in a sheet's XML, preserving styles and formatting.

    cell_updates: {"C6": "000001", "C7": "A319-113", ...}
    """
    root = etree.fromstring(sheet_xml)

    for cell_ref, value in cell_updates.items():
        # Find the <c> element with r="C6" etc.
        c = root.find(f".//ws:c[@r='{cell_ref}']", namespaces=NS)
        if c is None:
            # For now, fail loudly; you can relax this later if you want.
            raise ValueError(f"Cell {cell_ref} not found in sheet XML")

        # Remove existing <v> or <is> children
        for child in list(c):
            # tag names with namespace
            if child.tag in (
                f"{{{NS['ws']}}}v",
                f"{{{NS['ws']}}}is",
            ):
                c.remove(child)

        # Decide if this should be numeric or string
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            # Numeric cell
            c.attrib.pop("t", None)  # remove any existing t attr
            v_el = etree.SubElement(c, f"{{{NS['ws']}}}v")
            v_el.text = str(value)
        else:
            # String cell
            c.attrib["t"] = "str"
            v_el = etree.SubElement(c, f"{{{NS['ws']}}}v")
            v_el.text = str(value)

    return etree.tostring(root, xml_declaration=False, encoding="utf-8")

@app.get("/")
def root():
    return {
        "service": "xlsx-generator",
        "status": "online",
        "message": "XLSX generation service is running 🚀"
    }

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate-xlsx", response_model=GenerateResponse)
def generate_xlsx(payload: GeneratePayload):
    template_path = TEMPLATE_DIR / payload.template
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template '{payload.template}' not found")

    field_map = TEMPLATE_FIELD_MAP.get(payload.template)
    if not field_map:
        raise HTTPException(status_code=400, detail=f"No field map configured for '{payload.template}'")

    # Map incoming fields -> cells
    cell_updates: Dict[str, Union[str, int, float]] = {}
    for field_name, cell_ref in field_map.items():
        if field_name in payload.fields:
            cell_updates[cell_ref] = payload.fields[field_name]

    if not cell_updates:
        raise HTTPException(status_code=400, detail="No matching fields for template")

    # Work entirely in memory
    out_buf = io.BytesIO()

    with zipfile.ZipFile(template_path, "r") as zin, \
            zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as zout:

        # Find the path for the 'Maintenance Template' sheet, or just use the first sheet
        # If your template always uses that name, you can hardcode it.
        try:
            sheet_path = _find_sheet_path(zin, sheet_name="Maintenance Template")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error locating sheet: {e}")

        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == sheet_path:
                # Patch the sheet XML with our new values
                try:
                    data = _update_cells(data, cell_updates)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Error updating cells: {e}")

            zout.writestr(item, data)

    out_buf.seek(0)
    xlsx_bytes = out_buf.getvalue()
    b64 = base64.b64encode(xlsx_bytes).decode("ascii")

    file_name = f"lease-summary-{payload.fields.get('msn', '') or int(dt.datetime.utcnow().timestamp())}.xlsx"

    return GenerateResponse(
        file_name=file_name,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        data=b64,
    )

