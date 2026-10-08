"""Build submission documents: Markdown -> DOCX (pandoc) -> PDF (LibreOffice),
the presentation (python-pptx) and the D2 register workbook (openpyxl).

    python tools/build_docs.py            # all
    python tools/build_docs.py --no-pdf   # skip PDF conversion
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BUILD = DOCS / "build"


def md_to_docx(md: Path, ref: Path | None) -> Path:
    out = BUILD / (md.stem + ".docx")
    cmd = ["pandoc", str(md), "-o", str(out), "--resource-path", f"{DOCS}:{ROOT}", "--toc" if md.stem.startswith("D6") else "--standalone"]
    if md.stem.startswith("D6"):
        cmd += ["--toc-depth=2", "--number-sections"]
    if ref and ref.exists():
        cmd += ["--reference-doc", str(ref)]
    subprocess.run(cmd, check=True, cwd=DOCS)
    return out


def md_to_pdf(md: Path) -> Path:
    """Markdown -> self-contained HTML (MathML equations) -> PDF with Chromium."""
    html = BUILD / (md.stem + ".html")
    cmd = ["pandoc", str(md), "-o", str(html), "--standalone", "--embed-resources", "--mathml",
           "--resource-path", f"{DOCS}:{ROOT}", "--css", str(ROOT / "tools" / "doc.css"),
           "--metadata", "lang=en"]
    if md.stem.startswith("D6"):
        cmd += ["--toc", "--toc-depth=2", "--number-sections"]
    subprocess.run(cmd, check=True, cwd=DOCS)
    pdf = BUILD / (md.stem + ".pdf")
    subprocess.run(["node", str(ROOT / "tools" / "html2pdf.js"), str(html), str(pdf)], check=True)
    html.unlink()
    return pdf


def make_reference_docx() -> Path:
    """A reference document with readable styles (fonts, table style)."""
    ref = BUILD / "_reference.docx"
    subprocess.run(["pandoc", "-o", str(ref), "--print-default-data-file", "reference.docx"], check=True)
    from docx import Document
    from docx.shared import Pt, RGBColor
    d = Document(str(ref))
    st = d.styles
    for name, size, bold, color in [("Normal", 10.5, False, None), ("Title", 22, True, (0x1C, 0x5C, 0xAB)),
                                    ("Heading 1", 15, True, (0x10, 0x42, 0x81)), ("Heading 2", 12.5, True, (0x1C, 0x5C, 0xAB)),
                                    ("Heading 3", 11, True, (0x25, 0x6A, 0xBF))]:
        try:
            s = st[name]
        except KeyError:
            continue
        s.font.name = "Calibri"
        s.font.size = Pt(size)
        s.font.bold = bold
        if color:
            s.font.color.rgb = RGBColor(*color)
    d.save(str(ref))
    return ref


def style_tables(docx: Path):
    """Apply a grid table style, header shading and compact fonts to all tables."""
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt
    d = Document(str(docx))
    for t in d.tables:
        tblPr = t._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{edge}")
            e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "BDBBB3")
            borders.append(e)
        tblPr.append(borders)
        for i, row in enumerate(t.rows):
            for cell in row.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(8.5)
                        if i == 0:
                            r.font.bold = True
                if i == 0:
                    tcPr = cell._tc.get_or_add_tcPr()
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), "DCE8F7")
                    tcPr.append(shd)
    # images: limit width to page
    from docx.shared import Cm
    for shape in d.inline_shapes:
        if shape.width > Cm(16.5):
            ratio = Cm(16.5) / shape.width
            shape.width = int(shape.width * ratio)
            shape.height = int(shape.height * ratio)
    d.save(str(docx))


def register_xlsx():
    """D2 assumption/QA tables -> Excel workbook (one sheet per table)."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    md = (DOCS / "D2_Data_and_Assumption_Register.md").read_text()
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    def sheet_name(text):
        """Readable Excel sheet name (<= 31 chars): no table number, no
        parenthetical, no section number, cut at a word boundary."""
        t = re.sub(r"^Table [\d.]+ - ", "", text.strip("*# ").strip())
        t = re.sub(r"\([^)]*\)", "", t)
        t = re.sub(r"^[\d.]+\s+", "", t)
        t = re.sub(r"[^A-Za-z0-9 \-]", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        while len(t) > 31 and " " in t:
            t = t.rsplit(" ", 1)[0]
        return t[:31] or "Sheet"
    section = "Sheet"
    caption = None
    lines = md.splitlines()
    i = 0
    used = set()
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#"):
            section = sheet_name(ln)
            caption = None
        elif re.match(r"^\*[^*].*[^*]\*$", ln.strip()):
            caption = sheet_name(ln)
        elif ln.strip() and not ln.startswith("|"):
            caption = None
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[-| :]+\|$", lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[-| :]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            base_name = caption or section
            name = base_name
            k = 2
            while name in used:
                name = f"{base_name[:27]} {k}"; k += 1
            caption = None
            used.add(name)
            ws = wb.create_sheet(name)
            for r in rows:
                ws.append([re.sub(r"\*\*|`", "", c) for c in r])
            for c in ws[1]:
                c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="DCE8F7")
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(60, max(10, max(len(str(c.value or "")) for c in col) * 0.9))
                for c in col:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
            continue
        i += 1
    out = BUILD / "D2_Data_and_Assumption_Register.xlsx"
    wb.save(out)
    return out


def team_substitutions() -> dict:
    """'[Member n]' -> name from config/team.yaml (only for names filled in)."""
    import yaml
    t = yaml.safe_load((ROOT / "config" / "team.yaml").read_text())
    subs = {}
    for i, m in enumerate(t.get("members", []), 1):
        if m.get("name") and m["name"] != f"[Member {i}]":
            subs[f"[Member {i}]"] = m["name"]
    names = [m["name"] for m in t.get("members", [])]
    if subs:
        subs["[Member 1-5]"] = ", ".join(names)
    return subs


def with_names(md: Path, subs: dict) -> Path:
    """Temporary copy of a Markdown source with team names substituted
    (kept next to the source so relative figure paths still resolve)."""
    if not subs:
        return md
    txt = md.read_text()
    for k, v in subs.items():
        txt = txt.replace(k, v)
    tmp = md.with_name("_build_" + md.name)
    tmp.write_text(txt)
    return tmp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    ref = make_reference_docx()
    subs = team_substitutions()
    for src in sorted(DOCS.glob("D*.md")) + sorted(DOCS.glob("Appendix*.md")):
        md = with_names(src, subs)
        docx = md_to_docx(md, ref)
        if md != src:
            docx = docx.rename(BUILD / (src.stem + ".docx"))
        style_tables(docx)
        print("docx", docx.name)
        if not a.no_pdf and shutil.which("node"):
            pdf = md_to_pdf(md)
            if md != src:
                pdf = pdf.rename(BUILD / (src.stem + ".pdf"))
            print("pdf ", pdf.name)
        if md != src:
            md.unlink()
    print("xlsx", register_xlsx().name)
    try:
        from make_presentation import build as build_ppt  # noqa
        print("pptx", build_ppt())
    except ImportError:
        pass
    (BUILD / "_reference.docx").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
