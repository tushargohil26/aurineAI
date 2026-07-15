import base64
import html
import json
import re
import struct
import textwrap
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .config import get_settings


ARTIFACT_ROOT = Path("./generated_artifacts")


def safe_name(text: str, fallback: str = "artifact") -> str:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    name = "-".join(words[:7]).strip("-")
    return name[:70] or fallback


def artifacts_root() -> Path:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return ARTIFACT_ROOT


def classify_artifact(prompt: str) -> str:
    text = re.sub(r"[^a-z0-9\s._-]+", " ", prompt.lower())
    text = re.sub(r"\s+", " ", text).strip()
    if (
        any(word in text for word in ["zip", "archive", "bundle", "compressed"])
        or re.search(r"\b(give|send|download|provide|de|dedo|do|chahiye).*\bzip\b", text)
        or re.search(r"\bzip\b.*\b(file|de|dedo|do|chahiye|download)\b", text)
    ):
        return "zip"
    if any(word in text for word in ["html", "webpage", "web page", "landing page"]):
        return "html"
    if any(word in text for word in ["excel", "xlsx", "spreadsheet", "sheet"]):
        return "excel"
    if any(word in text for word in ["pdf", "report", "invoice", "resume", "document"]):
        return "pdf"
    if any(word in text for word in ["video", "animation", "reel", "shorts"]):
        return "video"
    if any(word in text for word in ["image", "img", "photo", "poster", "logo", "banner", "thumbnail", "wallpaper", "tasveer", "chitra", "billi", "cat"]):
        return "image"
    if any(word in text for word in ["markdown", "txt", "note", "file"]):
        return "document"
    return "document"


