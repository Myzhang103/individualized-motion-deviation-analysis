from __future__ import annotations

from pathlib import Path


def parse_trial_spec(spec: str) -> list[int]:
    """Parse a trial specification such as '2-5,8,10'."""
    values: list[int] = []
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            start_s, end_s = part.split('-', 1)
            start, end = int(start_s), int(end_s)
            step = 1 if end >= start else -1
            values.extend(range(start, end + step, step))
        else:
            values.append(int(part))
    return values


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
