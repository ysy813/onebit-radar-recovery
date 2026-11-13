"""Retrieve bibliographic metadata only; never infer model validation from it."""
from pathlib import Path
import concurrent.futures
import json
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
QUERIES = [
    'A Convolutional De-quantization Network for Harmonics Suppression in One-bit SAR Imaging',
    'The Bussgang Decomposition of Nonlinear Systems Basic Theory and MIMO Extensions',
    'The spectrum of clipped noise',
]


def fetch(query):
    url = 'https://api.crossref.org/works?' + urllib.parse.urlencode({'query.title': query, 'rows': 1})
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SARNetworkTeaching/1.0'})
        with urllib.request.urlopen(req, timeout=18) as response:
            item = json.load(response)['message']['items'][0]
        return dict(query=query, status='METADATA_RETRIEVED',
                    **{key: item.get(key) for key in ['title', 'DOI', 'author', 'published', 'URL', 'container-title', 'abstract']})
    except Exception as exc:
        return dict(query=query, status='UNAVAILABLE', error=str(exc))


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(fetch, QUERIES))
    path = ROOT / 'references/crossref_metadata.json'
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(rows, ensure_ascii=False, indent=2))
