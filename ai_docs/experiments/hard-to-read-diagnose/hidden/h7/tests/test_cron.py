from cron.jobs import Job, local_times


def test_daily_digest_keeps_local_time_across_spring_forward():
    job = Job("digest", "1d", "America/New_York", "2026-03-06 06:00")
    assert local_times(job, 5) == [
        "2026-03-06 06:00", "2026-03-07 06:00", "2026-03-08 06:00",
        "2026-03-09 06:00", "2026-03-10 06:00",
    ]


def test_daily_digest_keeps_local_time_across_fall_back():
    job = Job("digest", "1d", "Europe/Berlin", "2026-10-24 09:30")
    assert local_times(job, 4) == [
        "2026-10-24 09:30", "2026-10-25 09:30", "2026-10-26 09:30", "2026-10-27 09:30",
    ]


def test_short_intervals_are_elapsed_time():
    job = Job("poll", "6h", "America/New_York", "2026-03-07 18:00")
    utc = [r.isoformat() for r in __import__("cron.jobs", fromlist=["x"]).upcoming(job, 3)]
    assert utc == ["2026-03-07T23:00:00+00:00", "2026-03-08T05:00:00+00:00", "2026-03-08T11:00:00+00:00"]


def test_utc_jobs_unaffected():
    job = Job("daily", "1d", "UTC", "2026-03-06 06:00")
    assert local_times(job, 3) == ["2026-03-06 06:00", "2026-03-07 06:00", "2026-03-08 06:00"]
