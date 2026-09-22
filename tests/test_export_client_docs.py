"""Client document export: Markdown -> docx structure, and (with Chrome + npx) PDF / Mermaid."""
from __future__ import annotations

import importlib.util
import shutil
import sys
import zipfile
from pathlib import Path

import pytest

docx = pytest.importorskip("docx", reason="needs the export extra: uv pip install -e '.[export]'")
pytest.importorskip("markdown_it")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_client_docs.py"

spec = importlib.util.spec_from_file_location("export_client_docs", SCRIPT)
export = importlib.util.module_from_spec(spec)
sys.modules["export_client_docs"] = export
spec.loader.exec_module(export)  # type: ignore[union-attr]

HAS_CHROME = export.find_chrome() is not None
HAS_NPX = shutil.which("npx") is not None
needs_chrome = pytest.mark.skipif(not HAS_CHROME, reason="Chrome not found")
needs_mermaid = pytest.mark.skipif(not (HAS_CHROME and HAS_NPX), reason="npx or Chrome not found")

SAMPLE = """# 示例方案书

> 用途：说明示例。读者：客户。
> 版本：v0.1。

## 1. 摘要

常见问题一页备齐。普通段落，含 **粗体要点** 与 `code-id`，以及 [官方文档](https://example.com/doc)。

### 1.1 列表

- 第一项
- 第二项 **加粗**

1. 步骤一
2. 步骤二

中间段落。

1. 另一组第一步

## 2. 费用

| 项目 | 说明 |
|---|---|
| 首付 | 签约后支付 |
| 尾款 | 验收后支付 |

| A | B | C |
|---|---|---|
| 1 | 2 | 3 |
"""


