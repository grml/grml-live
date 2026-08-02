import contextlib
import datetime
import time


@contextlib.contextmanager
def log_elapsed_time(label: str):
    start = time.monotonic()
    try:
        yield
    finally:
        print(f"I: {label} took {datetime.timedelta(seconds=round(time.monotonic() - start))}", flush=True)
