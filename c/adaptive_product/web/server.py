#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import subprocess
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
C_ROOT = ROOT.parent
ENGINES: dict[str, dict[str, object]] = {
    "product": {
        "label": "Adaptive Product",
        "bins": [
            ROOT / "bin" / "ad_enhance.exe",
            ROOT / "bin" / "ad_enhance",
        ],
    },
    "contour_1": {
        "label": "Contour 1",
        "bins": [
            C_ROOT / "contour_1" / "bin" / "ad_enhance.exe",
            C_ROOT / "contour_1" / "bin" / "ad_enhance",
        ],
    },
}
DEFAULT_ENGINE = "contour_1"
OUT_DIR = ROOT / "out" / "web"
OUT_DIR.mkdir(parents=True, exist_ok=True)
HOST = "127.0.0.1"
PORT = int(__import__("os").environ.get("AD_PORT", "8765"))


def find_enhance_bin(engine: str) -> Path:
    cfg = ENGINES.get(engine)
    if cfg is None:
        raise FileNotFoundError(f"unknown engine: {engine}")
    bins = cfg["bins"]
    assert isinstance(bins, list)
    for path in bins:
        assert isinstance(path, Path)
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"ad_enhance binary not found for {engine}. Build contour_1 / adaptive_product first."
    )


