import threading
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def measure_peak_rss_bytes(
    fn: Callable[[], T], *, sample_interval_seconds: float = 0.005
) -> tuple[T, int | None]:
    """
    Measure approximate peak RSS (process resident set size) while running fn.

    Returns (result, peak_rss_bytes). If psutil isn't available, peak is None.
    """
    try:
        import psutil  # type: ignore[import-not-found]
    except Exception:
        return fn(), None

    proc = psutil.Process()
    peak = {"rss": proc.memory_info().rss}
    stop = threading.Event()

    def _sampler() -> None:
        while not stop.is_set():
            try:
                rss = proc.memory_info().rss
                if rss > peak["rss"]:
                    peak["rss"] = rss
            except Exception:
                pass
            time.sleep(sample_interval_seconds)

    t = threading.Thread(target=_sampler, daemon=True)
    t.start()
    try:
        result = fn()
    finally:
        stop.set()
        t.join(timeout=1.0)

    return result, int(peak["rss"])
