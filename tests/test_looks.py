import struct
import zlib
from pathlib import Path

import pytest

from woomba.db import connect
from woomba.jobs import create_project
from woomba.media.export import export_project
from woomba.media.import_clips import import_paths
from woomba.media.looks import grade_and_body_filters, simple_vf, validate_looks
from woomba.models import CreativeLooks
from woomba.paths import backgrounds_dir, db_path
from woomba.timeline import load_timeline, save_timeline

FIXTURE = Path(__file__).parent / "fixtures" / "short_clean.mp4"


def _write_tiny_png(path: Path, rgb: tuple[int, int, int] = (20, 40, 80)) -> None:
    width = height = 8
    r, g, b = rgb
    raw = b"".join(b"\x00" + bytes([r, g, b]) * width for _ in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def test_grade_filters_include_body_and_face() -> None:
    looks = CreativeLooks(
        body_type="slim",
        face_look="soft_beauty",
        confirm_own_likeness=True,
    )
    chain = grade_and_body_filters(looks)
    assert any("scale=iw*1.12" in part for part in chain)
    assert any("unsharp" in part for part in chain)
    assert simple_vf(looks)


def test_validate_requires_confirmation(tmp_path: Path) -> None:
    looks = CreativeLooks(face_look="warm_glow", confirm_own_likeness=False)
    with pytest.raises(RuntimeError, match="confirm"):
        validate_looks(tmp_path, looks)


@pytest.mark.skipif(not FIXTURE.exists(), reason="Run scripts/make_fixture.sh first")
def test_export_with_body_look(tmp_path: Path) -> None:
    conn = connect(db_path(tmp_path))
    create_project(conn, tmp_path, "looks-demo")
    import_paths(tmp_path, "looks-demo", [FIXTURE])
    timeline = load_timeline(tmp_path, "looks-demo")
    timeline.looks = CreativeLooks(
        body_type="athletic",
        face_look="cool_clean",
        background_mode="solid",
        background_color="#223344",
        confirm_own_likeness=True,
    )
    save_timeline(tmp_path, timeline)
    out = export_project(tmp_path, "looks-demo")
    assert out.exists()
    assert out.stat().st_size > 1000


@pytest.mark.skipif(not FIXTURE.exists(), reason="Run scripts/make_fixture.sh first")
def test_chroma_image_export(tmp_path: Path) -> None:
    conn = connect(db_path(tmp_path))
    create_project(conn, tmp_path, "chroma-demo")
    import_paths(tmp_path, "chroma-demo", [FIXTURE])
    bg_dir = backgrounds_dir(tmp_path)
    _write_tiny_png(bg_dir / "room.png")
    timeline = load_timeline(tmp_path, "chroma-demo")
    timeline.looks = CreativeLooks(
        background_mode="chroma_image",
        background_image="room.png",
        chroma_color="green",
        confirm_own_likeness=True,
    )
    save_timeline(tmp_path, timeline)
    out = export_project(tmp_path, "chroma-demo")
    assert out.exists()
