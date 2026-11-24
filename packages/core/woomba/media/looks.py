from __future__ import annotations

import os
import re
from pathlib import Path

from woomba.models import CreativeLooks
from woomba.paths import assets_dir, backgrounds_dir, faces_dir

_HEX = re.compile(r"^#?[0-9a-fA-F]{6}$")
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def looks_active(looks: CreativeLooks) -> bool:
    return (
        looks.background_mode != "none"
        or looks.face_look != "none"
        or looks.body_type != "none"
        or looks.face_morph != "none"
    )


def needs_chroma_composite(looks: CreativeLooks) -> bool:
    return looks.background_mode in {"chroma_solid", "chroma_image"}


def validate_looks(library_root: Path, looks: CreativeLooks) -> None:
    if not looks_active(looks):
        return
    if not looks.confirm_own_likeness:
        raise RuntimeError(
            "Creative looks require confirming these edits only change your own "
            "(or mutually consented) likeness — enable the checkbox on Export."
        )
    if looks.background_mode in {"solid", "chroma_solid"} and not _HEX.match(looks.background_color):
        raise RuntimeError("background_color must be a #RRGGBB hex color.")
    if looks.background_mode == "chroma_image":
        if resolve_background(library_root, looks.background_image) is None:
            raise RuntimeError(
                "chroma_image needs a background still — upload one under assets/backgrounds/."
            )
    if looks.face_morph == "likeness_ref":
        if resolve_face_ref(library_root, looks.face_ref_image) is None:
            raise RuntimeError("likeness_ref needs your own face still in assets/faces/.")
        if not morph_engine_available(library_root):
            raise RuntimeError(
                "Face morph needs a local model pack. Place models under "
                f"{assets_dir(library_root) / 'models'} or set WOOMBA_LOOKS_MODELS. "
                "Face look grades and body reshape work without it."
            )
        # Hook reserved for a future on-device engine; refuse silent no-ops.
        raise RuntimeError(
            "A model pack folder is present, but the on-device likeness engine is not "
            "wired in this build yet. Use Face look / Body type for now."
        )


def morph_engine_available(library_root: Path) -> bool:
    custom = os.environ.get("WOOMBA_LOOKS_MODELS")
    if custom:
        path = Path(custom).expanduser()
        if path.is_dir() and any(path.iterdir()):
            return True
    models = assets_dir(library_root) / "models"
    return models.is_dir() and any(models.iterdir())


def resolve_background(library_root: Path, name: str | None) -> Path | None:
    if not name:
        return None
    candidate = backgrounds_dir(library_root) / Path(name).name
    return candidate if candidate.is_file() else None


def resolve_face_ref(library_root: Path, name: str | None) -> Path | None:
    if not name:
        return None
    candidate = faces_dir(library_root) / Path(name).name
    return candidate if candidate.is_file() else None


def list_backgrounds(library_root: Path) -> list[dict]:
    return _list_images(backgrounds_dir(library_root))


def list_face_refs(library_root: Path) -> list[dict]:
    return _list_images(faces_dir(library_root))


def _list_images(root: Path) -> list[dict]:
    items: list[dict] = []
    for path in sorted(root.iterdir()):
        if path.suffix.lower() in _IMAGE_EXTS and path.is_file():
            items.append({"name": path.name, "path": str(path), "size_bytes": path.stat().st_size})
    return items


def ffmpeg_color(hex_color: str) -> str:
    value = hex_color[1:] if hex_color.startswith("#") else hex_color
    return f"0x{value.lower()}"


def grade_and_body_filters(looks: CreativeLooks, *, blur_faces: bool = False) -> list[str]:
    chain: list[str] = []
    if looks.body_type == "slim":
        chain.append("scale=iw*1.12:ih,crop=iw/1.12:ih:(iw-ow)/2:0")
    elif looks.body_type == "soft":
        chain.append("scale=iw*0.92:ih,pad=iw/0.92:ih:(ow-iw)/2:0:black")
    elif looks.body_type == "athletic":
        chain.append("scale=iw:ih*1.06,crop=iw:ih/1.06:0:(ih-oh)/2")
    elif looks.body_type == "tall":
        chain.append("scale=iw:ih*1.1,crop=iw:ih/1.1:0:(ih-oh)/2")

    if looks.face_look == "soft_beauty":
        chain.append("eq=contrast=1.04:brightness=0.02:saturation=1.04,unsharp=3:3:0.35")
    elif looks.face_look == "warm_glow":
        chain.append(
            "eq=contrast=1.03:brightness=0.03:saturation=1.12,colorbalance=rs=0.06:gs=0.02:bs=-0.04"
        )
    elif looks.face_look == "cool_clean":
        chain.append(
            "eq=contrast=1.06:brightness=0.01:saturation=0.95,colorbalance=rs=-0.04:bs=0.06"
        )

    if looks.background_mode == "soft_blur":
        chain.append("boxblur=6:2,eq=saturation=0.9")
    elif looks.background_mode == "solid":
        color = ffmpeg_color(looks.background_color)
        chain.append(f"pad=iw+80:ih+80:40:40:{color}")

    if blur_faces:
        chain.append("boxblur=8:1")
    return chain


def simple_vf(looks: CreativeLooks, *, blur_faces: bool = False) -> str | None:
    if needs_chroma_composite(looks):
        return None
    chain = grade_and_body_filters(looks, blur_faces=blur_faces)
    return ",".join(chain) if chain else None


def chroma_filter_complex(looks: CreativeLooks, *, blur_faces: bool = False) -> str:
    """filter_complex that keys subject and overlays on solid or image (input 1)."""
    pre = grade_and_body_filters(looks, blur_faces=blur_faces)
    # Body/face grades run before chromakey on the foreground.
    if pre:
        fg = f"[0:v]{','.join(pre)},"
    else:
        fg = "[0:v]"
    key = "0x00FF00" if looks.chroma_color == "green" else "0xFF00FF"
    sim = max(0.05, min(0.6, looks.chroma_similarity))
    fg += f"chromakey={key}:{sim}:0.1,format=yuva420p[fg]"

    if looks.background_mode == "chroma_solid":
        color = ffmpeg_color(looks.background_color)
        bg = f"color=c={color}:s=1920x1080:d=3600[bg]"
        return (
            f"{bg};{fg};"
            f"[bg][fg]scale2ref[bg2][fg2];[bg2][fg2]overlay=format=auto,format=yuv420p[vout]"
        )
    # chroma_image — still is -i index 1
    return (
        f"[1:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080[bg];"
        f"{fg};"
        f"[bg][fg]scale2ref[bg2][fg2];[bg2][fg2]overlay=format=auto,format=yuv420p[vout]"
    )
