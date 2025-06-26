import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

FILTER_LAST_DAYS = 90


def validate_timestamp(timestamp):
    if not timestamp:
        return False

    if timestamp.tzinfo:
        last_days_cutoff = datetime.now(timezone.utc) - timedelta(days=FILTER_LAST_DAYS)
    else:
        last_days_cutoff = datetime.now() - timedelta(days=FILTER_LAST_DAYS)
    return timestamp > last_days_cutoff


@contextmanager
def time_log(msg, debug=False):
    start = datetime.now()

    if debug:
        sys.stdout.write(f"Start {msg}")
        sys.stdout.flush()

    try:
        yield
    except:
        raise
    finally:
        finish = datetime.now()
        if debug:
            sys.stdout.write(f"Finish {msg} in {finish - start}")
            sys.stdout.flush()
