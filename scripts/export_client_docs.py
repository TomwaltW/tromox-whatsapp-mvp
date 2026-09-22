#!/usr/bin/env python3
"""Export Markdown documents (00-client/*.md by default) to an editable Word file and a PDF.

    python scripts/export_client_docs.py                       # all 00-client/*.md, docx + pdf
    python scripts/export_client_docs.py --docs 方案书 报价单
    python scripts/export_client_docs.py --formats docx         # docx | pdf | docx,pdf
    python scripts/export_client_docs.py --out-dir dist         # default; dist/ is gitignored
    python scripts/export_client_docs.py --paths 99-internal/zhang-baowen-brief.md 07-project/meeting-prep.md
    python scripts/export_client_docs.py --package zhang --date 2026-09-22
        # -> dist/zhang-2026-09-22/ (the PACKAGES["zhang"] documents, docx + pdf) + dist/zhang-2026-09-22.zip

One markdown-it token stream feeds both outputs: python-docx builds the .docx, the same
tokens rendered to HTML are printed to PDF by headless Chrome. ```mermaid blocks are
rendered to PNG with mermaid-cli (npx + local Chrome, same setup as check_mermaid.py) and
embedded in both. The output contains only the source content: no cover, no header or
footer, no file names. Any failure exits 1 and names the document and the step.
Needs the `export` extra: uv pip install --python .venv/bin/python -e ".[export]"
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.text.run import Run
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
CLIENT_DIR = ROOT / "00-client"
FORMATS = ("docx", "pdf")
# --package NAME exports a fixed bundle into <out-dir>/<NAME>-<date>/ and zips it next to it.
# "zhang" is what 张宝文 gets before 9/25: three internal notes (exported verbatim: repo paths,
# review markers and S-xx source ids stay in; no literal marker here or collect_open_questions.py
# would index this comment) plus the three client documents he forwards.
PACKAGES: dict[str, dict[str, tuple[str, ...]]] = {
    "zhang": {
        "internal": (
            "99-internal/zhang-baowen-brief.md",
            "99-internal/zhang-baowen-changelog-2026-09-22.md",
            "07-project/meeting-prep.md",
        ),
        "client": (
            "00-client/方案书.md",
            "00-client/报价单.md",
            "00-client/客户需提供清单.md",
        ),
    },
}
CHROME_CANDIDATES = (
    os.environ.get("PUPPETEER_EXECUTABLE_PATH", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
)
EAST_ASIA_FONT = "微软雅黑"
LATIN_FONT = "Calibri"
MONO_FONT = "Consolas"
# H1 is the document title; H2/H3 are the chapter levels.
HEADING_STYLES = {1: "Title", 2: "Heading 1", 3: "Heading 2", 4: "Heading 3", 5: "Heading 3", 6: "Heading 3"}
PAGE_WIDTH_CM, PAGE_HEIGHT_CM, MARGIN_CM = 21.0, 29.7, 2.0
MAX_IMAGE_HEIGHT_CM = 22.0

# Hiragino Sans GB first: PingFang SC (and Microsoft YaHei) glyphs for 页 见 齐 风 长 车 门…
# come out of Chrome's PDF text layer as CJK radicals (U+2E80 block, e.g. ⻚ ⻅ ⻬), which
# NFKC does not fold back, so copy / search in the PDF would miss them. Hiragino keeps the
# proper code points; the rest of the stack applies on machines without it.
CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: "Hiragino Sans GB", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
       font-size: 10.5pt; line-height: 1.6; color: #222; }
h1 { font-size: 20pt; margin: 0 0 12pt; }
h2 { font-size: 15pt; margin: 18pt 0 8pt; border-bottom: 1px solid #ccc; padding-bottom: 3pt; }
h3 { font-size: 12.5pt; margin: 14pt 0 6pt; }
h4, h5, h6 { font-size: 11pt; margin: 12pt 0 4pt; }
h1, h2, h3, h4 { page-break-after: avoid; }
p { margin: 4pt 0; }
ul, ol { margin: 4pt 0; padding-left: 22pt; }
blockquote { margin: 6pt 0; padding: 2pt 10pt; border-left: 3px solid #bbb; color: #555; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 9.5pt; }
th, td { border: 1px solid #888; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { font-weight: bold; background: #f0f0f0; }
tr { page-break-inside: avoid; }
code { font-family: Menlo, Consolas, monospace; font-size: 9pt; background: #f4f4f4; padding: 0 2pt; }
pre { background: #f4f4f4; padding: 6pt; white-space: pre-wrap; }
img.diagram { display: block; max-width: 100%; max-height: 24cm; margin: 8pt auto; }
a { color: #1a5fb4; }
"""


