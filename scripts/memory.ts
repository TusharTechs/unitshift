import fs from 'node:fs';
import path from 'node:path';
import { HMEM } from '../vendor/hmem/src/index.ts';

const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const hmem = new HMEM({ persistDir: process.env.UNITSHIFT_MEMORY_DIR || path.resolve('.state/hmem'), actor: 'unitshift-operator' });
if (input.action === 'approve') {
  const record = hmem.add({
    content: JSON.stringify({ supplier: input.supplier, scope: input.scope, contract: input.contract }),
    type: 'factual', layer: 'long_term', confidence: 1,
    tags: ['unitshift', input.supplier, input.scope], source: 'operator-approved:' + input.run_id,
    provenance: { origin: 'user_correction', learnedAt: Date.now(), label: 'Operator-approved semantic contract', refs: [input.run_id] },
  });
  console.log(JSON.stringify({ id: record.id, ledger: hmem.ledger.history(record.id) }));
} else if (input.action === 'recall') {
  const result = hmem.query(input.supplier, { threshold: 0, topN: 50 });
  const records = result.memories.flatMap((r: any) => {
    try {
      const parsed = JSON.parse(r.memory.content);
      return parsed.supplier === input.supplier ? [{ ...parsed, id: r.memory.id, relevance: r.relevance }] : [];
    } catch { return []; }
  });
  const current = records.find((r: any) => r.scope === input.scope) || null;
  console.log(JSON.stringify({ current, stale_count: records.filter((r: any) => r.scope !== input.scope).length,
    trace: { strategy: result.trace.strategy }, engine: 'Meterless H-MEM reference' }));
} else {
  throw new Error('Unsupported memory operation');
}
