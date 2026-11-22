from pathlib import Path

import pytest

from woomba.media.probe import probe_clip

FIXTURE = Path(__file__).parent / "fixtures" / "short_clean.mp4"


@pytest.mark.skipif(not FIXTURE.exists(), reason="Run scripts/make_fixture.sh first")
def test_probe_short_clean() -> None:
    info = probe_clip(FIXTURE)
    assert info.duration_ms >= 900
    assert info.width == 320
    assert info.height == 240
    assert info.has_audio is True
