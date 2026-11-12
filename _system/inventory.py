#!/usr/bin/env python3
"""Rebuild the baseline file inventory; stdout is generated evidence, not a catalog to edit."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

paths = git('ls-tree', '-r', '--name-only', 'HEAD').splitlines()
texts = {p: (ROOT / p).read_text(errors='replace') for p in paths}
rows = []
for path in paths:
    if path in ('CLAUDE.md', 'README.md'):
        role = 'catalog'
    elif path.endswith('CONTEXT.md'):
        role = 'contract'
    elif any('/' + part + '/' in '/' + path for part in ('brews', 'decklists', 'sessions', '_cache')):
        role = 'product'
    else:
        role = 'factory'
    rows.append({'path': path, 'role': role,
                 'last_commit': git('log', '-1', '--format=%h %aI', '--', path),
                 'referenced_by': [other for other, text in texts.items() if other != path and path in text]})
print(json.dumps({'baseline_commit': git('rev-parse', 'HEAD'), 'files': rows}, indent=2))
