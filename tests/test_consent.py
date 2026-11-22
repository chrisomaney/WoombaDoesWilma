from pathlib import Path

import pytest

from woomba.consent import accept_consent, read_consent, require_consent


def test_consent_defaults_false(tmp_path: Path) -> None:
    record = read_consent(tmp_path)
    assert record.accepted is False
    assert record.accepted_at is None


def test_accept_consent(tmp_path: Path) -> None:
    record = accept_consent(tmp_path)
    assert record.accepted is True
    assert record.accepted_at
    again = read_consent(tmp_path)
    assert again.accepted is True


def test_require_consent_blocks(tmp_path: Path) -> None:
    with pytest.raises(PermissionError):
        require_consent(tmp_path)
    accept_consent(tmp_path)
    require_consent(tmp_path)