def export_docx(tmp_path: Path, text: str = SAMPLE) -> Path:
    src = tmp_path / "示例.md"
    src.write_text(text, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    written = export.export_one(src, out, ("docx",))
    assert written == [out / "示例.docx"]
    return written[0]


def paragraphs(path: Path) -> list:
    return docx.Document(str(path)).paragraphs


def test_headings_become_title_and_heading_styles(tmp_path):
    doc = docx.Document(str(export_docx(tmp_path)))
    styled = [(p.style.name, p.text) for p in doc.paragraphs if p.style.name in ("Title", "Heading 1", "Heading 2")]
    assert styled == [
        ("Title", "示例方案书"),
        ("Heading 1", "1. 摘要"),
        ("Heading 2", "1.1 列表"),
        ("Heading 1", "2. 费用"),
    ]


def test_tables_are_real_bordered_word_tables(tmp_path):
    doc = docx.Document(str(export_docx(tmp_path)))
    assert len(doc.tables) == 2
    first = doc.tables[0]
    assert first.style.name == "Table Grid"
    assert first._tbl.tblPr.find(docx.oxml.ns.qn("w:tblBorders")) is not None
    assert [[c.text for c in row.cells] for row in first.rows] == [
        ["项目", "说明"], ["首付", "签约后支付"], ["尾款", "验收后支付"],
    ]
    header_runs = [r for c in first.rows[0].cells for r in c.paragraphs[0].runs]
    assert header_runs and all(r.bold for r in header_runs)
    assert len(doc.tables[1].columns) == 3


def test_lists_bold_code_and_quote(tmp_path):
    paras = paragraphs(export_docx(tmp_path))
    texts = [p.text for p in paras]
    assert "第一项" in texts and "第二项 加粗" in texts
    # ordered lists carry literal numbers, restarting for a separate list
    assert "1. 步骤一" in texts and "2. 步骤二" in texts and "1. 另一组第一步" in texts
    para = next(p for p in paras if "粗体要点" in p.text)
    bold = [r.text for r in para.runs if r.bold]
    assert bold == ["粗体要点"]
    mono = [r for r in para.runs if r.text == "code-id"]
    assert mono and mono[0]._r.rPr.rFonts.get(docx.oxml.ns.qn("w:ascii")) == export.MONO_FONT
    quote = next(p for p in paras if p.text.startswith("用途"))
    assert "版本：v0.1。" in quote.text  # the two quote lines stay together, separated by a line break


def test_links_show_text_and_keep_url(tmp_path):
    path = export_docx(tmp_path)
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
    assert "<w:hyperlink" in xml and "官方文档" in xml
    assert "https://example.com/doc" not in xml
    assert 'Target="https://example.com/doc"' in rels


def test_east_asian_font_on_every_run(tmp_path):
    path = export_docx(tmp_path)
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert xml.count("<w:r>") + xml.count("<w:r ") == xml.count(f'w:eastAsia="{export.EAST_ASIA_FONT}"')
    assert "w:eastAsiaTheme" not in xml


def test_no_source_file_names_in_output(tmp_path):
    path = export_docx(tmp_path)
    with zipfile.ZipFile(path) as z:
        text = "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
    assert ".md" not in text and "python-docx" not in text


def test_a4_page_with_2cm_margins(tmp_path):
    section = docx.Document(str(export_docx(tmp_path))).sections[0]
    assert round(section.page_width.cm, 1) == 21.0 and round(section.page_height.cm, 1) == 29.7
    assert round(section.left_margin.cm, 1) == 2.0


def test_unsupported_markup_fails_with_document_and_step(tmp_path):
    src = tmp_path / "坏文档.md"
    src.write_text("# 标题\n\n![图](x.png)\n", encoding="utf-8")
    with pytest.raises(export.ExportError, match=r"坏文档: build docx failed"):
        export.export_one(src, tmp_path, ("docx",))


def test_cli_rejects_unknown_document_and_format(capsys):
    assert export.main(["--docs", "不存在的文档", "--formats", "docx"]) == 1
    assert "不存在的文档" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        export.main(["--formats", "rtf"])


def test_every_client_document_exports_to_docx(tmp_path):
    for src in sorted((ROOT / "00-client").glob("*.md")):
        if "```mermaid" in src.read_text(encoding="utf-8"):
            continue  # needs npx; covered by the Mermaid test below
        out = export.export_one(src, tmp_path, ("docx",))[0]
        assert docx.Document(str(out)).paragraphs


@needs_chrome
def test_pdf_has_text_and_no_header_footer(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    src = tmp_path / "示例.md"
    src.write_text(SAMPLE, encoding="utf-8")
    pdf = export.export_one(src, tmp_path, ("pdf",))[0]
    text = "".join(page.extract_text() or "" for page in pypdf.PdfReader(str(pdf)).pages)
    import unicodedata
    text = unicodedata.normalize("NFKC", text)
    assert "示例方案书" in text and "签约后支付" in text
    assert ".md" not in text and "file://" not in text
    # 页 / 见 / 齐 must not come back as CJK radicals (font choice, see CSS in the script)
    assert "常见问题一页备齐" in text
    assert not [ch for ch in text if 0x2E80 <= ord(ch) <= 0x2EFF]


@needs_mermaid
def test_mermaid_rendered_as_image_in_docx(tmp_path):
    text = "# 图\n\n```mermaid\nflowchart TD\n    A[入口] --> B[接待]\n```\n\n图下文字。\n"
    path = export_docx(tmp_path, text)
    with zipfile.ZipFile(path) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        xml = z.read("word/document.xml").decode("utf-8")
    assert media
    assert "flowchart" not in xml and "图下文字" in xml


def test_render_mermaid_passes_private_npm_cache_to_npx(tmp_path, monkeypatch):
    """No Node needed: subprocess.run is faked and just records the env it was handed."""
    import types

    calls: list[dict] = []

    def fake_run(cmd, **kw):
        calls.append(dict(kw.get("env") or {}))
        Path(cmd[cmd.index("-o") + 1]).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.delenv("TROMOX_NPM_CACHE", raising=False)
    monkeypatch.setattr(export.subprocess, "run", fake_run)
    monkeypatch.setattr(export.shutil, "which", lambda *_a, **_k: "/usr/bin/npx")
    monkeypatch.setattr(export, "find_chrome", lambda: "/fake/chrome")

    data = export.render_mermaid("graph TD; A-->B", tmp_path, "d")
    assert data.startswith(b"\x89PNG")
    assert len(calls) == 1
    env = calls[0]
    assert Path(env["npm_config_cache"]).resolve().is_relative_to((ROOT / "scratch").resolve())
    assert env["PUPPETEER_SKIP_DOWNLOAD"] == "1"


# ---------------------------------------------------------------- --paths / --package

INTERNAL_DOC = "99-internal/zhang-baowen-brief.md"
PACKAGE_STEMS = [Path(rel).stem for group in export.PACKAGES["zhang"].values() for rel in group]


def tiny_png() -> bytes:
    """A valid 2x1 RGB PNG that stands in for mermaid-cli output."""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00" + b"\xff" * 6)) + chunk(b"IEND", b""))


@pytest.fixture
def stub_mermaid(monkeypatch):
    """方案书 has a Mermaid block; mermaid-cli itself is covered above, and one npx start-up is ~80 s."""
    monkeypatch.setattr(export, "render_mermaid", lambda body, workdir, name: tiny_png())


def source_headings(rel: str, prefix: str) -> list[str]:
    """Heading lines of a repo Markdown file outside code fences, with inline `*` / backticks removed."""
    found, fenced = [], False
    for line in (ROOT / rel).read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith(prefix):
            found.append(line[len(prefix):].strip().replace("*", "").replace("`", ""))
    return found


def test_paths_rejects_files_outside_the_repo_or_not_markdown(tmp_path, capsys):
    outside = tmp_path / "外部.md"
    outside.write_text("# 外部\n", encoding="utf-8")
    out = str(tmp_path / "out")
    assert export.main(["--paths", str(outside), "--formats", "docx", "--out-dir", out]) == 1
    assert "outside the repository" in capsys.readouterr().err
    assert export.main(["--paths", "../外部.md", "--formats", "docx", "--out-dir", out]) == 1
    assert "outside the repository" in capsys.readouterr().err
    assert export.main(["--paths", "pyproject.toml", "--formats", "docx", "--out-dir", out]) == 1
    assert "not a Markdown file" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()  # refused before anything is written


def test_paths_exports_an_internal_document_named_after_its_stem(tmp_path):
    assert export.main(["--paths", INTERNAL_DOC, "--formats", "docx", "--out-dir", str(tmp_path)]) == 0
    doc = docx.Document(str(tmp_path / "zhang-baowen-brief.docx"))
    assert [p.text for p in doc.paragraphs if p.style.name == "Title"] == source_headings(INTERNAL_DOC, "# ")
    assert [p.text for p in doc.paragraphs if p.style.name == "Heading 1"] == source_headings(INTERNAL_DOC, "## ")


def test_docs_paths_and_package_flags_are_validated(tmp_path, capsys):
    out = str(tmp_path)
    assert export.main(["--docs", "方案书", "--paths", "00-client/方案书.md", "--formats", "docx", "--out-dir", out]) == 1
    assert "collide" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        export.main(["--package", "zhang", "--date", "22/09/2026", "--out-dir", out])
    with pytest.raises(SystemExit):
        export.main(["--package", "zhang", "--docs", "方案书", "--out-dir", out])
    with pytest.raises(SystemExit):
        export.main(["--package", "nobody", "--out-dir", out])
    assert not list(tmp_path.iterdir())


@pytest.mark.usefixtures("stub_mermaid")
def test_package_zhang_docx_only_bundles_six_documents_and_recreates_the_folder(tmp_path):
    argv = ["--package", "zhang", "--date", "2026-09-22", "--formats", "docx", "--out-dir", str(tmp_path)]
    assert export.main(argv) == 0
    folder = tmp_path / "zhang-2026-09-22"
    expected = sorted(f"{s}.docx" for s in PACKAGE_STEMS)
    assert len(expected) == 6 and sorted(p.name for p in folder.iterdir()) == expected
    with zipfile.ZipFile(tmp_path / "zhang-2026-09-22.zip") as z:
        infos = z.infolist()
    assert sorted(i.filename for i in infos) == [f"zhang-2026-09-22/{n}" for n in expected]
    assert not any(i.is_dir() for i in infos)
    assert all(i.flag_bits & 0x800 for i in infos if not i.filename.isascii())  # 方案书 etc. stored as UTF-8
    (folder / "stale.txt").write_text("x", encoding="utf-8")
    assert export.main(argv) == 0
    assert not (folder / "stale.txt").exists()


@needs_chrome
@pytest.mark.usefixtures("stub_mermaid")
def test_package_zhang_writes_twelve_files_and_the_zip(tmp_path):
    assert export.main(["--package", "zhang", "--date", "2026-09-22", "--out-dir", str(tmp_path)]) == 0
    expected = sorted(f"{s}.{ext}" for s in PACKAGE_STEMS for ext in ("docx", "pdf"))
    assert len(expected) == 12
    assert sorted(p.name for p in (tmp_path / "zhang-2026-09-22").iterdir()) == expected
    with zipfile.ZipFile(tmp_path / "zhang-2026-09-22.zip") as z:
        assert sorted(z.namelist()) == [f"zhang-2026-09-22/{n}" for n in expected]
        assert z.testzip() is None