def write_metadata(folder: Path, payload: dict) -> None:
    (folder / "artifact.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def list_artifacts() -> list[dict]:
    root = artifacts_root()
    items = []
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        metadata_path = folder / "artifact.json"
        if not metadata_path.exists():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        items.append(metadata)
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def get_artifact_file(artifact_id: str, filename: str) -> Path:
    folder = artifacts_root() / safe_name(artifact_id)
    target = (folder / filename).resolve()
    if not str(target).startswith(str(folder.resolve())) or not target.is_file():
        raise FileNotFoundError("Artifact file not found.")
    return target


def create_artifact(prompt: str, artifact_type: str | None = None, previous_prompt: str = "") -> dict:
    kind = artifact_type or classify_artifact(prompt)
    final_prompt = f"Previous artifact request: {previous_prompt}\nRequested changes: {prompt}" if previous_prompt else prompt
    artifact_id = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{safe_name(prompt)}-{uuid4().hex[:6]}"
    folder = artifacts_root() / artifact_id
    folder.mkdir(parents=True, exist_ok=False)

    if kind == "image":
        files = create_real_image(folder, final_prompt)
        title = "Generated image"
    elif kind == "video":
        files = create_video_scene(folder, prompt)
        title = "Generated video scene"
    elif kind == "pdf":
        files = create_pdf(folder, prompt)
        title = "Generated PDF"
    elif kind == "excel":
        files = create_excel(folder, prompt)
        title = "Generated Excel workbook"
    elif kind == "html":
        files = create_html_file(folder, prompt)
        title = "Generated HTML file"
    elif kind == "zip":
        files = create_zip_file(folder, prompt)
        title = "Generated ZIP archive"
    else:
        files = create_document(folder, prompt)
        title = "Generated document"

    metadata = {
        "id": artifact_id,
        "type": kind,
        "title": title,
        "prompt": final_prompt,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "files": files,
        "primary_file": files[0]["name"] if files else "",
    }
    write_metadata(folder, metadata)
    return metadata


def create_real_image(folder: Path, prompt: str) -> list[dict]:
    if "ai-svg" not in prompt.lower():
        return create_svg_image(folder, prompt)

    import json as _json
    import urllib.request
    import urllib.error

    settings = get_settings()
    ollama_url = settings.ollama_base_url + "/api/chat"

    svg_system = (
        "You are an SVG artist. Generate ONLY valid SVG code, no explanation, no markdown. "
        "Create a detailed, colorful, visually rich SVG illustration. "
        "Use gradients, shapes, circles, paths, rects. Make it beautiful and artistic. "
        "Output ONLY the <svg> tag and its contents, nothing else."
    )
    svg_messages = [
        {"role": "system", "content": svg_system},
        {"role": "user", "content": f"Create a detailed SVG illustration of: {prompt}. Make it colorful, detailed, at least 800x600."},
    ]
    try:
        req = urllib.request.Request(
            ollama_url,
            data=_json.dumps({"model": settings.aurine_native_model, "messages": svg_messages, "stream": False, "options": {"temperature": 0.7}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        svg_text = data.get("message", {}).get("content", "")
        svg_start = svg_text.find("<svg")
        svg_end = svg_text.rfind("</svg>")
        if svg_start >= 0 and svg_end > svg_start:
            svg_content = svg_text[svg_start:svg_end + 6]
            path = folder / "image.svg"
            path.write_text(svg_content, encoding="utf-8")
            return [{"name": "image.svg", "kind": "image/svg+xml"}]
    except Exception:
        pass

    html_system = (
        "You are a visual artist. Generate ONLY a complete HTML page with inline CSS that creates "
        "a beautiful, colorful visual illustration. Use gradients, animations, shapes via CSS. "
        "Output ONLY the <!doctype html> document, no explanation."
    )
    html_messages = [
        {"role": "system", "content": html_system},
        {"role": "user", "content": f"Create a beautiful visual illustration of: {prompt}. Use vibrant colors, gradients, shapes, make it artistic."},
    ]
    try:
        req = urllib.request.Request(
            ollama_url,
            data=_json.dumps({"model": settings.aurine_native_model, "messages": html_messages, "stream": False, "options": {"temperature": 0.7}}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        html_text = data.get("message", {}).get("content", "")
        if "<!doctype" in html_text.lower() or "<html" in html_text.lower():
            html_start = html_text.find("<!doctype")
            if html_start < 0:
                html_start = html_text.find("<html")
            if html_start >= 0:
                path = folder / "image.html"
                path.write_text(html_text[html_start:], encoding="utf-8")
                return [{"name": "image.html", "kind": "text/html"}]
    except Exception:
        pass

    return create_svg_image(folder, prompt)


def create_svg_image(folder: Path, prompt: str) -> list[dict]:
    title = html.escape(prompt[:90] or "Aurine image")
    lines = textwrap.wrap(prompt, width=42)[:5]
    text_nodes = "\n".join(
        f'<text x="70" y="{290 + index * 34}" class="caption">{html.escape(line)}</text>'
        for index, line in enumerate(lines)
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop stop-color="#07111f"/>
      <stop offset=".55" stop-color="#12344a"/>
      <stop offset="1" stop-color="#3b1c68"/>
    </linearGradient>
    <radialGradient id="glow" cx=".72" cy=".22" r=".7">
      <stop stop-color="#2dd4bf" stop-opacity=".75"/>
      <stop offset="1" stop-color="#2dd4bf" stop-opacity="0"/>
    </radialGradient>
    <style>
      .title {{ font: 900 64px 'Segoe UI', sans-serif; fill: #eef7ff; }}
      .caption {{ font: 500 27px 'Segoe UI', sans-serif; fill: #bfd7ff; }}
      .code {{ font: 700 22px Consolas, monospace; fill: #5eead4; opacity: .42; }}
    </style>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)"/>
  <rect width="1280" height="720" fill="url(#glow)"/>
  <g opacity=".45">
    <circle cx="920" cy="210" r="170" fill="#7c3aed"/>
    <circle cx="1030" cy="330" r="110" fill="#2dd4bf"/>
    <circle cx="840" cy="405" r="72" fill="#60a5fa"/>
  </g>
  <path d="M0 585 C240 495 450 670 680 585 C900 505 1030 585 1280 500 L1280 720 L0 720 Z" fill="#050812" opacity=".82"/>
  <text x="70" y="140" class="code">Aurine.create(image)</text>
  <text x="70" y="230" class="title">{title}</text>
  {text_nodes}
  <text x="70" y="650" class="code">generated_artifact: image.svg</text>
</svg>"""
    path = folder / "image.svg"
    path.write_text(svg, encoding="utf-8")
    return [{"name": "image.svg", "kind": "image/svg+xml"}]


def create_document(folder: Path, prompt: str) -> list[dict]:
    content = (
        "# Aurine Created Document\n\n"
        f"Request:\n{prompt}\n\n"
        f"Created:\n{datetime.utcnow().isoformat()}Z\n\n"
        "Aurine understood the request even if it was written in Hinglish, another language, or with spelling mistakes.\n"
    )
    path = folder / "document.md"
    path.write_text(content, encoding="utf-8")
    return [{"name": "document.md", "kind": "text/markdown"}]


def create_html_file(folder: Path, prompt: str) -> list[dict]:
    safe_prompt = html.escape(prompt)
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Aurine Created Page</title>
  <style>
    body {{ margin: 0; font-family: Inter, Segoe UI, Arial, sans-serif; color: #eef7ff; background: #07111f; }}
    main {{ min-height: 100vh; display: grid; place-items: center; padding: 32px; background: linear-gradient(135deg, #07111f, #174256 55%, #31245f); }}
    section {{ width: min(860px, 100%); }}
    h1 {{ font-size: clamp(34px, 7vw, 76px); margin: 0 0 18px; }}
    p {{ font-size: 20px; line-height: 1.6; color: #c9e7ff; }}
    .badge {{ display: inline-block; margin-bottom: 18px; color: #07111f; background: #7dd3fc; padding: 8px 12px; border-radius: 999px; font-weight: 800; }}
  </style>
</head>
<body>
  <main>
    <section>
      <div class="badge">Aurine real HTML artifact</div>
      <h1>Created from your request</h1>
      <p>{safe_prompt}</p>
    </section>
  </main>
</body>
</html>"""
    path = folder / "page.html"
    path.write_text(html_text, encoding="utf-8")
    return [{"name": "page.html", "kind": "text/html"}]


def create_zip_file(folder: Path, prompt: str) -> list[dict]:
    readme = (
        "# Aurine ZIP Bundle\n\n"
        f"Request: {prompt}\n\n"
        "This is a real ZIP archive generated by Aurine. Add more exact file names in your prompt to create a fuller bundle.\n"
    )
    sample = f"Created at {datetime.utcnow().isoformat()}Z\nPrompt: {prompt}\n"
    path = folder / "bundle.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", readme)
        archive.writestr("content.txt", sample)
    return [{"name": "bundle.zip", "kind": "application/zip"}]


def create_video_scene(folder: Path, prompt: str) -> list[dict]:
    path = folder / "video.avi"
    create_simple_avi(path, prompt)
    return [{"name": "video.avi", "kind": "video/x-msvideo"}]


def create_simple_avi(path: Path, prompt: str) -> None:
    width, height, frames, fps = 320, 180, 72, 12
    row_size = ((width * 3 + 3) // 4) * 4
    frame_size = row_size * height
    movi = bytearray()
    idx = bytearray()
    offset = 4
    for frame in range(frames):
        pixels = bytearray()
        for y in range(height - 1, -1, -1):
            row = bytearray()
            for x in range(width):
                r = (x + frame * 4) % 256
                g = (y * 2 + frame * 5) % 256
                b = (80 + x // 3 + y // 4 + frame * 3) % 256
                row.extend([b, g, r])
            row.extend(b"\x00" * (row_size - width * 3))
            pixels.extend(row)
        chunk_data = bytes(pixels)
        movi.extend(b"00db" + struct.pack("<I", frame_size) + chunk_data)
        idx.extend(b"00db" + struct.pack("<III", 0x10, offset, frame_size))
        offset += 8 + frame_size

    avih = struct.pack("<IIIIIIIIIIIIIIII", int(1_000_000 / fps), frame_size * fps, 0, 0x10, frames, 0, 1, frame_size, width, height, 0, 0, 0, 0, 0, 0)
    strh = struct.pack("<4s4sIHHIIIIIIIIhhhh", b"vids", b"DIB ", 0, 0, 0, 0, 1, fps, 0, frames, frame_size, 0xFFFFFFFF, 0, 0, 0, width, height)
    strf = struct.pack("<IIIHHIIIIII", 40, width, height, 1, 24, 0, frame_size, 0, 0, 0, 0)

    def chunk(name: bytes, data: bytes) -> bytes:
        return name + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) % 2 else b"")

    def list_chunk(kind: bytes, data: bytes) -> bytes:
        return b"LIST" + struct.pack("<I", len(data) + 4) + kind + data

    note = f"Aurine real video: {prompt[:160]}".encode("ascii", errors="ignore")
    hdrl = list_chunk(b"hdrl", chunk(b"avih", avih) + list_chunk(b"strl", chunk(b"strh", strh) + chunk(b"strf", strf)))
    body = b"AVI " + hdrl + list_chunk(b"INFO", chunk(b"ISBJ", note)) + list_chunk(b"movi", bytes(movi)) + chunk(b"idx1", bytes(idx))
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def create_video_scene_html(folder: Path, prompt: str) -> list[dict]:
    safe_prompt = html.escape(prompt)
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Aurine Video Scene</title>
  <style>
    body {{ margin:0; background:#050812; color:#eaf2ff; font-family:Inter,Segoe UI,sans-serif; }}
    .stage {{ min-height:100vh; display:grid; place-items:center; overflow:hidden; background:radial-gradient(circle at 70% 20%, #2dd4bf55, transparent 35%), linear-gradient(135deg,#050812,#111a33 55%,#2e1065); }}
    .card {{ width:min(900px,90vw); aspect-ratio:16/9; position:relative; border:1px solid #2dd4bf55; border-radius:18px; overflow:hidden; box-shadow:0 30px 90px #0008; }}
    .orb {{ position:absolute; width:260px; height:260px; border-radius:50%; background:#7c3aed; filter:blur(12px); animation:float 6s ease-in-out infinite alternate; }}
    .orb.two {{ right:8%; bottom:10%; background:#2dd4bf; animation-delay:-2s; }}
    h1 {{ position:absolute; left:48px; bottom:150px; right:48px; font-size:54px; line-height:1.05; margin:0; }}
    p {{ position:absolute; left:52px; bottom:72px; right:52px; font-size:22px; color:#bfd7ff; }}
    .scan {{ position:absolute; inset:0; background:linear-gradient(transparent, #2dd4bf22, transparent); animation:scan 4s linear infinite; }}
    @keyframes float {{ from {{ transform:translate(-20px,-12px) scale(.9); }} to {{ transform:translate(70px,34px) scale(1.2); }} }}
    @keyframes scan {{ from {{ transform:translateY(-100%); }} to {{ transform:translateY(100%); }} }}
  </style>
</head>
<body>
  <section class="stage">
    <div class="card">
      <div class="orb"></div>
      <div class="orb two"></div>
      <div class="scan"></div>
      <h1>Aurine Video Scene</h1>
      <p>{safe_prompt}</p>
    </div>
  </section>
</body>
</html>"""
    path = folder / "video-scene.html"
    path.write_text(html_text, encoding="utf-8")
    return [{"name": "video-scene.html", "kind": "text/html"}]


def create_excel(folder: Path, prompt: str) -> list[dict]:
    rows = [
        ["Aurine Excel Workbook"],
        ["Request", prompt],
        ["Status", "Created as a real .xlsx file"],
        [],
        ["Item", "Detail"],
        ["Generated at", datetime.utcnow().isoformat() + "Z"],
        ["Next step", "Open this workbook in Excel or upload it back to Aurine."],
    ]

    def cell_ref(col: int, row: int) -> str:
        name = ""
        col += 1
        while col:
            col, rem = divmod(col - 1, 26)
            name = chr(65 + rem) + name
        return f"{name}{row}"

    sheet_rows = []
    for r_index, row in enumerate(rows, start=1):
        cells = []
        for c_index, value in enumerate(row):
            ref = cell_ref(c_index, r_index)
            text = html.escape(str(value))
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        sheet_rows.append(f'<row r="{r_index}">{"".join(cells)}</row>')

    files = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        "xl/workbook.xml": """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Aurine" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        "xl/_rels/workbook.xml.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        "xl/worksheets/sheet1.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>""",
    }
    path = folder / "workbook.xlsx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return [{"name": "workbook.xlsx", "kind": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}]


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def create_pdf(folder: Path, prompt: str) -> list[dict]:
    lines = ["Aurine Created PDF", "", "Request:"] + textwrap.wrap(prompt, width=78)
    stream_lines = ["BT", "/F1 18 Tf", "72 760 Td", "24 TL"]
    for index, line in enumerate(lines[:30]):
        font = "/F1 18 Tf" if index == 0 else "/F1 11 Tf"
        stream_lines.append(font)
        stream_lines.append(f"({pdf_escape(line)}) Tj")
        stream_lines.append("T*")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines)
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream.encode('latin-1', errors='ignore'))} >>\nstream\n{stream}\nendstream",
    ]
    pdf = "%PDF-1.4\n"
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf.encode("latin-1")))
        pdf += f"{number} 0 obj\n{obj}\nendobj\n"
    xref = len(pdf.encode("latin-1"))
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    path = folder / "document.pdf"
    path.write_bytes(pdf.encode("latin-1", errors="ignore"))
    return [{"name": "document.pdf", "kind": "application/pdf"}]


