from pathlib import Path
from bs4 import BeautifulSoup, Tag
import re
import sys

CONTENT_SELECTORS = [
    'main',
    'article',
    '[role="main"]',
    '.content',
    '.region-content',
    '.node__content',
]

DROP_SELECTORS = [
    'script', 'style', 'noscript', 'svg', 'form', 'nav', 'header', 'footer', 'aside',
    '.breadcrumb', '.breadcrumbs', '.skip-link', '.visually-hidden', '.sr-only'
]

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def find_content_root(soup: BeautifulSoup) -> Tag:
    for sel in CONTENT_SELECTORS:
        node = soup.select_one(sel)
        if node:
            return node
    return soup.body or soup

def drop_noise(root: Tag) -> None:
    for sel in DROP_SELECTORS:
        for node in root.select(sel):
            node.decompose()
    for node in root.select('[hidden], .hidden, [aria-hidden="true"]'):
        node.decompose()

def iter_blocks(root: Tag):
    for tag in root.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'tr']):
        if tag.name == 'tr':
            cells = [clean_text(c.get_text(' ', strip=True)) for c in tag.find_all(['th', 'td'])]
            cells = [c for c in cells if c]
            if cells:
                yield '- ' + ' | '.join(cells)
            continue

        text = clean_text(tag.get_text(' ', strip=True))
        if not text:
            continue

        if tag.name in ['h1', 'h2', 'h3', 'h4']:
            level = int(tag.name[1])
            yield f"{'#' * level} {text}"
        elif tag.name == 'li':
            yield f'- {text}'
        else:
            yield text

def dedupe_adjacent(lines):
    out = []
    prev = None
    for line in lines:
        if line != prev:
            out.append(line)
        prev = line
    return out

def extract_file(path: Path) -> str:
    html = path.read_text(encoding='utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')
    root = find_content_root(soup)
    drop_noise(root)
    lines = dedupe_adjacent(list(iter_blocks(root)))
    return '\n\n'.join(lines)

def main():
    if len(sys.argv) < 2:
        print('Usage: python src/extract.py <html-file-or-directory>')
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f'Input path does not exist: {src}')
        sys.exit(1)

    files = [src] if src.is_file() else sorted(src.rglob('*.html'))

    BASE_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = BASE_DIR.parent
    out_dir = PROJECT_ROOT / 'data' / 'processed'
    out_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        text = extract_file(file)
        out_path = out_dir / f'{file.stem}.md'
        out_path.write_text(text, encoding='utf-8')
        print(f'Wrote {out_path}')

if __name__ == '__main__':
    main()