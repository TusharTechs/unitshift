// Resolve Python without assuming a POSIX executable name on Windows.
import { spawnSync } from 'node:child_process';
const explicit = process.env.UNITSHIFT_PYTHON;
const candidates = explicit ? [[explicit, []]] : process.platform === 'win32'
  ? [['python', []], ['py', ['-3']], ['python3', []]]
  : [['python3', []], ['python', []]];
let selected;
for (const [command, prefix] of candidates) {
  const probe = spawnSync(command, [...prefix, '-c', 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'], { stdio: 'ignore' });
  if (probe.status === 0) { selected = [command, prefix]; break; }
}
if (!selected) {
  console.error('UnitShift requires Python 3.11 or newer. Install Python and restart this terminal, or set UNITSHIFT_PYTHON to its executable path.');
  process.exit(1);
}
const [command, prefix] = selected;
const child = spawnSync(command, [...prefix, ...process.argv.slice(2)], { stdio: 'inherit', env: process.env });
if (child.error) { console.error(child.error.message); process.exit(1); }
process.exit(child.status ?? 1);
