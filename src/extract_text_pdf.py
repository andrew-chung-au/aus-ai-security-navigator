from pathlib import Path
from pypdf import PdfReader
import re
import sys


def clean_text(text: str) -> str:
    text = text.replace('\u00a0', ' ')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    parts = []

    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = clean_text(text)

        if not text:
            continue

        parts.append(f"# Page {i}\n\n{text}")

    return "\n\n".join(parts).strip()


def main():
    if len(sys.argv) < 2:
        print('Usage: python src/extract_pdfs.py <pdf-file-or-directory>')
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f'Input path does not exist: {src}')
        sys.exit(1)

    files = [src] if src.is_file() else sorted(src.rglob('*.pdf'))

    BASE_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = BASE_DIR.parent
    out_dir = PROJECT_ROOT / 'data' / 'processed'
    out_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        text = extract_pdf(file)
        out_path = out_dir / f'{file.stem}.md'
        out_path.write_text(text, encoding='utf-8')
        print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()