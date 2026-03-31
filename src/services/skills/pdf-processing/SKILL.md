---
name: pdf-processing
description: >
  Use this skill for any task involving PDF files.
  Trigger when the user wants to: read or extract text from a PDF, extract tables or data
  into Excel / CSV / JSON, or create and write a new PDF from text or markdown content.
  Do NOT use for Word documents (.docx) — use the docx skill instead.
version: 2.0.0
---

# Skill: PDF Processing

Handle PDF read, write, and data-extraction operations.

---

## How to determine `<DEEPAGENTFORCE_ROOT>`

All script paths use `<DEEPAGENTFORCE_ROOT>` — the **absolute path to the DeepAgentForce
project root** on the current host. Resolve it once at runtime:
```bash
find / -type d -name "DeepAgentForce" 2>/dev/null | head -1
# Example: /home/user/projects/DeepAgentForce
```

All scripts live at:
```
<DEEPAGENTFORCE_ROOT>/src/services/skills/pdf-processing/scripts/
```

---

## Script Selection
```
User mentions PDF
  ├─ "read" / "extract text" / "content"        → extract_text.py
  ├─ "table" / "data" / "spreadsheet" / "excel" → extract_tables.py
  └─ "create" / "write" / "generate" a PDF      → write_pdf.py
```

---

## Scripts

### 1. `extract_text.py` — Extract text from PDF
```bash
python <DEEPAGENTFORCE_ROOT>/src/services/skills/pdf-processing/scripts/extract_text.py \
  <pdf_path> [--pages PAGES] [--output OUTPUT]
```

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pdf_path` | ✅ | — | Path to PDF file |
| `--pages` | ❌ | all | Page range: `"1-5"` or `"1,3,5"` |
| `--output` | ❌ | stdout | Save extracted text to file |

**Examples:**
```bash
# Extract all text
python .../extract_text.py report.pdf

# Specific pages
python .../extract_text.py report.pdf --pages "1-5"

# Save to file
python .../extract_text.py report.pdf --output extracted.txt
```

---

### 2. `extract_tables.py` — Extract tables to Excel / CSV / JSON
```bash
python <DEEPAGENTFORCE_ROOT>/src/services/skills/pdf-processing/scripts/extract_tables.py \
  <pdf_path> [--format FORMAT] [--output OUTPUT]
```

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pdf_path` | ✅ | — | Path to PDF file |
| `--format` | ❌ | `excel` | Output format: `excel` / `csv` / `json` |
| `--output` | ❌ | auto | Output file path |

**Examples:**
```bash
# Extract to Excel (default)
python .../extract_tables.py financial_report.pdf

# Extract to CSV
python .../extract_tables.py data.pdf --format csv

# Custom output path
python .../extract_tables.py data.pdf --output results/tables.xlsx
```

> **Note:** If no tables are found, the PDF may be image-based and requires OCR preprocessing.

---

### 3. `write_pdf.py` — Create a new PDF from text or markdown
```bash
python <DEEPAGENTFORCE_ROOT>/src/services/skills/pdf-processing/scripts/write_pdf.py \
  <output_path> [--title TITLE] [--content TEXT] [--input FILE] \
  [--font-size N] [--page-size A4|LETTER] [--author AUTHOR]
```

| Parameter | Required | Default | Description |
|---|---|---|---|
| `output_path` | ✅ | — | Output PDF file path |
| `--content` | ✅ or `--input` | — | Inline text / markdown content |
| `--input` | ✅ or `--content` | — | Path to a `.txt` or `.md` file |
| `--title` | ❌ | — | Title rendered at top of document |
| `--author` | ❌ | — | PDF author metadata |
| `--font-size` | ❌ | `12` | Base font size |
| `--page-size` | ❌ | `A4` | `A4` or `LETTER` |

**Markdown support:** `# Heading`, `## Subheading`, `- bullet` are rendered correctly.  
**CJK support:** Automatically detects and uses a system CJK font if available.

**Examples:**
```bash
# From inline text
python .../write_pdf.py report.pdf --title "Monthly Report" --content "Hello World"

# From markdown file
python .../write_pdf.py report.pdf --title "Report" --input content.md

# Custom font and page size
python .../write_pdf.py output.pdf --input draft.txt --font-size 14 --page-size LETTER
```

---

## Error Reference

| Error | Likely cause | Fix |
|---|---|---|
| `FileNotFoundError` | Wrong file path | Verify path with `ls` |
| `ImportError` | Missing Python package | See dependencies below |
| `No tables found` | Image-based PDF | OCR preprocessing required |
| `No text extracted` | Image-only PDF | OCR preprocessing required |
| CJK text garbled | No CJK font installed | `apt install fonts-wqy-zenhei` |

---

## Dependencies
```bash
# Python packages
pip install pdfplumber reportlab pandas openpyxl

# CJK font support (Ubuntu/Debian)
sudo apt-get install fonts-wqy-zenhei

# CJK font support (macOS)
brew install font-wqy-zenhei
```