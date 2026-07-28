"""
Extract DEI keyword measures from raw proxy statement text in batch JSONL files.

Reads batch input files from R2 one at a time, counts keyword occurrences,
and saves results to proxy_dei_keywords.csv.
"""
import sys
import os
import json
import re
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import pandas as pd
from shared.r2 import _get_s3_client, _R2_BUCKET, upload_to_r2
from shared.paths import data_dir

# ---------------------------------------------------------------------------
# Keyword patterns (compiled, case-insensitive, whole-word)
# ---------------------------------------------------------------------------
DEI_WORDS = re.compile(
    r'\b(?:diversity|diverse|inclusion|inclusive|equity|equitable|dei)\b',
    re.IGNORECASE
)

GENDER_WORDS = re.compile(
    r'\b(?:gender|women|woman|female|girls)\b',
    re.IGNORECASE
)

WORKFORCE_DEI_WORDS = re.compile(
    r'\b(?:retention|pipeline|recruit|hire|hiring|talent|'
    r'workforce\s+diversity|pay\s+equity|pay\s+gap|'
    r'parental\s+leave|family\s+leave|mentoring|sponsorship)\b',
    re.IGNORECASE
)

# Any DEI-related keyword (union of all above, for paragraph detection)
ANY_DEI = re.compile(
    r'\b(?:diversity|diverse|inclusion|inclusive|equity|equitable|dei|'
    r'gender|women|woman|female|girls|'
    r'retention|pipeline|recruit|hire|hiring|talent|'
    r'mentoring|sponsorship)\b|'
    r'\b(?:workforce\s+diversity|pay\s+equity|pay\s+gap|'
    r'parental\s+leave|family\s+leave)\b',
    re.IGNORECASE
)

# Separator between prompt instructions and proxy text
PROXY_SEPARATOR = '. Here is the content from the proxy statement: '


def extract_proxy_text(full_text: str) -> str:
    """Extract just the proxy statement text, stripping the LLM prompt."""
    idx = full_text.find(PROXY_SEPARATOR)
    if idx >= 0:
        return full_text[idx + len(PROXY_SEPARATOR):]
    # Fallback: if separator not found, use everything after first 4000 chars
    # (prompt is ~4500 chars, proxy text starts after)
    return full_text[4000:]


def compute_measures(text: str) -> dict:
    """Compute all DEI keyword measures for a proxy statement."""
    dei_count = len(DEI_WORDS.findall(text))
    gender_count = len(GENDER_WORDS.findall(text))
    workforce_count = len(WORKFORCE_DEI_WORDS.findall(text))

    # Split into paragraphs (double newline or similar)
    paragraphs = re.split(r'\n\s*\n', text)

    dei_char_length = 0
    dei_section_count = 0
    for para in paragraphs:
        if ANY_DEI.search(para):
            dei_char_length += len(para)
            dei_section_count += 1

    return {
        'dei_word_count': dei_count,
        'gender_word_count': gender_count,
        'dei_char_length': dei_char_length,
        'dei_section_count': dei_section_count,
        'workforce_dei_count': workforce_count,
        'total_doc_length': len(text),
    }


def process_jsonl_streaming(s3_client, key: str, seen: set) -> list:
    """Process a single JSONL file from R2, streaming line by line."""
    resp = s3_client.get_object(Bucket=_R2_BUCKET, Key=key)
    body = resp['Body']

    results = []
    buffer = b''
    for chunk in body.iter_lines():
        line = chunk.decode('utf-8', errors='replace').strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        accession = obj.get('custom_id', '')
        if not accession or accession in seen:
            continue
        seen.add(accession)

        # Extract text
        try:
            full_text = obj['request']['contents'][0]['parts'][0]['text']
        except (KeyError, IndexError):
            continue

        proxy_text = extract_proxy_text(full_text)
        measures = compute_measures(proxy_text)
        measures['accession_number'] = accession
        results.append(measures)

    return results


def process_jsonl_manual(s3_client, key: str, seen: set) -> list:
    """Process a JSONL file by downloading fully and splitting lines."""
    resp = s3_client.get_object(Bucket=_R2_BUCKET, Key=key)
    raw = resp['Body'].read()
    text_data = raw.decode('utf-8', errors='replace')
    del raw  # free memory

    results = []
    for line in text_data.split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        accession = obj.get('custom_id', '')
        if not accession or accession in seen:
            continue
        seen.add(accession)

        try:
            full_text = obj['request']['contents'][0]['parts'][0]['text']
        except (KeyError, IndexError):
            continue

        proxy_text = extract_proxy_text(full_text)
        measures = compute_measures(proxy_text)
        measures['accession_number'] = accession
        results.append(measures)

    return results


