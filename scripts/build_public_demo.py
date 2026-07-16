"""Build the deterministic, silent 60-second constructed-demo asset."""

from __future__ import annotations

import json
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "site" / "assets"
SIZE = (1280, 720)
FPS = 2
DISCLOSURE = (
    "Deliberately constructed demo — deterministic evidence rules and human review. "
    "ScopeProof does not guarantee correctness or replace QA."
)


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    arial = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf"
    )
    dejavu = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    candidates = [
        Path(arial),
        Path("/System/Library/Fonts/Helvetica.ttc"),
        Path(dejavu),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _fit_cover(image: Image.Image) -> Image.Image:
    source = image.convert("RGB")
    scale = max(SIZE[0] / source.width, SIZE[1] / source.height)
    resized = source.resize(
        (round(source.width * scale), round(source.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - SIZE[0]) // 2
    top = (resized.height - SIZE[1]) // 2
    return resized.crop((left, top, left + SIZE[0], top + SIZE[1]))


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _captioned(source: Path, caption: str, *, disclosure: bool = False) -> Image.Image:
    frame = _fit_cover(Image.open(source))
    draw = ImageDraw.Draw(frame, "RGBA")
    caption_font = _font(30, bold=True)
    small_font = _font(19)
    lines = _wrap(draw, caption, caption_font, 1120)
    disclosure_lines = _wrap(draw, DISCLOSURE, small_font, 1120) if disclosure else []
    panel_height = 42 + len(lines) * 43 + len(disclosure_lines) * 30
    panel_top = SIZE[1] - panel_height
    draw.rectangle((0, panel_top, SIZE[0], SIZE[1]), fill=(5, 7, 10, 235))
    y = panel_top + 20
    for line in lines:
        draw.text((80, y), line, font=caption_font, fill=(247, 247, 242, 255))
        y += 43
    for line in disclosure_lines:
        draw.text((80, y + 2), line, font=small_font, fill=(216, 255, 99, 255))
        y += 30
    return frame


def _title_frame() -> Image.Image:
    frame = Image.new("RGB", SIZE, "#0d0f12")
    draw = ImageDraw.Draw(frame, "RGBA")
    draw.ellipse((820, -340, 1500, 340), fill=(140, 236, 255, 24))
    draw.ellipse((-280, 420, 360, 1060), fill=(216, 255, 99, 20))
    draw.rounded_rectangle((72, 70, 150, 148), radius=17, fill="#d8ff63")
    draw.text((92, 91), "SP", font=_font(23, bold=True), fill="#0d0f12")
    draw.text((180, 89), "ScopeProof", font=_font(34, bold=True), fill="#f7f7f2")
    draw.text((76, 230), "Does this PR prove", font=_font(66, bold=True), fill="#f7f7f2")
    draw.text((76, 305), "the requirement?", font=_font(66, bold=True), fill="#f7f7f2")
    draw.text(
        (79, 425),
        "PR  →  Criteria  →  Evidence  →  Decisions  →  Outcome",
        font=_font(27, bold=True),
        fill="#8cecff",
    )
    disclosure_lines = _wrap(draw, DISCLOSURE, _font(22), 1080)
    y = 535
    for line in disclosure_lines:
        draw.text((80, y), line, font=_font(22), fill="#d8ff63")
        y += 34
    return frame


def build() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    title = _title_frame()
    title.save(ASSETS / "scopeproof-demo-poster.jpg", quality=92, optimize=True)
    scenes = [
        (5, title),
        (
            10,
            _captioned(
                ASSETS / "demo-criteria.png",
                "A source owner confirms normalized criteria before analysis.",
            ),
        ),
        (
            20,
            _captioned(
                ASSETS / "demo-evidence.png",
                "Deterministic rules cite evidence candidates—or state what is missing.",
            ),
        ),
        (
            15,
            _captioned(
                ASSETS / "demo-missing.png",
                "Missing stays Missing. A human decides what the evidence means.",
            ),
        ),
        (
            10,
            _captioned(
                ASSETS / "demo-summary.png",
                "Record one honest outcome; never turn a technical run into validation.",
                disclosure=True,
            ),
        ),
    ]
    output = ASSETS / "scopeproof-captioned-demo.mp4"
    writer = imageio_ffmpeg.write_frames(
        str(output),
        SIZE,
        fps=FPS,
        codec="libx264",
        pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p",
        output_params=[
            "-movflags",
            "+faststart",
            "-an",
            "-metadata",
            "title=ScopeProof constructed demo",
        ],
    )
    writer.send(None)
    try:
        for seconds, frame in scenes:
            payload = frame.convert("RGB").tobytes()
            for _ in range(seconds * FPS):
                writer.send(payload)
    finally:
        writer.close()

    manifest = {
        "asset": output.name,
        "duration_seconds": 60,
        "dimensions": list(SIZE),
        "frames_per_second": FPS,
        "audio": False,
        "source_type": "deliberately_constructed_demo",
        "source_frames": [
            "generated title and disclosure",
            "demo-criteria.png",
            "demo-evidence.png",
            "demo-missing.png",
            "demo-summary.png",
        ],
        "disclosure": DISCLOSURE,
        "generator": "scripts/build_public_demo.py",
    }
    (ASSETS / "demo-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build()
