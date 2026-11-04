import json
from pathlib import Path

d = json.loads(Path('data/timeline.json').read_text())
lines = [
    '# Unified chronological timeline',
    '',
    'Records are kept in the source timeline order. Approximate or unknown dates are preserved exactly as supplied by the source.',
    'Each record retains any source book/chapter citations exposed by the Fandom timeline.',
    '',
]
last = None
for r in d['records']:
    if r['section'] != last:
        lines += [f"## {r['section']}", '']
        last = r['section']
    meta = ' · '.join(x for x in [r['era_label'], r['time'], r['date']] if x)
    lines += [f"### {meta or 'Undated event'}", '', r['event'], '']
    if r.get('novel_citations'):
        cites = ', '.join(f"Book {c['book']}, chapter {c['chapter']}" for c in r['novel_citations'])
        lines += [f"Novel citation: {cites}", '']
    lines += [f"Source: [{r['source_template']}]({r['source_template']})", '']
Path('data/timeline.md').write_text('\n'.join(lines), encoding='utf-8')
print(f"wrote {len(d['records'])} records")
