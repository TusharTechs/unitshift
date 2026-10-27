import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from .config import ROOT

_lock = threading.Lock()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def receipt(run_id, kind, details):
    folder = ROOT / '.state/runs'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (run_id + '.jsonl')
    with _lock:
        previous = '0' * 64
        if path.exists():
            lines = path.read_text().splitlines()
            if lines:
                previous = json.loads(lines[-1])['hash']
        record = {'at': datetime.now(timezone.utc).isoformat(), 'run_id': run_id, 'kind': kind,
                  'details': details, 'previous_hash': previous}
        record['hash'] = digest(record)
        with path.open('a') as f:
            f.write(json.dumps(record, default=str) + '\n')
    return record

def load_receipts(run_id):
    path = ROOT / '.state/runs' / (run_id + '.jsonl')
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
