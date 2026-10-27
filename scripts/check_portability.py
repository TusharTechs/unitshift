"""Integration smoke checks for the Node memory bridge and read-only SQLite paths."""
import json,os,sqlite3,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.config import ROOT
from app.memory import memory_call
from app import replay
with tempfile.TemporaryDirectory(prefix='unitshift source check ') as folder:
 root=Path(folder);file=root/'.state/public/retail.sqlite3';file.parent.mkdir(parents=True)
 with sqlite3.connect(file) as db:db.execute('CREATE TABLE example(value TEXT)');db.execute('INSERT INTO example VALUES (?)',('source ✓',))
 with patch.object(replay,'ROOT',root),replay.source_database() as db:
  assert db.execute('SELECT value FROM example').fetchone()[0]=='source ✓'
  try:db.execute("INSERT INTO example VALUES ('must fail')")
  except sqlite3.OperationalError:pass
  else:raise AssertionError('Source index must remain read-only')
 with patch.dict(os.environ,{'UNITSHIFT_MEMORY_DIR':str(root/'memory')}):
  saved=memory_call({'action':'approve','supplier':'platform-check','scope':'uci-v1','contract':{'requirement':'original invoice reference'},'run_id':'platform-check'})
  recalled=memory_call({'action':'recall','supplier':'platform-check','scope':'uci-v1'})
  stale=memory_call({'action':'recall','supplier':'platform-check','scope':'other-version'})
  assert recalled['current']['id']==saved['id'] and stale['current'] is None
 print('PASS: read-only source URI with spaces; real H-MEM approve, recall and stale-scope rejection.')
if (ROOT/'.state/public/retail.sqlite3').exists():
 with replay.source_database() as db:assert db.execute('SELECT COUNT(*) FROM lines').fetchone()[0]==541909
 assert replay.ledger('invoice:581483')['count']==1
 print('PASS: complete 541,909-line public source index and exact invoice navigation.')