class ExportError(Exception):
    """A failure attributed to one document and one step."""


def markdown() -> MarkdownIt:
    # breaks=True: a single newline inside a paragraph stays a line break (the stacked
    # "> 用途 / > 版本" lines at the top of every document).
    return MarkdownIt("commonmark", {"breaks": True}).enable("table")


# ---------------------------------------------------------------- mermaid


def find_chrome() -> str | None:
    return next((c for c in CHROME_CANDIDATES if c and Path(c).exists()), None)


def render_mermaid(body: str, workdir: Path, name: str) -> bytes:
    """Render one mermaid block to PNG bytes (white background, 2x scale)."""
    chrome = find_chrome()
    if not shutil.which("npx") or not chrome:
        raise RuntimeError("npx or Chrome not found; cannot render Mermaid")
    env = {**os.environ, "PUPPETEER_SKIP_DOWNLOAD": "1", "PUPPETEER_SKIP_CHROMIUM_DOWNLOAD": "1"}
    config = workdir / "puppeteer.json"
    config.write_text(json.dumps({"executablePath": chrome, "args": ["--no-sandbox"]}), encoding="utf-8")
    src, out = workdir / f"{name}.mmd", workdir / f"{name}.png"
    src.write_text(body, encoding="utf-8")
    proc = subprocess.run(
        ["npx", "-y", "@mermaid-js/mermaid-cli@11", "-q", "-p", str(config),
         "-i", str(src), "-o", str(out), "-b", "white", "-s", "2"],
        capture_output=True, text=True, env=env, timeout=300,
    )
    if proc.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        detail = " | ".join((proc.stderr or proc.stdout).strip().splitlines()[:6])
        raise RuntimeError(f"mermaid-cli exit {proc.returncode}: {detail}")
    return out.read_bytes()


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


def render_diagrams(tokens: list, workdir: Path) -> list[bytes]:
    """PNG bytes for every ```mermaid fence, in document order."""
    return [render_mermaid(t.content, workdir, f"diagram_{i}")
            for i, t in enumerate(t for t in tokens if t.type == "fence" and is_mermaid(t))]


def is_mermaid(token) -> bool:
    return token.info.strip().split(" ")[0].lower() == "mermaid"


# ---------------------------------------------------------------- docx


def set_run_fonts(rpr_parent, mono: bool = False) -> None:
    """Explicit Latin + East Asian fonts on a run or style (theme fonts removed)."""
    rpr = rpr_parent.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(attr), None)
    latin = MONO_FONT if mono else LATIN_FONT
    for attr, value in (("w:ascii", latin), ("w:hAnsi", latin), ("w:cs", latin), ("w:eastAsia", EAST_ASIA_FONT)):
        fonts.set(qn(attr), value)


def new_document():
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(PAGE_WIDTH_CM), Cm(PAGE_HEIGHT_CM)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Cm(MARGIN_CM))
    for name in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3", "List Bullet", "Table Grid"):
        set_run_fonts(doc.styles[name].element)
    doc.styles["Normal"].font.size = Pt(10.5)
    props = doc.core_properties
    props.author = props.last_modified_by = props.comments = ""
    return doc


def add_hyperlink(paragraph, url: str, text: str, bold: bool, italic: bool):
    rel_id = paragraph.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rel_id)
    paragraph._p.append(link)
    r = OxmlElement("w:r")
    link.append(r)
    run = Run(r, paragraph)
    run.text = text
    run.bold, run.italic, run.underline = bold or None, italic or None, True
    run.font.color.rgb = RGBColor(0x1A, 0x5F, 0xB4)
    set_run_fonts(run._r)
    return run


def add_inline(paragraph, inline, bold: bool = False) -> None:
    """Append the children of an `inline` token to a python-docx paragraph."""
    strong = em = 0
    link_url: str | None = None
    link_text: list[str] = []
    for child in inline.children or []:
        kind = child.type
        if kind == "strong_open":
            strong += 1
        elif kind == "strong_close":
            strong -= 1
        elif kind == "em_open":
            em += 1
        elif kind == "em_close":
            em -= 1
        elif kind == "link_open":
            link_url, link_text = child.attrGet("href") or "", []
        elif kind == "link_close":
            add_hyperlink(paragraph, link_url or "", "".join(link_text), bold or strong > 0, em > 0)
            link_url = None
        elif kind in ("text", "code_inline") and link_url is not None:
            link_text.append(child.content)
        elif kind in ("text", "code_inline"):
            run = paragraph.add_run(child.content)
            run.bold = True if (bold or strong > 0) else None
            run.italic = True if em > 0 else None
            set_run_fonts(run._r, mono=kind == "code_inline")
        elif kind in ("softbreak", "hardbreak"):
            if link_url is not None:
                link_text.append(" ")
            else:
                run = paragraph.add_run()
                run.add_break(WD_BREAK.LINE)
                set_run_fonts(run._r)
        elif kind == "image":
            raise ValueError(f"inline image not supported: {child.attrGet('src')}")
        else:
            raise ValueError(f"unsupported inline token {kind!r} ({child.content[:40]!r})")


