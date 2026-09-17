"""Reproducible source-only density denominator; no candidate inputs."""
import argparse
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import unicodedata
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=pathlib.Path, required=True)
parser.add_argument('--manifest', type=pathlib.Path, required=True)
parser.add_argument('--page-map', type=pathlib.Path, required=True)
parser.add_argument('--private-dir', type=pathlib.Path, required=True, help='Restricted directory for extracted source XML')
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
SOURCE_SHA = '5f89aa2592218983c594278bfd86cc1e4b74be1dd6dd8aac5c2610a48fa34047'
NS = {'x': 'http://www.w3.org/1999/xhtml'}
source = args.source
assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA
def verified_json(path, identity_key, expected_file_sha, expected_canonical_sha):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_file_sha, f'Unexpected input bytes: {path.name}'
    data = json.loads(raw)
    assert data.get(identity_key) == expected_canonical_sha
    semantic = {k: v for k, v in data.items() if k != identity_key}
    actual = hashlib.sha256(json.dumps(semantic, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    assert actual == expected_canonical_sha, f'Unexpected canonical identity: {path.name}'
    return data

manifest = verified_json(args.manifest, 'chunk_manifest_sha256',
    '5287f421e1e7be03444c2681beb1e1d63d5d103a96ab770565e32411956ce396',
    '5fc5450386114fdeb19838f54d3f1662c3d6dec81d4729c73f4f7ec0cb341a6f')
page_map = verified_json(args.page_map, 'page_map_sha256',
    'dbc3ac1a4a7ea04403639dd9f41cdf79eebf1b8486d4ff65f799d05730fc8b0d',
    '452602deebdae19f8e35c589f2ff2a7a0b9fc955d268b14f760391b0043e9653')
assert page_map['source_sha256'] == SOURCE_SHA
assert manifest['page_map_sha256'] == page_map['page_map_sha256']
args.private_dir.mkdir(parents=True, exist_ok=True)
xml = args.private_dir / 'source-bbox.xml'
subprocess.run(['pdftotext', '-bbox-layout', str(source), str(xml)], check=True)
pages = ET.parse(xml).findall('.//x:page', NS)
assert len(pages) == 425
starts = {c['owned_document_page_ranges'][0][0] for c in manifest['chunks']}
map_pages = {3, 127, 129, 225, 345}
records, cleaned = [], {}

for n, page in enumerate(pages, 1):
    lines, excluded = [], collections.Counter()
    for line in page.findall('.//x:line', NS):
        words = line.findall('x:word', NS)
        raw = ' '.join(w.text or '' for w in words)
        y = float(line.attrib['yMin'])
        reason = None
        if n in map_pages:
            # Exact caption geometry; map internals/keys and source credits stay out.
            if n == 3:
                caption = (470 < y < 481) or (482 < y < 490)
            elif n == 129:
                caption = (310 < y < 325) or (327 < y < 335)
            else:
                caption = raw.startswith('Map ')
            if not caption:
                reason = 'map_internals_key_or_source_credit'
        elif n in starts and y < (210 if n == 136 else 170):
            reason = 'chapter_display'
        elif y < 50:
            reason = 'running_furniture'
        if reason:
            excluded[reason] += len(words)
            continue
        kept = []
        for w in words:
            text = unicodedata.normalize('NFKC', w.text or '')
            height = float(w.attrib['yMax']) - float(w.attrib['yMin'])
            if text.isdigit() and height < 8 and n not in map_pages:
                excluded['superscript_note_callout'] += 1
            else:
                kept.append(text)
        text = ' '.join(kept)
        if n in map_pages:
            text = re.sub(r'^Map\s+\d+\.\s*', '', text)
        lines.append(text)
    # A line-wrap hyphen does not create an extra word. Lexical hyphens elsewhere remain.
    text = re.sub(r'(?<=[^\W\d_])[-\u00ad]\s*\n\s*(?=[^\W\d_])', '', '\n'.join(lines))
    tokens = [t for t in text.split() if any(c.isalnum() for c in t)]
    cleaned[n] = text
    records.append({'document_page': n, 'source_page_label': str(n),
                    'indexable_source_words': len(tokens),
                    'excluded_extracted_token_counts': dict(excluded),
                    'role': 'substantive_map_caption_only' if n in map_pages else 'body_and_substantive_notes'})

joins = []
for n in range(1, 425):
    # No joining across chapter boundaries or map interruptions; ownership stays on first page.
    if n + 1 in starts or n in map_pages or n + 1 in map_pages:
        continue
    if re.search(r'[^\W\d_][-\u00ad]\s*$', cleaned[n]) and re.match(r'\s*[^\W\d_]', cleaned[n + 1]):
        records[n]['indexable_source_words'] -= 1
        joins.append({'starts_on_document_page': n, 'continues_on_document_page': n + 1,
                      'word_assigned_to_document_page': n})

chunks = []
for chunk in manifest['chunks']:
    owned = [n for a, b in chunk['owned_document_page_ranges'] for n in range(a, b + 1)]
    chunks.append({'chunk_id': chunk['chunk_id'], 'owned_document_page_ranges': chunk['owned_document_page_ranges'],
                   'owned_document_pages': owned,
                   'indexable_source_words': sum(records[n-1]['indexable_source_words'] for n in owned)})
assert [n for c in chunks for n in c['owned_document_pages']] == list(range(1, 426))
assert all(r['indexable_source_words'] > 0 for r in records)
assert sum(c['indexable_source_words'] for c in chunks) == sum(r['indexable_source_words'] for r in records)
result = {
    'schema_version': 'source-density-measurement-v1',
    'status': 'computed_unregistered_measurement',
    'approval': 'This program computes measurements only; source-protocol approval, if any, is a separate artifact.',
    'measurement_id': 'ohfr-2002-uniform-body-caption-v1',
    'source_sha256': SOURCE_SHA,
    'page_map_sha256': page_map['page_map_sha256'],
    'chunk_manifest_sha256': manifest['chunk_manifest_sha256'],
    'candidate_information_used': False,
    'benchmark_selection_input': False,
    'extractor': subprocess.run(['pdftotext', '-v'], capture_output=True, text=True).stderr.splitlines()[0],
    'extraction_command_template': 'pdftotext -bbox-layout SOURCE.pdf PRIVATE/source-bbox.xml',
    'script_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
    'extraction_xml_sha256': hashlib.sha256(xml.read_bytes()).hexdigest(),
    'protocol': {
        'inclusions': ['Body prose and block quotations', 'Substantive available notes', 'Substantive map caption wording'],
        'exclusions': ['Running heads and folios: line yMin < 50 on ordinary pages',
                       'Chapter display: line yMin < 170 on chapter opening pages, except page 136 threshold 210',
                       'Map internals, numbered map key and source credit on pages 3, 127, 129, 225, 345',
                       'Map number label at caption start',
                       'Standalone numeric words of bbox height < 8 points: superscript note callouts'],
        'map_caption_lines': {'3': ['470 < line yMin < 481', '482 < line yMin < 490'],
                              '127': ['line starts Map'], '129': ['310 < line yMin < 325', '327 < line yMin < 335'],
                              '225': ['line starts Map'], '345': ['line starts Map']},
        'unicode': 'NFKC normalization before counting',
        'token': 'Whitespace-delimited unit containing at least one Unicode letter or number; retained lexical compounds count once',
        'line_wraps': 'Remove terminal hyphen followed across a line break by a letter; join across contiguous ordinary pages of the same chapter, assigning the joined word to its first page',
        'scope': 'Owned source pages only, once each; no context-page duplication or inferred absent material',
        'source_role_note': 'Maps remain eligible semantic evidence even though graphic internals are excluded from the prose density denominator',
        'limits': 'An exact extraction-based operational denominator, not a claim of linguistically unique word segmentation; spacing inherited from the PDF may separate possessives or words around em dashes.'
    },
    'cross_page_hyphen_joins': joins,
    'total_indexable_source_words': sum(c['indexable_source_words'] for c in chunks),
    'chunks': chunks,
    'pages': records,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'total': result['total_indexable_source_words'], 'chunks': [(c['chunk_id'],c['indexable_source_words']) for c in chunks], 'cross_page_joins': len(joins)}, indent=2))
