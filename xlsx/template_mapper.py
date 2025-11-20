#!/usr/bin/env python3
"""
Template Mapper Utility

Scans an Excel template and helps generate field mappings for the service.
Extracts cell references with values to help you identify which cells need to be populated.

Usage:
    python template_mapper.py path/to/template.xlsx [--sheet "Sheet Name"]
"""

import sys
import zipfile
import argparse
from pathlib import Path
from lxml import etree
import json


NS = {
    "ws": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def parse_shared_strings(zf: zipfile.ZipFile) -> list:
    """Parse shared strings table"""
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []

    xml_data = zf.read("xl/sharedStrings.xml")
    root = etree.fromstring(xml_data)
    strings = []

    for si in root.findall("ws:si", namespaces=NS):
        t = si.find("ws:t", namespaces=NS)
        if t is not None and t.text:
            strings.append(t.text)
        else:
            # Handle rich text
            rich_text = []
            for r_elem in si.findall("ws:r", namespaces=NS):
                t_elem = r_elem.find("ws:t", namespaces=NS)
                if t_elem is not None and t_elem.text:
                    rich_text.append(t_elem.text)
            strings.append("".join(rich_text) if rich_text else "")

    return strings


def find_sheet_path(zf: zipfile.ZipFile, sheet_name: str = None) -> str:
    """Find worksheet path by name, or return first sheet"""
    workbook_xml = zf.read("xl/workbook.xml")
    wb_root = etree.fromstring(workbook_xml)

    sheets_el = wb_root.find("ws:sheets", namespaces=NS)
    if sheets_el is None:
        raise ValueError("Unable to find <sheets> element")

    # Get target sheet
    target_sheet = None
    if sheet_name:
        for sheet in sheets_el.findall("ws:sheet", namespaces=NS):
            if sheet.get("name") == sheet_name:
                target_sheet = sheet
                break
        if not target_sheet:
            raise ValueError(f"Sheet '{sheet_name}' not found")
    else:
        target_sheet = sheets_el.find("ws:sheet", namespaces=NS)

    rel_id = target_sheet.get(f"{{{NS['r']}}}id")

    # Resolve relationship
    rels_xml = zf.read("xl/_rels/workbook.xml.rels")
    rels_root = etree.fromstring(rels_xml)

    for rel in rels_root.findall("rel:Relationship", namespaces=NS):
        if rel.get("Id") == rel_id:
            target = rel.get("Target")
            if not target.startswith("xl/"):
                target = f"xl/{target}"
            return target

    raise ValueError(f"Relationship '{rel_id}' not found")


def list_sheets(zf: zipfile.ZipFile) -> list:
    """List all sheet names in workbook"""
    workbook_xml = zf.read("xl/workbook.xml")
    wb_root = etree.fromstring(workbook_xml)

    sheets_el = wb_root.find("ws:sheets", namespaces=NS)
    if sheets_el is None:
        return []

    return [sheet.get("name") for sheet in sheets_el.findall("ws:sheet", namespaces=NS)]


def analyze_sheet(zf: zipfile.ZipFile, sheet_path: str, shared_strings: list) -> list:
    """Analyze sheet and return cells with their values"""
    sheet_xml = zf.read(sheet_path)
    root = etree.fromstring(sheet_xml)

    cells = []
    for c in root.findall(".//ws:c", namespaces=NS):
        cell_ref = c.get("r")
        cell_type = c.get("t", "n")  # Default to numeric

        v_elem = c.find("ws:v", namespaces=NS)
        f_elem = c.find("ws:f", namespaces=NS)

        value = None
        value_type = "empty"

        if f_elem is not None:
            # Formula cell
            value = f"=FORMULA={f_elem.text or ''}"
            value_type = "formula"
        elif v_elem is not None and v_elem.text:
            if cell_type == "s":
                # Shared string
                idx = int(v_elem.text)
                if idx < len(shared_strings):
                    value = shared_strings[idx]
                    value_type = "string"
            elif cell_type == "str":
                # Inline string
                value = v_elem.text
                value_type = "string"
            elif cell_type == "b":
                # Boolean
                value = v_elem.text == "1"
                value_type = "boolean"
            else:
                # Numeric
                value = v_elem.text
                value_type = "number"

        if value is not None:
            cells.append({
                "ref": cell_ref,
                "type": value_type,
                "value": value
            })

    return cells


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Excel template and generate field mappings"
    )
    parser.add_argument("template", help="Path to template .xlsx file")
    parser.add_argument(
        "--sheet",
        help="Specific sheet name to analyze (default: first sheet)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON format"
    )
    parser.add_argument(
        "--list-sheets",
        action="store_true",
        help="List all sheets in the workbook"
    )

    args = parser.parse_args()

    template_path = Path(args.template)
    if not template_path.exists():
        print(f"Error: Template file not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with zipfile.ZipFile(template_path, "r") as zf:
            # List sheets if requested
            if args.list_sheets:
                sheets = list_sheets(zf)
                print(f"\nSheets in {template_path.name}:")
                for i, sheet in enumerate(sheets, 1):
                    print(f"  {i}. {sheet}")
                sys.exit(0)

            # Parse shared strings
            shared_strings = parse_shared_strings(zf)

            # Find target sheet
            sheet_path = find_sheet_path(zf, args.sheet)
            sheet_name = args.sheet or "first sheet"

            # Analyze cells
            cells = analyze_sheet(zf, sheet_path, shared_strings)

            if args.json:
                # Output as JSON
                output = {
                    "template": template_path.name,
                    "sheet": sheet_name,
                    "cells": cells
                }
                print(json.dumps(output, indent=2))
            else:
                # Human-readable output
                print(f"\n{'='*70}")
                print(f"Template: {template_path.name}")
                print(f"Sheet: {sheet_name}")
                print(f"Total cells with values: {len(cells)}")
                print(f"{'='*70}\n")

                print("Cell Reference | Type    | Value")
                print("-" * 70)

                for cell in sorted(cells, key=lambda x: (x["ref"])):
                    ref = cell["ref"].ljust(14)
                    ctype = cell["type"].ljust(8)
                    value = str(cell["value"])
                    if len(value) > 45:
                        value = value[:42] + "..."

                    print(f"{ref} | {ctype} | {value}")

                print("\n" + "="*70)
                print("\nSuggested field mapping for app/main.py:")
                print("="*70)
                print(f"""
TEMPLATE_CONFIG = {{
    "{template_path.name}": {{
        "sheet_name": "{sheet_name}",
        "fields": {{
            # Map your field names to cell references below:
            # "field_name": "CELL_REF",
""")

                # Suggest mappings for cells that look like labels
                suggestions = []
                for cell in cells:
                    if cell["type"] == "string" and len(str(cell["value"])) > 0:
                        # Create a field name suggestion
                        field_name = str(cell["value"]).lower()
                        field_name = "".join(c if c.isalnum() else "_" for c in field_name)
                        field_name = field_name.strip("_")[:30]
                        if field_name:
                            suggestions.append(f'            # "{field_name}": "{cell["ref"]}",')

                if suggestions:
                    print("            # Suggestions based on cell content:")
                    for suggestion in suggestions[:10]:  # Limit to 10 suggestions
                        print(suggestion)

                print("""        }},
    }},
}}
""")

    except Exception as e:
        print(f"Error analyzing template: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
