from pathlib import Path

import pytest

from woomba.media.silence import detect_silence, invert_to_keep_ranges

FIXTURE = Path(__file__).parent / "fixtures" / "silence_demo.mp4"


@pytest.mark.skipif(not FIXTURE.exists(), reason="Run scripts/make_fixture.sh first")
def test_detect_silence_in_fixture() -> None:
    silence = detect_silence(FIXTURE, noise_db=-35.0, min_silence_s=0.3)
    assert silence, "expected a silent middle section"
    assert any(800 <= s.start_ms <= 1400 for s in silence)


def test_invert_keep_ranges() -> None:
    from woomba.media.silence import TimeRange

    silence = [TimeRange(1000, 2000)]
    keep = invert_to_keep_ranges(3000, silence, pad_ms=0, min_keep_ms=100)
    assert keep[0].start_ms == 0
    assert keep[0].end_ms == 1000
    assert keep[-1].end_ms == 3000
