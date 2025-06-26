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
