#!/usr/bin/env python3
"""
Write / create PDF files from text, markdown, or structured content
Part of the pdf-processing Agent Skill
"""

import argparse
import sys
import json
from pathlib import Path


def write_pdf(output_path: str, content: str = None, input_file: str = None,
              title: str = "", author: str = "", font_size: int = 12,
              page_size: str = "A4", encoding: str = "utf-8") -> int:
    """Create a PDF from plain text or a text file."""
    try:
        from reportlab.lib.pagesizes import A4, LETTER
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import reportlab.lib.colors as colors
    except ImportError as e:
        print(f"❌ Error: Missing dependency: {e}")
        print("   Install with: pip install reportlab")
        return 1

    try:
        # ── Resolve content ──────────────────────────────────────────────────
        if input_file:
            src = Path(input_file)
            if not src.exists():
                print(f"❌ Error: Input file not found: {input_file}")
                return 1
            content = src.read_text(encoding=encoding)

        if not content:
            print("❌ Error: No content provided. Use --content or --input.")
            return 1

        # ── Page size ────────────────────────────────────────────────────────
        page = A4 if page_size.upper() == "A4" else LETTER

        # ── Font: try to register a CJK-capable font, fall back to Helvetica ─
        _register_cjk_font()

        # ── Build document ───────────────────────────────────────────────────
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=page,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=25 * mm,
            bottomMargin=20 * mm,
            title=title,
            author=author,
        )

        styles = getSampleStyleSheet()
        body_font = "CJKFont" if _cjk_available() else "Helvetica"

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontName=body_font,
            fontSize=font_size + 6,
            spaceAfter=12,
            textColor=colors.HexColor("#1a1a1a"),
        )
        normal_style = ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=font_size,
            leading=font_size * 1.6,
            spaceAfter=6,
        )
        h1_style = ParagraphStyle(
            "H1",
            parent=styles["Heading1"],
            fontName=body_font,
            fontSize=font_size + 4,
            spaceBefore=10,
            spaceAfter=6,
        )

        story = []

        # Title page element
        if title:
            story.append(Paragraph(_escape(title), title_style))
            story.append(Spacer(1, 6 * mm))

        # Render content line by line
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                story.append(Spacer(1, 3 * mm))
            elif stripped.startswith("# "):
                story.append(Paragraph(_escape(stripped[2:]), h1_style))
            elif stripped.startswith("## "):
                h2 = ParagraphStyle("H2", parent=h1_style, fontSize=font_size + 2)
                story.append(Paragraph(_escape(stripped[3:]), h2))
            elif stripped.startswith("- ") or stripped.startswith("* "):
                bullet_style = ParagraphStyle(
                    "Bullet", parent=normal_style,
                    leftIndent=12, bulletIndent=4
                )
                story.append(Paragraph(f"• {_escape(stripped[2:])}", bullet_style))
            else:
                story.append(Paragraph(_escape(stripped), normal_style))

        doc.build(story)

        size_kb = output_file.stat().st_size // 1024
        print(f"✅ PDF created: {output_file}  ({size_kb} KB, {_count_pages(content)} pages est.)")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


# ── Helpers ──────────────────────────────────────────────────────────────────

def _escape(text: str) -> str:
    """Escape special ReportLab XML characters."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def _cjk_available() -> bool:
    from reportlab.pdfbase import pdfmetrics
    return "CJKFont" in pdfmetrics.getRegisteredFontNames()


def _register_cjk_font():
    """Try to register a system CJK font for Chinese/Japanese/Korean support."""
    candidates = [
        # Linux
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Windows
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for path in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont("CJKFont", path))
                return
            except Exception:
                continue


def _count_pages(content: str, chars_per_page: int = 1800) -> int:
    return max(1, len(content) // chars_per_page)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Create a PDF from text or a text/markdown file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From inline text
  %(prog)s report.pdf --title "Monthly Report" --content "Hello World"

  # From a markdown / plain-text file
  %(prog)s report.pdf --title "Report" --input content.md

  # Custom font size and page size
  %(prog)s output.pdf --input draft.txt --font-size 14 --page-size LETTER
        """
    )

    parser.add_argument("output_path", help="Output PDF file path")
    parser.add_argument("--title",     default="",    help="Document title shown at top")
    parser.add_argument("--author",    default="",    help="PDF author metadata")
    parser.add_argument("--content",   default=None,  help="Inline text content")
    parser.add_argument("--input",     default=None,  help="Path to input text/markdown file")
    parser.add_argument("--font-size", type=int, default=12, help="Base font size (default: 12)")
    parser.add_argument("--page-size", choices=["A4", "LETTER"], default="A4",
                        help="Page size (default: A4)")
    parser.add_argument("--encoding",  default="utf-8", help="Input file encoding (default: utf-8)")

    args = parser.parse_args()

    sys.exit(write_pdf(
        args.output_path,
        content=args.content,
        input_file=args.input,
        title=args.title,
        author=args.author,
        font_size=args.font_size,
        page_size=args.page_size,
        encoding=args.encoding,
    ))


if __name__ == "__main__":
    main()