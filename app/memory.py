import json
import subprocess
import threading
from .config import ROOT

_lock = threading.Lock()

def memory_call(payload):
    with _lock:
        result = subprocess.run(['node', str(ROOT/'node_modules/tsx/dist/cli.mjs'), 'scripts/memory.ts'],
                                cwd=ROOT, input=json.dumps(payload), text=True, capture_output=True, timeout=20)
    if result.returncode:
        raise RuntimeError('H-MEM operation failed. Run npm install and npm run setup:memory.')
    return json.loads(result.stdout)
