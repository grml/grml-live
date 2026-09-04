import contextlib
import datetime
import time

from . import logkit


@contextlib.contextmanager
def log_elapsed_time(label: str):
    start = time.monotonic()
    try:
        yield
    finally:
        logkit.info(f"{label} took {datetime.timedelta(seconds=round(time.monotonic() - start))}")
