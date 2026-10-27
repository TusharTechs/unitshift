from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent.parent

def config():
    values = {}
    path = ROOT / '.env.local'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('\"\'')
    values.update({k: v for k, v in os.environ.items() if k in values or k.startswith(('UNITSHIFT_','ZETARIS_','NEBIUS_','NIGHTSHIFT_')) or k in ('DATA_BACKEND','NEMOTRON_MODEL')})
    return values

def status():
    c = config()
    return {
        'zetaris': bool(c.get('ZETARIS_API_KEY') and c.get('ZETARIS_ORG_ID')),
        'nebius': bool(c.get('NEBIUS_API_KEY') and c.get('NEMOTRON_MODEL')),
        'nightshift': bool(c.get('NIGHTSHIFT_BASE_URL') and c.get('NIGHTSHIFT_MODEL') and c.get('NIGHTSHIFT_API_KEY')),
        'hmem': (ROOT / 'vendor/hmem/src/index.ts').exists(),
        'model': c.get('NEMOTRON_MODEL', ''),
        'data_backend': c.get('DATA_BACKEND','local'),
    }
