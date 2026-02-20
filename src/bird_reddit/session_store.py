"""Persist a stable device_id UUID across runs to prevent rotation detection."""

import json
import uuid
from pathlib import Path

SESSION_PATH = Path.home() / ".config" / "bird-reddit" / "session.json"

_cached = None


def _read_session():
    try:
        data = json.loads(SESSION_PATH.read_text())
        if data.get("device_id"):
            return data
    except Exception:
        pass
    return None


def _write_session(data):
    try:
        SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        SESSION_PATH.write_text(json.dumps(data, indent=2) + "\n")
    except Exception:
        pass


def get_device_id():
    global _cached
    if _cached:
        return _cached["device_id"]

    existing = _read_session()
    if existing:
        _cached = existing
        return existing["device_id"]

    fresh = {"device_id": str(uuid.uuid4()), "created_at": __import__("datetime").datetime.now().isoformat()}
    _write_session(fresh)
    _cached = fresh
    return fresh["device_id"]
