"""Tests for the on-disk kill-switch sentinel guard."""

from __future__ import annotations

from pathlib import Path

import pytest
from contracts.risk import RiskDecision
from engine.risk.kill_switch import KillSwitchGuard


def test_allow_when_sentinel_absent(tmp_path: Path) -> None:
    sentinel = tmp_path / "KILL"
    guard = KillSwitchGuard(sentinel)

    assert not sentinel.exists()
    state = guard.state()
    assert state.engaged is False
    assert state.sentinel_path == str(sentinel)

    result = guard.check()
    assert result.decision == RiskDecision.ALLOW
    assert result.allowed
    assert result.reasons


def test_block_when_sentinel_present(tmp_path: Path) -> None:
    sentinel = tmp_path / "KILL"
    sentinel.write_text("engaged")
    guard = KillSwitchGuard(sentinel)

    state = guard.state()
    assert state.engaged is True

    result = guard.check()
    assert result.decision == RiskDecision.BLOCK
    assert not result.allowed
    assert any("kill switch engaged" in r for r in result.reasons)


def test_state_toggles_when_sentinel_created_and_removed(tmp_path: Path) -> None:
    sentinel = tmp_path / "KILL"
    guard = KillSwitchGuard(sentinel)

    assert guard.state().engaged is False
    assert guard.check().decision == RiskDecision.ALLOW

    sentinel.touch()
    assert guard.state().engaged is True
    assert guard.check().decision == RiskDecision.BLOCK

    sentinel.unlink()
    assert guard.state().engaged is False
    assert guard.check().decision == RiskDecision.ALLOW


def test_accepts_string_path(tmp_path: Path) -> None:
    sentinel = tmp_path / "KILL"
    guard = KillSwitchGuard(str(sentinel))

    assert guard.check().decision == RiskDecision.ALLOW
    sentinel.touch()
    assert guard.check().decision == RiskDecision.BLOCK


def test_empty_file_still_blocks(tmp_path: Path) -> None:
    sentinel = tmp_path / "KILL"
    sentinel.write_text("")
    guard = KillSwitchGuard(sentinel)
    # Content does not matter; presence is the signal.
    assert guard.check().decision == RiskDecision.BLOCK


@pytest.mark.parametrize("filename", ["KILL", "STOP", ".halt"])
def test_arbitrary_filename(tmp_path: Path, filename: str) -> None:
    sentinel = tmp_path / filename
    guard = KillSwitchGuard(sentinel)
    assert guard.check().decision == RiskDecision.ALLOW
    sentinel.touch()
    assert guard.check().decision == RiskDecision.BLOCK
