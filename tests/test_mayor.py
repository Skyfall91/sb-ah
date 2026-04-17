import pytest
from analyzers.mayor import MayorAnalyzer, MayorCycle


def make_history(base: float, spikes_at: list, spike_mult: float, days: int = 180) -> list[dict]:
    from datetime import datetime, timedelta
    result = []
    start = datetime(2025, 1, 1)
    for i in range(days):
        price = base * spike_mult if i in spikes_at else base
        result.append({"time": (start + timedelta(days=i)).isoformat(), "avg": price})
    return result


@pytest.fixture
def analyzer():
    return MayorAnalyzer(min_cycles=3, min_avg_increase_pct=50.0, min_profit=100_000)


def test_item_with_strong_diana_correlation_detected(analyzer):
    history = make_history(base=80_000, spikes_at=list(range(0, 93, 31)), spike_mult=3.0, days=180)
    cycles = [
        MayorCycle(mayor="Diana", start_day=0, end_day=30),
        MayorCycle(mayor="Diana", start_day=31, end_day=61),
        MayorCycle(mayor="Diana", start_day=62, end_day=92),
    ]
    results = analyzer.analyze_item("GRIFFIN_FEATHER", "Griffin Feather", history, cycles, current_mayor="Diana")
    assert results is not None
    assert results.confidence in ("high", "medium")


def test_item_with_insufficient_cycles_returns_none(analyzer):
    history = make_history(base=80_000, spikes_at=[0, 31], spike_mult=2.0, days=180)
    cycles = [
        MayorCycle(mayor="Diana", start_day=0, end_day=30),
        MayorCycle(mayor="Diana", start_day=31, end_day=61),
    ]
    results = analyzer.analyze_item("ITEM", "Item", history, cycles, current_mayor="Diana")
    assert results is None


def test_item_with_weak_correlation_ignored(analyzer):
    history = make_history(base=80_000, spikes_at=[], spike_mult=1.0, days=180)
    cycles = [
        MayorCycle(mayor="Diana", start_day=0, end_day=30),
        MayorCycle(mayor="Diana", start_day=31, end_day=61),
        MayorCycle(mayor="Diana", start_day=62, end_day=92),
    ]
    results = analyzer.analyze_item("FLAT_ITEM", "Flat Item", history, cycles, current_mayor="Diana")
    assert results is None


def test_wrong_mayor_not_reported(analyzer):
    history = make_history(base=80_000, spikes_at=list(range(0, 93, 31)), spike_mult=3.0, days=180)
    cycles = [
        MayorCycle(mayor="Diana", start_day=0, end_day=30),
        MayorCycle(mayor="Diana", start_day=31, end_day=61),
        MayorCycle(mayor="Diana", start_day=62, end_day=92),
    ]
    results = analyzer.analyze_item("GRIFFIN_FEATHER", "Griffin Feather", history, cycles, current_mayor="Technoblade")
    assert results is None
