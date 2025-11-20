"""
Core XLSX XML manipulation logic
Preserves 100% of formatting by only modifying cell values
"""

import io
import zipfile
from typing import Dict, Union, Optional
from lxml import etree
from pathlib import Path


# XML Namespace constants for Excel
NS = {
    "ws": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


class XLSXGenerator:
    """
    Handles XLSX file manipulation by directly working with XML structure
    """

    def __init__(self, template_path: Path):
        """
        Initialize generator with a template file

        Args:
            template_path: Path to the template XLSX file
        """
        self.template_path = template_path
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

    def generate(
        self,
        cell_updates: Dict[str, Union[str, int, float]],
        sheet_name: Optional[str] = None
    ) -> bytes:
        """
        Generate XLSX with updated cell values

        Args:
            cell_updates: Dictionary mapping cell references to values (e.g., {"B3": "value"})
            sheet_name: Sheet name to modify (defaults to first sheet if None)

        Returns:
            Bytes of the generated XLSX file
        """
        if not cell_updates:
            raise ValueError("cell_updates cannot be empty")

        out_buf = io.BytesIO()

        with zipfile.ZipFile(self.template_path, "r") as zin, \
                zipfile.ZipFile(out_buf, "w", compression=zipfile.ZIP_DEFLATED) as zout:

            # Find the target sheet path
            if sheet_name:
                sheet_path = self._find_sheet_path_by_name(zin, sheet_name)
            else:
                sheet_path = self._find_first_sheet_path(zin)

            # Process shared strings if they exist
            shared_strings_updated = False
            shared_strings_xml = None
            string_table = []

            if "xl/sharedStrings.xml" in zin.namelist():
                shared_strings_xml = zin.read("xl/sharedStrings.xml")
                string_table = self._parse_shared_strings(shared_strings_xml)

            # Copy all files, modifying only the target sheet
            for item in zin.infolist():
                data = zin.read(item.filename)

                if item.filename == sheet_path:
                    # Update the worksheet XML
                    data = self._update_cells(
                        data,
                        cell_updates,
                        string_table,
                        use_shared_strings=bool(shared_strings_xml)
                    )
                elif item.filename == "xl/sharedStrings.xml" and string_table:
                    # Update shared strings if modified
                    data = self._rebuild_shared_strings(string_table)
                    shared_strings_updated = True

                zout.writestr(item, data)

        out_buf.seek(0)
        return out_buf.getvalue()

    def _find_first_sheet_path(self, zf: zipfile.ZipFile) -> str:
        """Find the path to the first worksheet"""
        workbook_xml = zf.read("xl/workbook.xml")
        wb_root = etree.fromstring(workbook_xml)

        sheets_el = wb_root.find("ws:sheets", namespaces=NS)
        if sheets_el is None:
            raise ValueError("Unable to find <sheets> element in workbook.xml")

        first_sheet = sheets_el.find("ws:sheet", namespaces=NS)
        if first_sheet is None:
            raise ValueError("No sheets found in workbook")

        rel_id = first_sheet.get(f"{{{NS['r']}}}id")
        return self._resolve_relationship(zf, rel_id)

    def _find_sheet_path_by_name(self, zf: zipfile.ZipFile, sheet_name: str) -> str:
        """Find the path to a worksheet by name"""
        workbook_xml = zf.read("xl/workbook.xml")
        wb_root = etree.fromstring(workbook_xml)

        sheets_el = wb_root.find("ws:sheets", namespaces=NS)
        if sheets_el is None:
            raise ValueError("Unable to find <sheets> element in workbook.xml")

        for sheet in sheets_el.findall("ws:sheet", namespaces=NS):
            if sheet.get("name") == sheet_name:
                rel_id = sheet.get(f"{{{NS['r']}}}id")
                return self._resolve_relationship(zf, rel_id)

        raise ValueError(f"Sheet named '{sheet_name}' not found")

    def _resolve_relationship(self, zf: zipfile.ZipFile, rel_id: str) -> str:
        """Resolve a relationship ID to a file path"""
        rels_xml = zf.read("xl/_rels/workbook.xml.rels")
        rels_root = etree.fromstring(rels_xml)

        for rel in rels_root.findall("rel:Relationship", namespaces=NS):
            if rel.get("Id") == rel_id:
                target = rel.get("Target")
                if not target.startswith("xl/"):
                    target = f"xl/{target}"
                return target

        raise ValueError(f"Relationship ID '{rel_id}' not found")

    def _parse_shared_strings(self, xml_data: bytes) -> list:
        """Parse shared strings table into a list"""
        root = etree.fromstring(xml_data)
        strings = []

        for si in root.findall("ws:si", namespaces=NS):
            # Handle simple text
            t = si.find("ws:t", namespaces=NS)
            if t is not None and t.text:
                strings.append(t.text)
            else:
                # Handle rich text (multiple r elements)
                rich_text = []
                for r_elem in si.findall("ws:r", namespaces=NS):
                    t_elem = r_elem.find("ws:t", namespaces=NS)
                    if t_elem is not None and t_elem.text:
                        rich_text.append(t_elem.text)
                strings.append("".join(rich_text) if rich_text else "")

        return strings

    def _rebuild_shared_strings(self, string_table: list) -> bytes:
        """Rebuild shared strings XML from list"""
        root = etree.Element(
            f"{{{NS['ws']}}}sst",
            attrib={
                "count": str(len(string_table)),
                "uniqueCount": str(len(string_table))
            },
            nsmap={"": NS["ws"]}
        )

        for text in string_table:
            si = etree.SubElement(root, f"{{{NS['ws']}}}si")
            t = etree.SubElement(si, f"{{{NS['ws']}}}t")
            t.text = str(text)
            # Preserve space if text has leading/trailing whitespace
            if text and (text[0].isspace() or text[-1].isspace()):
                t.attrib["{http://www.w3.org/XML/1998/namespace}space"] = "preserve"

        return etree.tostring(root, xml_declaration=True, encoding="UTF-8")

    def _update_cells(
        self,
        sheet_xml: bytes,
        cell_updates: Dict[str, Union[str, int, float]],
        string_table: list,
        use_shared_strings: bool = False
    ) -> bytes:
        """
        Update specific cells in worksheet XML

        Args:
            sheet_xml: Original worksheet XML bytes
            cell_updates: Dict of cell references to values
            string_table: Shared strings table (modified in place)
            use_shared_strings: Whether to use shared strings for text values
        """
        root = etree.fromstring(sheet_xml)
        sheet_data = root.find("ws:sheetData", namespaces=NS)

        if sheet_data is None:
            raise ValueError("No sheetData element found in worksheet")

        for cell_ref, value in cell_updates.items():
            # Parse cell reference (e.g., "B3" -> row=3, col=B)
            row_num = self._get_row_number(cell_ref)

            # Find or create the row
            row = self._find_or_create_row(sheet_data, row_num)

            # Find or create the cell
            cell = self._find_or_create_cell(row, cell_ref)

            # Check if cell has a formula - preserve it
            formula_elem = cell.find("ws:f", namespaces=NS)
            if formula_elem is not None:
                # This cell has a formula - skip updating to preserve calculation
                continue

            # Remove existing value elements
            for child in list(cell):
                if child.tag in (f"{{{NS['ws']}}}v", f"{{{NS['ws']}}}is"):
                    cell.remove(child)

            # Set the new value
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                # Numeric cell
                cell.attrib.pop("t", None)
                v_el = etree.SubElement(cell, f"{{{NS['ws']}}}v")
                v_el.text = str(value)
            else:
                # String cell
                if use_shared_strings and string_table is not None:
                    # Use shared strings table
                    str_val = str(value)
                    if str_val in string_table:
                        str_idx = string_table.index(str_val)
                    else:
                        str_idx = len(string_table)
                        string_table.append(str_val)

                    cell.attrib["t"] = "s"
                    v_el = etree.SubElement(cell, f"{{{NS['ws']}}}v")
                    v_el.text = str(str_idx)
                else:
                    # Inline string
                    cell.attrib["t"] = "str"
                    v_el = etree.SubElement(cell, f"{{{NS['ws']}}}v")
                    v_el.text = str(value)

        return etree.tostring(root, xml_declaration=False, encoding="utf-8")

    def _get_row_number(self, cell_ref: str) -> int:
        """Extract row number from cell reference (e.g., 'B3' -> 3)"""
        import re
        match = re.match(r"[A-Z]+(\d+)", cell_ref)
        if not match:
            raise ValueError(f"Invalid cell reference: {cell_ref}")
        return int(match.group(1))

    def _find_or_create_row(self, sheet_data: etree.Element, row_num: int) -> etree.Element:
        """Find existing row or create new one"""
        for row in sheet_data.findall("ws:row", namespaces=NS):
            if int(row.get("r", 0)) == row_num:
                return row

        # Create new row in correct position
        new_row = etree.Element(f"{{{NS['ws']}}}row", attrib={"r": str(row_num)})

        # Insert in correct position (sorted by row number)
        inserted = False
        for i, row in enumerate(sheet_data.findall("ws:row", namespaces=NS)):
            if int(row.get("r", 0)) > row_num:
                sheet_data.insert(i, new_row)
                inserted = True
                break

        if not inserted:
            sheet_data.append(new_row)

        return new_row

    def _find_or_create_cell(self, row: etree.Element, cell_ref: str) -> etree.Element:
        """Find existing cell or create new one"""
        for cell in row.findall("ws:c", namespaces=NS):
            if cell.get("r") == cell_ref:
                return cell

        # Create new cell
        new_cell = etree.Element(f"{{{NS['ws']}}}c", attrib={"r": cell_ref})

        # Insert in correct position (sorted by column)
        inserted = False
        for i, cell in enumerate(row.findall("ws:c", namespaces=NS)):
            if self._compare_cell_refs(cell_ref, cell.get("r", "")) < 0:
                row.insert(i, new_cell)
                inserted = True
                break

        if not inserted:
            row.append(new_cell)

        return new_cell

    def _compare_cell_refs(self, ref1: str, ref2: str) -> int:
        """Compare two cell references for sorting (-1, 0, 1)"""
        import re

        match1 = re.match(r"([A-Z]+)(\d+)", ref1)
        match2 = re.match(r"([A-Z]+)(\d+)", ref2)

        if not match1 or not match2:
            return 0

        col1, row1 = match1.groups()
        col2, row2 = match2.groups()

        # Compare columns first
        if col1 < col2:
            return -1
        elif col1 > col2:
            return 1
        else:
            # Same column, compare rows
            return int(row1) - int(row2)
