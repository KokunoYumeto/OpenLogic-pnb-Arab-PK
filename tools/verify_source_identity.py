"""Verify frozen source, reviewed translation and bundled-font identities.

This does not certify new translations or replace semantic/visual review.
Uses only Python's standard library. No writes, network or TeX launch.
"""
import hashlib
import json
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
manifest=[json.loads(line) for line in (REPO/'provenance/SOURCE_MANIFEST.jsonl').read_text('utf-8-sig').splitlines()]
for row in manifest:
    path=(REPO/'upstream'/row['source_path']).resolve()
    if not path.is_relative_to(REPO/'upstream'): raise ValueError('Source path escapes upstream')
    if sha(path)!=row['source_sha256'] or path.stat().st_size!=row['source_bytes']:
        raise ValueError('Source mismatch: '+row['unit_id'])
audits=json.loads((REPO/'provenance/ALL_TRANSLATION_AUDITS.json').read_text('utf-8'))
for row in audits['units']:
    path=(REPO/'translation'/row['source_path']).resolve()
    if not path.is_relative_to(REPO/'translation'): raise ValueError('Target path escapes translation')
    if sha(path)!=row['translation_sha256'] or path.stat().st_size!=row['translation_bytes']:
        raise ValueError('Reviewed translation changed: '+row['unit_id'])
inputs=json.loads((REPO/'provenance/READER_INPUTS.json').read_text('utf-8'))
for row in inputs['font_bundle_capture']:
    if sha(REPO/'fonts'/row['file'])!=row['sha256']:
        raise ValueError('Font mismatch: '+row['file'])
for row in inputs['assets']:
    if sha(REPO/'upstream'/row['source_path'])!=row['sha256']:
        raise ValueError('Asset mismatch: '+row['source_path'])
for row in inputs['generated_inputs']:
    if sha(REPO/row['file'])!=row['sha256']:
        raise ValueError('Exact accepted TeX input changed')
candidate=json.loads((REPO/'provenance/PORTABLE_CANDIDATE_INPUTS.json').read_text('utf-8'))
if sha(REPO/'reader/sets-preamble.tex')!=candidate['preamble_sha256']:
    raise ValueError('Candidate preamble changed since recorded input generation')
if sha(REPO/'tools/build_sets_reader.py')!=candidate['builder_sha256']:
    raise ValueError('Candidate builder changed since recorded input generation')
print(json.dumps({'source_units_verified':len(manifest),'reviewed_translation_units_verified':len(audits['units']),'fonts_verified':len(inputs['font_bundle_capture']),'original_assets_verified':len(inputs['assets']),'exact_reference_tex_inputs_verified':len(inputs['generated_inputs']),'passed':True,'limit':'Identity verification only; portable candidate remains unbuilt and no new semantic or visual acceptance is implied.'}))
