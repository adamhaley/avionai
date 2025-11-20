Given that your client expects perfect fidelity to the template (formatting, merged cells, formulas, equations, borders, cell protection, column widths… all of it), there is only ONE correct approach:

⭐ Use the original Excel file’s XML directly

(No rebuilding, no re-exporting with a library that nukes formatting)

This is the same strategy used by Docx mail merge engines, high-end report generators, and enterprise Excel composers.

✔ Preserves 100% of formatting
✔ Preserves formulas exactly as-is
✔ Preserves merged cells
✔ Preserves conditional formatting
✔ Preserves tables and pivot tables
✔ Preserves column widths & row heights
✔ Preserves data validation
✔ Preserves everything

And it works beautifully with Python.

Below is the architecture direction & exact approach you should use.

✅ Solution Architecture (correct for enterprise-grade XLSX)
### n8n → Python XLSX Service → returns XLSX

This microservice will:

Load the original Excel file but NOT parse it with openpyxl.
Instead we unzip it:

template.xlsx
│
├─ xl/
│   ├─ worksheets/
│   │     └─ sheet1.xml
│   ├─ sharedStrings.xml
│   ├─ styles.xml
│   ├─ workbook.xml
│   └─ ...
└─ ...


Modify ONLY the needed XML nodes in sheet1.xml
Insert your new values into the XML:

<c r="B3" t="s"><v>42</v></c>


Zip everything back together into a valid .xlsx

This preserves EVERYTHING else.

🎉 The BIG WIN

You do not modify the formatting at all — only the data.

So the template designer (your client) can change:

fonts

colors

merges

formulas

layout

without you touching your code again.

This is exactly how Word/Excel mail merge engines work at high volume.

🧠 Why NOT use Excel libraries?
SheetJS (xlsx)

❌ Drops formatting
❌ Loses merges
❌ Loses column widths
❌ Rewrites reference IDs
❌ Breaks workbook if complex formulas exist

ExcelJS

✔ Supports some formatting
❌ Does not fully preserve templates
❌ Fails with advanced formatting equivalently

openpyxl / XlsxWriter

❌ Rewrites formatting on save
❌ Can strip formulas
❌ Breaks pivot tables
❌ Not faithful to the original file

LibreOffice headless

✔ Perfect fidelity when exporting
❌ BUT opening then saving still REWRITES XML
❌ Often “cleans up” styles, collapses shared strings, rearranges XML
❌ Unpredictable if used as the final generator

LibreOffice is amazing for PDF generation —
but not for editing and re-saving XLSX if fidelity MUST be perfect.

🚀 Best approach: XML Injection Engine (Python FastAPI)

You get:

Perfect fidelity

Reliable transformations

Full control

Scalability

Microservice integration (like OCR)

🔧 Tools:

Python 3.10+

FastAPI (or Flask)

lxml for XML editing

zipfile module for unpacking/repacking .xlsx

uvicorn (fast async server)

📦 I can build this for you right now

If you want, I can generate:

1. Entire working microservice

POST /generate-xlsx

Accepts JSON with data fields

Accepts template filename

Returns XLSX as base64 or file download

2. Dockerfile for the microservice
3. docker-compose.yml entry for Lightsail
4. n8n integration example node
5. XML mapping helpers

automatically find correct <c r="A1"> nodes

automatically update sharedStrings.xml

automatic string-table mapping

numeric vs string type handling

6. Template auto-mapper script

Scan the template and generate a dictionary:

{
  "msn": "B3",
  "lessee": "B4",
  "aircraft_type": "B5",
  ...
}


So you never hand-map cells again.