def build_docx(tokens: list, diagrams: list[bytes], out: Path) -> None:
    doc = new_document()
    lists: list[list] = []        # stack of [kind, next_number]
    item_first_para: list[bool] = []
    quote_depth = 0
    diagram_iter = iter(diagrams)
    content_width = PAGE_WIDTH_CM - 2 * MARGIN_CM
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        kind = tok.type
        if kind == "heading_open":
            level = int(tok.tag[1])
            para = doc.add_paragraph(style=HEADING_STYLES[level])
            add_inline(para, tokens[i + 1])
            i += 3
            continue
        if kind == "paragraph_open":
            inline = tokens[i + 1]
            if item_first_para and item_first_para[-1]:
                item_first_para[-1] = False
                list_kind = lists[-1]
                depth = len(lists) - 1
                if list_kind[0] == "bullet":
                    para = doc.add_paragraph(style="List Bullet")
                    para.paragraph_format.left_indent = Cm(0.63 * (depth + 1))
                else:
                    # Literal "N. " prefix: Word's shared List Number numbering would
                    # continue counting across separate lists.
                    para = doc.add_paragraph()
                    para.paragraph_format.left_indent = Cm(0.63 * (depth + 1))
                    para.paragraph_format.first_line_indent = Cm(-0.63)
                    prefix = para.add_run(f"{list_kind[1]}. ")
                    set_run_fonts(prefix._r)
                    list_kind[1] += 1
            else:
                para = doc.add_paragraph()
                indent = 0.63 * len(lists) + (0.5 if quote_depth else 0)
                if indent:
                    para.paragraph_format.left_indent = Cm(indent)
            add_inline(para, inline)
            if quote_depth:
                for run in para.runs:
                    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            i += 3
            continue
        if kind == "bullet_list_open":
            lists.append(["bullet", 0])
        elif kind == "ordered_list_open":
            lists.append(["ordered", int(tok.attrGet("start") or 1)])
        elif kind in ("bullet_list_close", "ordered_list_close"):
            lists.pop()
        elif kind == "list_item_open":
            item_first_para.append(True)
        elif kind == "list_item_close":
            item_first_para.pop()
        elif kind == "blockquote_open":
            quote_depth += 1
        elif kind == "blockquote_close":
            quote_depth -= 1
        elif kind == "table_open":
            i = add_table(doc, tokens, i)
            continue
        elif kind == "fence" and is_mermaid(tok):
            data = next(diagram_iter)
            w_px, h_px = png_size(data)
            width = min(content_width, MAX_IMAGE_HEIGHT_CM * w_px / h_px)
            doc.add_picture(io.BytesIO(data), width=Cm(width))
            doc.paragraphs[-1].alignment = 1  # center
        elif kind in ("fence", "code_block"):
            para = doc.add_paragraph()
            for n, line in enumerate(tok.content.rstrip("\n").split("\n")):
                if n:
                    brk = para.add_run()
                    brk.add_break(WD_BREAK.LINE)
                    set_run_fonts(brk._r, mono=True)
                set_run_fonts(para.add_run(line)._r, mono=True)
        elif kind == "hr":
            doc.add_paragraph()
        else:
            raise ValueError(f"unsupported block token {kind!r} at line {(tok.map or [0])[0] + 1}")
        i += 1
    doc.save(str(out))


