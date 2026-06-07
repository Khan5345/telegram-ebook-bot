"""
Persistent stats tracking for the Ebook Library Bot.

Stats are stored in stats.json next to this file. All reads and writes
are protected by a threading lock so they're safe with the bot's
single-process polling + Flask thread setup.
"""

import json
import os
import threading

STATS_FILE = os.path.join(os.path.dirname(__file__), "stats.json")
_lock = threading.Lock()


def _load() -> dict:
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"user_ids": [], "downloads": 0, "stars_earned": 0}


def _save(data: dict) -> None:
    with open(STATS_FILE, "w") as f:
        json.dump(data, f)


def record_user(user_id: int) -> None:
    """Track a unique user who sent /start."""
    with _lock:
        data = _load()
        if user_id not in data["user_ids"]:
            data["user_ids"].append(user_id)
            _save(data)


def record_download() -> None:
    """Increment the download counter (free or paid)."""
    with _lock:
        data = _load()
        data["downloads"] += 1
        _save(data)


def record_purchase(stars: int) -> None:
    """Record a completed Stars payment and count the download."""
    with _lock:
        data = _load()
        data["downloads"] += 1
        data["stars_earned"] += stars
        _save(data)


def get_stats() -> dict:
    """Return a snapshot of current stats."""
    with _lock:
        data = _load()
    return {
        "unique_users": len(data["user_ids"]),
        "downloads": data["downloads"],
        "stars_earned": data["stars_earned"],
    }