def main():
    s3 = _get_s3_client()

    # List all batch input files
    prefix = 'Data/proxy statements/batch_jobs/batches_'
    keys = []
    continuation_token = None
    while True:
        kwargs = {'Bucket': _R2_BUCKET, 'Prefix': prefix, 'MaxKeys': 1000}
        if continuation_token:
            kwargs['ContinuationToken'] = continuation_token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get('Contents', []):
            if obj['Key'].endswith('.jsonl'):
                keys.append(obj['Key'])
        if resp.get('IsTruncated'):
            continuation_token = resp['NextContinuationToken']
        else:
            break

    print(f'Found {len(keys)} batch JSONL files')

    seen = set()
    all_results = []

    for i, key in enumerate(sorted(keys)):
        fname = key.split('/')[-1]
        print(f'[{i+1}/{len(keys)}] Processing {fname}...', end=' ', flush=True)

        try:
            results = process_jsonl_manual(s3, key, seen)
            all_results.extend(results)
            print(f'{len(results)} new proxies (total: {len(all_results)})')
        except Exception as e:
            print(f'ERROR: {e}')
            continue

    print(f'\nTotal unique proxies: {len(all_results)}')

    # Build DataFrame and save
    df = pd.DataFrame(all_results)
    cols = ['accession_number', 'dei_word_count', 'gender_word_count',
            'dei_char_length', 'dei_section_count', 'workforce_dei_count',
            'total_doc_length']
    df = df[cols]

    outdir = os.path.join(data_dir, 'proxy statements')
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, 'proxy_dei_keywords.csv')
    df.to_csv(outpath, index=False)
    print(f'Saved to {outpath} ({len(df)} rows)')

    # Upload to R2
    upload_to_r2('proxy statements/proxy_dei_keywords.csv')

    # --- Verification ---
    print('\n=== Verification ===')

    # Summary stats
    print('\nOverall summary:')
    print(df.describe().round(1))

    # Merge with existing data
    existing_path = os.path.join(data_dir, 'proxy statements',
                                  'combined proxy statement data.CSV')
    if not os.path.exists(existing_path):
        from shared.r2 import ensure_data_file
        ensure_data_file('proxy statements/combined proxy statement data.CSV')

    existing = pd.read_csv(existing_path, low_memory=False)
    print(f'\nExisting CSV: {len(existing)} rows')

    merged = existing.merge(df, on='accession_number', how='inner')
    print(f'Merged: {len(merged)} rows (inner join)')

    # Year-level stats
    if 'fiscal_year_end' in merged.columns:
        yr_col = 'fiscal_year_end'
    elif 'year' in merged.columns:
        yr_col = 'year'
    else:
        yr_col = None

    if yr_col:
        merged['_year'] = pd.to_datetime(merged[yr_col], errors='coerce').dt.year
        yearly = merged.groupby('_year')[
            ['dei_word_count', 'gender_word_count', 'dei_char_length',
             'dei_section_count', 'workforce_dei_count']
        ].mean().round(1)
        print(f'\nMean keyword counts by year:')
        print(yearly.to_string())

    # Correlation with existing binary measure
    if 'general_dei_present' in merged.columns:
        dei_binary = merged['general_dei_present'].astype(float)
        corr = dei_binary.corr(merged['dei_word_count'].astype(float))
        print(f'\nCorrelation of dei_word_count with general_dei_present: {corr:.3f}')

        # Mean keyword count by binary flag
        print('\nMean dei_word_count by general_dei_present:')
        print(merged.groupby('general_dei_present')['dei_word_count'].describe().round(1))

    # Spot check: highest dei_word_count
    print('\n=== Spot check: Top 5 by dei_word_count ===')
    top5 = df.nlargest(5, 'dei_word_count')
    for _, row in top5.iterrows():
        print(f"  {row['accession_number']}: dei={row['dei_word_count']}, "
              f"gender={row['gender_word_count']}, "
              f"workforce={row['workforce_dei_count']}, "
              f"doc_len={row['total_doc_length']}")


if __name__ == '__main__':
    main()