def add_table(doc, tokens: list, start: int) -> int:
    """Consume table_open..table_close; return the index after it."""
    rows: list[list[tuple[bool, object]]] = []
    i = start + 1
    while tokens[i].type != "table_close":
        kind = tokens[i].type
        if kind == "tr_open":
            rows.append([])
        elif kind in ("th_open", "td_open"):
            rows[-1].append((kind == "th_open", tokens[i + 1]))
            i += 2
        i += 1
    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=cols)
    table.style = doc.styles["Table Grid"]
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Borders also set on the table itself: Pages / Quick Look ignore the style's borders.
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        line = OxmlElement(f"w:{edge}")
        for attr, value in (("w:val", "single"), ("w:sz", "4"), ("w:space", "0"), ("w:color", "888888")):
            line.set(qn(attr), value)
        borders.append(line)
    table._tbl.tblPr.append(borders)
    for r, row in enumerate(rows):
        for c, (is_header, inline) in enumerate(row):
            cell = table.cell(r, c)
            cell.paragraphs[0].paragraph_format.space_after = Pt(2)
            add_inline(cell.paragraphs[0], inline, bold=is_header)
            if is_header:
                shade = OxmlElement("w:shd")
                shade.set(qn("w:val"), "clear")
                shade.set(qn("w:color"), "auto")
                shade.set(qn("w:fill"), "F0F0F0")
                cell._tc.get_or_add_tcPr().append(shade)
    if rows and rows[0] and rows[0][0][0]:
        # repeat the header row on every page
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:tblHeader"))
    doc.add_paragraph()  # keep consecutive tables / following text apart
    return i + 1


# ---------------------------------------------------------------- pdf


def build_html(md: MarkdownIt, tokens: list, diagrams: list[bytes], title: str) -> str:
    uris = iter(f"data:image/png;base64,{base64.b64encode(d).decode()}" for d in diagrams)
    for tok in tokens:
        if tok.type == "fence" and is_mermaid(tok):
            tok.type, tok.content = "html_block", f'<img class="diagram" src="{next(uris)}" alt="">\n'
    md.options["html"] = True  # only our own <img> blocks; the sources contain no raw HTML
    body = md.renderer.render(tokens, md.options, {})
    return (f'<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head>\n<body>\n{body}</body></html>\n")


def pdf_complete(path: Path) -> bool:
    try:
        return path.stat().st_size > 0 and b"%%EOF" in path.read_bytes()[-1024:]
    except OSError:
        return False


def print_pdf(html_path: Path, out: Path, workdir: Path, timeout: float = 180) -> None:
    """Headless Chrome print, without the default header/footer (it would print the file URL).

    No --user-data-dir: with a fresh profile, Chrome on macOS writes the PDF and then never
    exits. As a second guard, a Chrome still running a few seconds after the PDF is complete
    is terminated.
    """
    chrome = find_chrome()
    if not chrome:
        raise RuntimeError("Chrome not found; cannot print PDF")
    if out.exists():
        out.unlink()
    log = workdir / "chrome.log"
    with log.open("w") as sink:
        proc = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--no-first-run",
             f"--print-to-pdf={out}", html_path.as_uri()],
            stdout=sink, stderr=subprocess.STDOUT,
        )
        deadline, done_at = time.monotonic() + timeout, None
        while proc.poll() is None:
            now = time.monotonic()
            if done_at is None and pdf_complete(out):
                done_at = now
            if (done_at is not None and now - done_at > 5) or now > deadline:
                proc.terminate()
                try:
                    proc.wait(10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                break
            time.sleep(0.2)
    if not pdf_complete(out):
        tail = " | ".join(log.read_text(errors="replace").strip().splitlines()[-4:])
        raise RuntimeError(f"Chrome exit {proc.returncode}, no complete PDF: {tail}")


# ---------------------------------------------------------------- driver


def document_title(tokens: list, fallback: str) -> str:
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.tag == "h1":
            return tokens[i + 1].content
    return fallback


def export_one(src: Path, out_dir: Path, formats: tuple[str, ...]) -> list[Path]:
    name = src.stem
    written: list[Path] = []

    def step(label: str, func, *args):
        try:
            return func(*args)
        except Exception as exc:  # noqa: BLE001 - every failure is reported with doc + step
            raise ExportError(f"{name}: {label} failed: {exc}") from exc

    md = markdown()
    tokens = step("parse markdown", lambda: md.parse(src.read_text(encoding="utf-8")))
    with tempfile.TemporaryDirectory(prefix="export-") as tmp:
        workdir = Path(tmp)
        diagrams = step("render mermaid", render_diagrams, tokens, workdir)
        if "docx" in formats:
            out = out_dir / f"{name}.docx"
            step("build docx", build_docx, tokens, diagrams, out)
            written.append(out)
        if "pdf" in formats:
            html_path = workdir / "page.html"
            page = step("build html", build_html, md, tokens, diagrams, document_title(tokens, name))
            html_path.write_text(page, encoding="utf-8")
            out = out_dir / f"{name}.pdf"
            step("print pdf (Chrome)", print_pdf, html_path, out, workdir)
            written.append(out)
    return written


def parse_formats(value: str) -> tuple[str, ...]:
    chosen = tuple(dict.fromkeys(v.strip().lower() for v in value.split(",") if v.strip()))
    bad = [v for v in chosen if v not in FORMATS]
    if bad or not chosen:
        raise argparse.ArgumentTypeError(f"formats must be docx, pdf or docx,pdf (got {value!r})")
    return chosen


def parse_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD (got {value!r})") from None


def resolve_paths(values: list[str]) -> list[Path]:
    """Markdown files given as repo-relative (or absolute) paths; anything outside the repository is refused."""
    sources: list[Path] = []
    for value in values:
        path = Path(value)
        path = (path if path.is_absolute() else ROOT / path).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"{value}: outside the repository ({ROOT})")
        if path.suffix != ".md" or not path.is_file():
            raise ValueError(f"{value}: not a Markdown file")
        sources.append(path)
    return sources


