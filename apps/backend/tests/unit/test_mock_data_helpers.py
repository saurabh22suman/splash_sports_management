"""Unit tests for pure helpers in mock_data.py."""

from __future__ import annotations

from datetime import datetime, timezone

from scripts.mock_data import (
    _to_e164,
    _weighted_status,
    _pick_window,
    _pick_time_slot,
)


def test_to_e164_strips_spaces():
    assert _to_e164("+61 4 1200 0001") == "+61412000001"


def test_to_e164_keeps_already_e164():
    assert _to_e164("+61412000001") == "+61412000001"


def test_weighted_status_returns_known_status():
    rng = __import__("random").Random(42)
    for _ in range(100):
        s = _weighted_status(rng)
        assert s in {"confirmed", "completed", "cancelled", "no_show"}


def test_weighted_status_distribution_within_tolerance():
    import random

    rng = random.Random(42)
    counts = {"confirmed": 0, "completed": 0, "cancelled": 0, "no_show": 0}
    for _ in range(1000):
        counts[_weighted_status(rng)] += 1
    # 60/20/10/10 distribution with reasonable tolerance
    assert 500 <= counts["confirmed"] <= 700
    assert 150 <= counts["completed"] <= 250
    assert 50 <= counts["cancelled"] <= 150
    assert 50 <= counts["no_show"] <= 150


def test_pick_window_for_confirmed_within_next_14_days():
    rng = __import__("random").Random(42)
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    start, _ = _pick_window("confirmed", rng, now)
    # next 14 days = 2026-08-07 to 2026-08-21
    assert now <= start <= datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def test_pick_window_for_completed_in_past_30_days():
    rng = __import__("random").Random(42)
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    start, _ = _pick_window("completed", rng, now)
    assert datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc) <= start < now


def test_pick_time_slot_returns_known_window():
    rng = __import__("random").Random(42)
    for _ in range(50):
        start = _pick_time_slot(rng, datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc))
        hour = start.hour
        # Morning cluster 6-9 or evening cluster 17-20
        assert 6 <= hour <= 9 or 17 <= hour <= 20, f"unexpected hour {hour}"