def parse_enhance_output(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def normalize_meta(meta: dict[str, str], engine: str) -> dict[str, str]:
    out = dict(meta)
    out["engine"] = engine
    label = ENGINES.get(engine, {}).get("label")
    if isinstance(label, str):
        out["engine_label"] = label

    aliases = [
        ("time_assess_s", "assess_s"),
        ("time_decide_s", "decide_s"),
        ("time_apply_s", "apply_s"),
        ("time_core_s", "total_s"),
        ("time_assess_x100000", "assess_x100000"),
        ("time_decide_x100000", "decide_x100000"),
        ("time_apply_x100000", "apply_x100000"),
        ("time_core_x100000", "total_x100000"),
    ]
    for preferred, fallback in aliases:
        if preferred not in out and fallback in out:
            out[preferred] = out[fallback]
    if "time_all_s" not in out and "time_core_s" in out:
        out["time_all_s"] = out["time_core_s"]
    if "time_all_x100000" not in out and "time_core_x100000" in out:
        out["time_all_x100000"] = out["time_core_x100000"]
    return out


def _to_yuv(rgb: Image.Image) -> tuple[Image.Image, Image.Image, Image.Image]:
    ycbcr = rgb.convert("YCbCr")
    y, cb, cr = ycbcr.split()
    return y, cb, cr


def _from_yuv(y: Image.Image, cb: Image.Image, cr: Image.Image) -> Image.Image:
    return Image.merge("YCbCr", (y, cb, cr)).convert("RGB")


def _label_plane(plane: Image.Image, title: str) -> Image.Image:
    canvas = ImageOps.expand(plane.convert("L").convert("RGB"), border=0)
    draw = ImageDraw.Draw(canvas)
    pad = 8
    text = title
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    box = (pad, pad, pad + tw + 12, pad + th + 10)
    draw.rectangle(box, fill=(0, 0, 0))
    draw.text((pad + 6, pad + 4), text, fill=(220, 240, 228), font=font)
    return canvas


def build_layers_strip(y: Image.Image, cb: Image.Image, cr: Image.Image) -> Image.Image:
    panels = [
        _label_plane(y, "Y"),
        _label_plane(cb, "U / Cb"),
        _label_plane(cr, "V / Cr"),
    ]
    h = max(p.height for p in panels)
    gap = 8
    total_w = sum(p.width for p in panels) + gap * (len(panels) - 1)
    strip = Image.new("RGB", (total_w, h), (8, 12, 10))
    x = 0
    for panel in panels:
        if panel.height != h:
            panel = ImageOps.pad(panel, (panel.width, h), color=(8, 12, 10))
        strip.paste(panel, (x, 0))
        x += panel.width + gap
    return strip


def rebuild_color_after(in_path: Path, gray_out_path: Path, color_out_path: Path, layers_path: Path) -> None:
    original = Image.open(in_path).convert("RGB")
    y0, cb, cr = _to_yuv(original)
    y_enhanced = Image.open(gray_out_path).convert("L")
    if y_enhanced.size != y0.size:
        y_enhanced = y_enhanced.resize(y0.size, Image.Resampling.BILINEAR)
    color = _from_yuv(y_enhanced, cb, cr)
    color.save(color_out_path)
    build_layers_strip(y_enhanced, cb, cr).save(layers_path)


INDEX_HTML = """<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Adaptive Enhance</title>
  <style>
    :root {
      --bg0: #0f1412;
      --bg1: #1a2420;
      --ink: #e8f0ea;
      --muted: #9bb0a3;
      --accent: #3dcf8e;
      --line: rgba(232, 240, 234, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", "Candara", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1200px 600px at 10% -10%, #244036 0%, transparent 55%),
        radial-gradient(900px 500px at 100% 0%, #1d2c40 0%, transparent 50%),
        linear-gradient(160deg, var(--bg0), var(--bg1));
    }
    main {
      width: min(1400px, calc(100% - 2rem));
      margin: 0 auto;
      padding: 2.5rem 0 3rem;
    }
    h1 {
      margin: 0 0 0.4rem;
      font-size: clamp(1.8rem, 4vw, 2.6rem);
      letter-spacing: 0.02em;
    }
    p.lead {
      margin: 0 0 1.6rem;
      color: var(--muted);
      max-width: 46rem;
    }
    .panel {
      border: 1px solid var(--line);
      background: rgba(8, 12, 10, 0.45);
      backdrop-filter: blur(8px);
      padding: 1.2rem;
    }
    .row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.8rem;
      align-items: center;
      margin-bottom: 1rem;
    }
    label.engine {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      color: var(--muted);
      font-size: 0.95rem;
    }
    select {
      background: #0c1210;
      color: var(--ink);
      border: 1px solid var(--line);
      padding: 0.55rem 0.7rem;
    }
    input[type="file"] {
      color: var(--muted);
    }
    button {
      border: 0;
      background: var(--accent);
      color: #062216;
      font-weight: 700;
      padding: 0.7rem 1.1rem;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.5;
      cursor: wait;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1rem;
    }
    @media (max-width: 1100px) {
      .grid { grid-template-columns: 1fr; }
    }
    figure {
      margin: 0;
      border: 1px solid var(--line);
      background: #050807;
    }
    figure img {
      display: block;
      width: 100%;
      height: auto;
      max-height: 420px;
      object-fit: contain;
      background: #050807;
    }
    figcaption {
      padding: 0.55rem 0.7rem;
      color: var(--muted);
      font-size: 0.92rem;
      border-top: 1px solid var(--line);
    }
    pre {
      margin: 1rem 0 0;
      padding: 0.9rem;
      overflow: auto;
      border: 1px solid var(--line);
      background: rgba(0, 0, 0, 0.35);
      color: #cfe7d8;
      font-size: 0.85rem;
    }
    .err { color: #ff8f8f; }
    .timing {
      margin-top: 1rem;
      padding: 0.9rem;
      border: 1px solid var(--line);
      background: rgba(0, 0, 0, 0.28);
      color: #d7e7d8;
      font-size: 0.9rem;
    }
    .timing table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 0.55rem;
    }
    .timing th, .timing td {
      text-align: left;
      padding: 0.28rem 0.4rem;
      border-bottom: 1px solid var(--line);
      font-variant-numeric: tabular-nums;
    }
    .timing th { color: var(--muted); font-weight: 600; }
  </style>
</head>
<body>
  <main>
    <h1>Adaptive Enhance</h1>
    <p class="lead">Завантаж фото — обери ядро (Contour 1 або Product), оцінка + маршрут + apply. Третє вікно показує шари Y, U, V.</p>
    <section class="panel">
      <div class="row">
        <label class="engine" for="engine">Ядро
          <select id="engine">
            <option value="contour_1" selected>Contour 1</option>
            <option value="product">Adaptive Product</option>
          </select>
        </label>
        <input id="file" type="file" accept="image/png,image/jpeg,image/bmp,.png,.jpg,.jpeg,.bmp" />
        <button id="run" type="button">Покращити</button>
      </div>
      <div class="grid">
        <figure>
          <img id="before" alt="До" />
          <figcaption>До</figcaption>
        </figure>
        <figure>
          <img id="after" alt="Після" />
          <figcaption>Після (Y виправлено + U/V)</figcaption>
        </figure>
        <figure>
          <img id="layers" alt="Шари Y U V" />
          <figcaption>Шари Y · U · V</figcaption>
        </figure>
      </div>
      <div id="timing" class="timing">Підсумок часу з’явиться після обробки (одиниця: 1/100000 с).</div>
      <pre id="meta">Очікую файл…</pre>
    </section>
  </main>
  <script>
    const fileInput = document.getElementById("file");
    const engineSelect = document.getElementById("engine");
    const runBtn = document.getElementById("run");
    const before = document.getElementById("before");
    const after = document.getElementById("after");
    const layers = document.getElementById("layers");
    const meta = document.getElementById("meta");
    const timingBox = document.getElementById("timing");

    function timingSummary(m) {
      const rows = [
        ["engine", m.engine_label || m.engine, ""],
        ["assess (оцінка)", m.time_assess_s, m.time_assess_x100000],
        ["decide (маршрут)", m.time_decide_s, m.time_decide_x100000],
        ["apply (корекція)", m.time_apply_s, m.time_apply_x100000],
        ["CORE = assess+decide+apply", m.time_core_s, m.time_core_x100000],
        ["load (читання файлу)", m.time_load_s, m.time_load_x100000],
        ["save (запис PNG)", m.time_save_s, m.time_save_x100000],
        ["ALL = core + I/O", m.time_all_s, m.time_all_x100000]
      ];
      let html = "<strong>Підсумок часу</strong> (с, 1/100000)<br/>";
      html += "<span style='color:#9bb0a3'>ALL виглядає більшим через save PNG — саме ядро дешеве.</span><table>";
      html += "<tr><th>операція</th><th>час, с</th><th>×100000</th></tr>";
      for (const row of rows) {
        const heavy = row[0].indexOf("ALL") === 0 || row[0].indexOf("save") === 0;
        const mark = row[0].indexOf("CORE") === 0 ? " style='color:#3dcf8e;font-weight:700'" : (heavy ? " style='color:#c9b28a'" : "");
        html += "<tr" + mark + "><td>" + row[0] + "</td><td>" + (row[1] || "—") + "</td><td>" + (row[2] || "—") + "</td></tr>";
      }
      html += "</table>";
      return html;
    }

    fileInput.addEventListener("change", () => {
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        return;
      }
      before.src = URL.createObjectURL(file);
      after.removeAttribute("src");
      layers.removeAttribute("src");
      meta.className = "";
      meta.textContent = "Файл готовий: " + file.name;
      timingBox.innerHTML = "Підсумок часу з’явиться після обробки (одиниця: 1/100000 с).";
    });

    runBtn.addEventListener("click", async () => {
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        meta.textContent = "Спочатку вибери фото.";
        meta.className = "err";
        return;
      }
      runBtn.disabled = true;
      meta.className = "";
      meta.textContent = "Обробка…";
      try {
        const body = new FormData();
        body.append("file", file, file.name);
        body.append("engine", engineSelect.value || "contour_1");
        const res = await fetch("/api/enhance", { method: "POST", body });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || "enhance failed");
        }
        const stamp = Date.now();
        after.src = data.output_url + "?t=" + stamp;
        layers.src = data.layers_url + "?t=" + stamp;
        timingBox.innerHTML = timingSummary(data.meta || {});
        meta.textContent = JSON.stringify(data.meta, null, 2);
      } catch (err) {
        meta.className = "err";
        meta.textContent = String(err.message || err);
      } finally {
        runBtn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        print("[%s] %s" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path.startswith("/out/"):
            rel = path[len("/out/") :]
            file_path = (OUT_DIR / rel).resolve()
            if not str(file_path).startswith(str(OUT_DIR.resolve())) or not file_path.is_file():
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            self._send(200, file_path.read_bytes(), ctype)
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/enhance":
            self._send(404, b'{"error":"not found"}', "application/json")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            boundary = self._multipart_boundary()
            fields = self._extract_fields(raw, boundary)
            payload = fields.get("file_bytes")
            filename = fields.get("filename")
            engine = fields.get("engine") or DEFAULT_ENGINE
            if engine not in ENGINES:
                raise ValueError(f"unknown engine: {engine}")
            if payload is None:
                raise ValueError("file field missing")
            assert isinstance(payload, bytes)
            ext = Path(str(filename or "upload.png")).suffix.lower()
            if ext not in (".png", ".jpg", ".jpeg", ".bmp"):
                ext = ".png"
            job = uuid.uuid4().hex
            in_path = OUT_DIR / f"{job}_in{ext}"
            gray_out_path = OUT_DIR / f"{job}_gray.png"
            color_out_path = OUT_DIR / f"{job}_out.png"
            layers_path = OUT_DIR / f"{job}_layers.png"
            in_path.write_bytes(payload)
            bin_path = find_enhance_bin(str(engine))
            cmd = [str(bin_path)]
            if str(engine) == "contour_1":
                cmd.append("--force")
            cmd.extend([str(in_path), str(gray_out_path)])
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0 or not gray_out_path.is_file():
                raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "enhance failed")
            meta = normalize_meta(parse_enhance_output(completed.stdout), str(engine))
            rebuild_color_after(in_path, gray_out_path, color_out_path, layers_path)
            body = json.dumps(
                {
                    "ok": True,
                    "output_url": f"/out/{color_out_path.name}",
                    "layers_url": f"/out/{layers_path.name}",
                    "meta": meta,
                }
            ).encode("utf-8")
            self._send(200, body, "application/json")
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
            self._send(400, body, "application/json")

    def _multipart_boundary(self) -> bytes:
        ctype = self.headers.get("Content-Type", "")
        marker = "boundary="
        idx = ctype.find(marker)
        if idx < 0:
            raise ValueError("multipart boundary missing")
        return ctype[idx + len(marker) :].encode("utf-8")

    def _extract_fields(self, raw: bytes, boundary: bytes) -> dict[str, object]:
        sep = b"--" + boundary
        parts = raw.split(sep)
        out: dict[str, object] = {}
        for part in parts:
            if b"Content-Disposition:" not in part:
                continue
            head, _, body = part.partition(b"\r\n\r\n")
            if not body:
                continue
            if body.endswith(b"\r\n"):
                body = body[:-2]
            if body.endswith(b"--"):
                body = body[:-2]
            disposition = head.decode("utf-8", errors="ignore")
            name = None
            filename = None
            for token in disposition.split(";"):
                token = token.strip()
                if token.startswith("name="):
                    name = token.split("=", 1)[1].strip().strip('"')
                if token.startswith("filename="):
                    filename = token.split("=", 1)[1].strip().strip('"')
            if name == "file":
                out["file_bytes"] = body
                out["filename"] = filename
            elif name == "engine":
                out["engine"] = body.decode("utf-8", errors="ignore").strip()
        return out


def main() -> None:
    available: list[str] = []
    has_any = False
    for key in ENGINES:
        try:
            path = find_enhance_bin(key)
            available.append(f"{key}={path}")
            has_any = True
        except FileNotFoundError as exc:
            available.append(f"{key}=MISSING ({exc})")
    if not has_any:
        raise SystemExit("No enhance binaries found. Build contour_1 and/or adaptive_product first.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Adaptive Enhance UI: http://{HOST}:{PORT}")
    for line in available:
        print(f"Binary: {line}")
    server.serve_forever()


if __name__ == "__main__":
    main()