def select_sources(args: argparse.Namespace) -> list[Path]:
    """The files to export: a package, --docs and/or --paths, else every 00-client/*.md. Output names must not clash."""
    if args.package:
        return resolve_paths([rel for group in PACKAGES[args.package].values() for rel in group])
    if not args.docs and not args.paths:
        return sorted(CLIENT_DIR.glob("*.md"))
    sources: list[Path] = []
    if args.docs:
        docs = [CLIENT_DIR / f"{d.removesuffix('.md')}.md" for d in args.docs]
        missing = [s.stem for s in docs if not s.exists()]
        if missing:
            raise ValueError(f"no such client document: {', '.join(missing)}")
        sources += docs
    if args.paths:
        sources += resolve_paths(args.paths)
    stems = [s.stem for s in sources]
    clashes = sorted({s for s in stems if stems.count(s) > 1})
    if clashes:
        raise ValueError(f"output names collide: {', '.join(clashes)}")
    return sources


def write_zip(files: list[Path], zip_path: Path, folder: str) -> None:
    """One top-level folder, no directory entries; zipfile stores non-ASCII names as UTF-8 and flags them."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, arcname=f"{folder}/{f.name}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Export Markdown to .docx and .pdf: 00-client/*.md by default, any repository "
                    "file with --paths, or a predefined bundle with --package.")
    ap.add_argument("--docs", nargs="+", metavar="NAME", help="client document names without .md (default: all of 00-client/)")
    ap.add_argument("--paths", nargs="+", metavar="PATH",
                    help="repo-relative .md paths from any directory, e.g. 99-internal/zhang-baowen-brief.md; "
                         "the output is named after the file stem; may be combined with --docs")
    ap.add_argument("--package", choices=sorted(PACKAGES),
                    help="export a predefined bundle into <out-dir>/<package>-<date>/ (recreated on every run) "
                         "and zip it as <out-dir>/<package>-<date>.zip; cannot be combined with --docs / --paths")
    ap.add_argument("--date", type=parse_date, default=date.today().isoformat(), metavar="YYYY-MM-DD",
                    help="date in the package folder and zip name (default: today)")
    ap.add_argument("--formats", type=parse_formats, default=FORMATS, help="docx | pdf | docx,pdf")
    ap.add_argument("--out-dir", default="dist", help="output directory, relative to the repo root (default dist)")
    args = ap.parse_args(argv)
    if args.package and (args.docs or args.paths):
        ap.error("--package cannot be combined with --docs or --paths")

    try:
        sources = select_sources(args)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    out_dir = Path(args.out_dir)
    out_dir = out_dir if out_dir.is_absolute() else ROOT / out_dir
    folder = f"{args.package}-{args.date}" if args.package else None
    if folder:
        out_dir = out_dir / folder
        if out_dir.exists():
            shutil.rmtree(out_dir)  # the folder is exactly this run's package, nothing stale
    out_dir.mkdir(parents=True, exist_ok=True)

    failed = 0
    written_all: list[Path] = []
    for src in sources:
        try:
            written = export_one(src, out_dir, args.formats)
        except ExportError as exc:
            failed += 1
            print(f"FAIL {exc}", file=sys.stderr)
            continue
        written_all += written
        print(f"ok   {src.stem}: " + ", ".join(p.name for p in written))
    print(f"{len(sources)} document(s), {failed} failed")
    if failed:
        return 1
    if folder:
        zip_path = out_dir.parent / f"{folder}.zip"
        write_zip(written_all, zip_path, folder)
        print(f"zip  {zip_path.name}: {len(written_all)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
