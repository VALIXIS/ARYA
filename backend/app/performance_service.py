"""
performance_service.py
----------------------
Small timing and reporting helpers for ARYA chat performance.
"""

import logging
import time
from collections import defaultdict, deque

logger = logging.getLogger("arya.performance")
logging.basicConfig(level=logging.INFO)

_timings = defaultdict(lambda: deque(maxlen=50))


def start_timer() -> float:
    """Start a high-resolution timer."""
    return time.perf_counter()


def elapsed_ms(start_time: float) -> float:
    """Return elapsed time in milliseconds."""
    return (time.perf_counter() - start_time) * 1000


def log_timing(name: str, duration_ms: float) -> None:
    """Store a timing measurement for the performance report."""
    _timings[name].append(duration_ms)


def log_perf(label: str, duration_ms: float | None = None) -> None:
    """Log a [PERF] timing line or point-in-time event."""
    if duration_ms is None:
        logger.info("[PERF] %s", label)
        return

    logger.info("[PERF] %s: %.0f ms", label, duration_ms)


def log_event(name: str) -> None:
    """Log a point-in-time performance event."""
    log_perf(name)


def get_report() -> dict:
    """Return a compact performance report."""
    def avg(name: str) -> float:
        samples = _timings.get(name, [])
        return round(sum(samples) / len(samples), 2) if samples else 0.0

    return {
        "Average AI time": avg("ai_response"),
        "Average memory time": avg("memory_retrieval"),
        "Average context time": avg("context_resolution"),
        "Average total request time": avg("total_response"),
    }
