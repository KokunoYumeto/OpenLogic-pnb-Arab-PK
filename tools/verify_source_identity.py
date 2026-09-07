"""Verify frozen source, current repaired translation and reader identities.

Historical target hashes remain valid for unchanged units. Exact repair receipts
authorize later target bytes; this verifier checks those bytes and their recorded
structural gates without promoting isolated repairs to whole-unit acceptance.
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
prefix=json.loads((REPO/'provenance/REPAIRED_PREFIX_QA.json').read_text('utf-8'))
if not prefix['valid'] or prefix['errors']:
    raise ValueError('Current repaired-prefix QA is not valid')
if prefix['semantic_blockers_unsupported_plus_needs_revision'] or prefix['semantic_unresolved_including_contentious']:
    raise ValueError('Current repaired-prefix QA retains unresolved choices')
repair_targets={}
for unit_id,row in prefix['structural_unit_checks'].items():
    if not all(row['checks'].values()):
        raise ValueError('Repaired-prefix structural failure: '+unit_id)
    repair_targets[unit_id]=(row['source_path'],row['target_sha256'],row['target_bytes'],'validated-prefix')

ext=json.loads((REPO/'provenance/EXTENSIONALITY_ADJUDICATION.json').read_text('utf-8'))
if ext['resolved_provisional'] != 14 or ext['choice_count'] != 14 or ext['semantic_acceptance']:
    raise ValueError('Extensionality adjudication scope/status mismatch')
for unit_id,row in ext['structural_unit_checks'].items():
    if not all(row['checks'].values()):
        raise ValueError('Extensionality structural failure: '+unit_id)
    # A newer full-prefix receipt takes precedence for OLP-0005.
    repair_targets.setdefault(unit_id,(row['source_path'],row['target_sha256'],row['target_bytes'],'isolated-extensionality'))

theorem=json.loads((REPO/'provenance/OLP0018_THEOREM_REPAIR.json').read_text('utf-8'))
theorem_required_true=('block_count_equal','command_multiset_equal','protected_arguments_equal','formula_order_and_content_equal','placeholder_token_multiset_equal','balanced_braces','no_forbidden_bidi_or_replacement_forms')
if (theorem['semantic_acceptance']
        or not all(theorem['formal_checks'][key] for key in theorem_required_true)
        or theorem['formal_checks']['old_wrong_phrase_occurrences'] != 0
        or theorem['formal_checks']['new_repaired_phrase_occurrences'] != 1):
    raise ValueError('OLP-0018 theorem repair scope/structure mismatch')
audit_by_id={row['unit_id']:row for row in audits['units']}
olp18=audit_by_id['OLP-0018']
repair_targets['OLP-0018']=(olp18['source_path'],theorem['artifacts']['target']['sha256'],theorem['artifacts']['target']['bytes'],'isolated-theorem-noun')

historical_exact=0
repair_exact=0
repair_kinds={}
for row in audits['units']:
    path=(REPO/'translation'/row['source_path']).resolve()
    if not path.is_relative_to(REPO/'translation'): raise ValueError('Target path escapes translation')
    current=(sha(path),path.stat().st_size)
    historical=(row['translation_sha256'],row['translation_bytes'])
    if current == historical:
        historical_exact += 1
        continue
    authorized=repair_targets.get(row['unit_id'])
    if authorized is None:
        raise ValueError('Translation changed without exact repair receipt: '+row['unit_id'])
    source_path,target_sha,target_bytes,kind=authorized
    if source_path != row['source_path'] or current != (target_sha,target_bytes):
        raise ValueError('Current target does not match exact repair receipt: '+row['unit_id'])
    repair_exact += 1
    repair_kinds[kind]=repair_kinds.get(kind,0)+1
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
candidate_qa_path=REPO/'provenance/PORTABLE_CANDIDATE_QA.json'
candidate_qa=json.loads(candidate_qa_path.read_text('utf-8'))
candidate_manifest_path=REPO/'provenance/PORTABLE_CANDIDATE_INPUTS.json'
if candidate_qa['status']!='REPRODUCED_FULL_PAGE_VISUAL_PASS_NOT_RELEASED':
    raise ValueError('Portable-candidate status mismatch')
if candidate_qa['inputs']['builder']['sha256']!=sha(REPO/'tools/build_sets_reader.py'):
    raise ValueError('Portable-candidate QA builder identity mismatch')
if candidate_qa['inputs']['manifest']['sha256']!=sha(candidate_manifest_path):
    raise ValueError('Portable-candidate QA input identity mismatch')
if candidate_qa['inputs']['english_bridge_isolations']!=len(candidate.get('english_bridge_isolations',[])) or len(candidate.get('english_bridge_isolations',[]))!=65:
    raise ValueError('Portable-candidate bridge-isolation count mismatch')
if candidate_qa['inputs']['russell_bridge_isolations']!=2 or candidate_qa['inputs']['single_variable_parenthetical_false_positives']!=0:
    raise ValueError('Portable-candidate bridge classification mismatch')
if candidate_qa['visual_review']['result']!='PASS' or candidate_qa['visual_review']['visible_defects'] or candidate_qa['visual_review']['all_pages_rendered']!=29:
    raise ValueError('Portable-candidate visual record mismatch')
if not all(candidate_qa['profiles'][profile]['all_fonts_embedded'] for profile in ('naskh','nastaliq')):
    raise ValueError('Portable-candidate embedded-font record mismatch')
if candidate_qa['scope']['release_effect'].startswith('None.') is False:
    raise ValueError('Portable-candidate QA release scope mismatch')
print(json.dumps({'source_units_verified':len(manifest),'translation_units_verified':len(audits['units']),'historical_target_bytes_verified':historical_exact,'repair_receipt_target_bytes_verified':repair_exact,'repair_receipt_kinds':repair_kinds,'validated_semantic_prefix_through':prefix['through_unit'],'isolated_repairs_do_not_accept_later_units':True,'fonts_verified':len(inputs['font_bundle_capture']),'original_assets_verified':len(inputs['assets']),'exact_reference_tex_inputs_verified':len(inputs['generated_inputs']),'portable_candidate_qa_verified':True,'portable_candidate_pages':candidate_qa['visual_review']['all_pages_rendered'],'portable_candidate_released':False,'passed':True,'limit':'Identity and recorded structural-gate verification only; semantic acceptance is limited to the prefix named above. Isolated later repairs and a successful local portable-reader layout review do not accept later units, release candidate PDFs, or establish cross-platform byte reproducibility.'},ensure_ascii=False))
