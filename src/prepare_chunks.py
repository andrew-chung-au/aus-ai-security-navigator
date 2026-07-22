from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple


# Paths
MANIFEST_PATH = Path("data/source_manifest_core.csv")
INPUT_DIR = Path("data/processed")
OUTPUT_DIR = Path("data/chunks")
OUTPUT_PATH = OUTPUT_DIR / "chunks.jsonl"


# Match Markdown headings like "# Title", "## Section", etc.
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")

# Match top-level numbered list items like "1. Something"
NUMBERED_ITEM_RE = re.compile(r"^(\d+)\.\s+(.*\S)\s*$")


# Child headings that should be merged into their parent section
PAIR_CHILD_HEADINGS = {
    "managing risks",
    "scenario example:",
    "scenario example",
    "recommended best practices",
}


def normalize(text: str) -> str:
    """Lowercase and collapse whitespace."""
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def load_manifest(path: Path) -> Dict[str, dict]:
    """Load manifest rows keyed by source_id."""
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    by_source_id = {row["source_id"]: row for row in rows}
    return by_source_id


def parse_markdown(file_path: Path) -> Tuple[str, List[dict]]:
    """
    Parse a cleaned Markdown file into:
    - document_title (first H1 or filename stem)
    - sections: list of dicts with heading_path, heading_level, content
    """
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    document_title = None
    sections: List[dict] = []
    heading_stack: List[Tuple[int, str]] = []
    current_content: List[str] = []

    def flush_current() -> None:
        nonlocal current_content, sections, heading_stack
        content = "\n".join(current_content).strip()
        if content and heading_stack:
            sections.append(
                {
                    "heading_path": [h for _, h in heading_stack],
                    "heading_level": heading_stack[-1][0],
                    "content": content,
                }
            )
        current_content = []

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            heading_text = m.group(2).strip()

            if level == 1 and document_title is None:
                document_title = heading_text

            flush_current()

            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()

            heading_stack.append((level, heading_text))
        else:
            current_content.append(line)

    flush_current()

    if not document_title:
        document_title = file_path.stem

    return document_title, sections


def merge_sections(sections: List[dict]) -> List[dict]:
    """
    Merge certain child sections (e.g. 'Managing risks', 'Scenario example')
    into their parent section so risk+mitigation patterns stay together.
    """
    if not sections:
        return []

    merged: List[dict] = []
    i = 0

    while i < len(sections):
        current = sections[i]
        current_path = current["heading_path"][:]
        current_content = current["content"].strip()
        current_level = current["heading_level"]

        while i + 1 < len(sections):
            nxt = sections[i + 1]
            nxt_last = normalize(nxt["heading_path"][-1]) if nxt["heading_path"] else ""

            if (
                nxt_last in PAIR_CHILD_HEADINGS
                and len(nxt["heading_path"]) >= 2
                and current_path
                and nxt["heading_path"][:-1] == current_path
            ):
                current_path = nxt["heading_path"][:]
                current_content = current_content + "\n\n" + nxt["content"].strip()
                current_level = nxt["heading_level"]
                i += 1
            else:
                break

        merged.append(
            {
                "heading_path": current_path,
                "heading_level": current_level,
                "content": current_content.strip(),
            }
        )
        i += 1

    return merged


def split_numbered_items(content: str) -> List[dict]:
    """
    Split a section into:
    - optional intro text before a numbered list
    - one chunk per top-level numbered list item

    Returns a list of dicts:
    - {"type": "intro", "title": None, "content": "..."}
    - {"type": "item", "title": "1. Some title", "content": "..."}
    """
    lines = content.splitlines()

    numbered_indices = []
    for i, line in enumerate(lines):
        if NUMBERED_ITEM_RE.match(line.strip()):
            numbered_indices.append(i)

    if len(numbered_indices) < 2:
        return [{"type": "full", "title": None, "content": content.strip()}]

    chunks = []

    first_idx = numbered_indices[0]
    intro_text = "\n".join(lines[:first_idx]).strip()
    if intro_text:
        chunks.append(
            {
                "type": "intro",
                "title": None,
                "content": intro_text,
            }
        )

    for idx, start in enumerate(numbered_indices):
        end = numbered_indices[idx + 1] if idx + 1 < len(numbered_indices) else len(lines)
        block_lines = lines[start:end]
        if not block_lines:
            continue

        first_line = block_lines[0].strip()
        m = NUMBERED_ITEM_RE.match(first_line)
        if not m:
            continue

        item_title = f"{m.group(1)}. {m.group(2).strip()}"
        item_content = "\n".join(block_lines).strip()

        chunks.append(
            {
                "type": "item",
                "title": item_title,
                "content": item_content,
            }
        )

    return chunks


def section_to_chunks(section: dict) -> List[dict]:
    """
    Convert one section into one or more chunks.

    Default:
    - keep section as a single chunk

    Special handling:
    - if the section contains a top-level numbered list with 2+ items,
      split into:
        - optional intro chunk
        - one chunk per numbered item
    """
    content = section["content"].strip()
    if not content:
        return []

    numbered_parts = split_numbered_items(content)

    # No useful numbered split found
    if len(numbered_parts) == 1 and numbered_parts[0]["type"] == "full":
        return [
            {
                "heading_path": section["heading_path"],
                "content": content,
            }
        ]

    result = []
    for part in numbered_parts:
        if part["type"] == "intro":
            result.append(
                {
                    "heading_path": section["heading_path"],
                    "content": part["content"],
                }
            )
        elif part["type"] == "item":
            result.append(
                {
                    "heading_path": section["heading_path"] + [part["title"]],
                    "content": part["content"],
                }
            )

    return result


def build_chunk_text(heading_path: List[str], content: str) -> str:
    """
    Prepend the heading breadcrumb to the chunk text for better retrieval.
    Example:
      'Recommended actions > Immediate\\n\\n<content>'
    """
    breadcrumb = " > ".join(heading_path).strip()
    if breadcrumb:
        return f"{breadcrumb}\n\n{content.strip()}"
    return content.strip()


def chunk_length_metrics(chunk_text: str) -> dict:
    """
    Simple metrics so you can inspect chunk sizes in the first run.
    """
    words = len(re.findall(r"\S+", chunk_text))
    chars = len(chunk_text)
    lines = len(chunk_text.splitlines())
    return {
        "chars": chars,
        "words": words,
        "lines": lines,
    }


def main() -> None:
    manifest_by_id = load_manifest(MANIFEST_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chunk_count = 0
    smallest_chunk = None
    all_chunks = []

    with OUTPUT_PATH.open("w", encoding="utf-8") as out:
        for file_path in sorted(INPUT_DIR.glob("*.md")):
            document_title, sections = parse_markdown(file_path)

            source_id = file_path.stem
            if source_id not in manifest_by_id:
                valid_ids = sorted(manifest_by_id.keys())
                raise ValueError(
                    "\n".join([
                        f"Markdown file '{file_path.name}' does not match any manifest source_id.",
                        f"Filename stem: '{source_id}'",
                        f"Valid source_id values: {', '.join(valid_ids)}"
                    ])
                )

            manifest_row = manifest_by_id[source_id]
            audience_tag = manifest_row.get("audience_tag", "").strip()
            if not audience_tag:
                raise ValueError(f"Missing audience_tag for source_id={source_id}")

            merged_sections = merge_sections(sections)

            for section in merged_sections:
                chunk_parts = section_to_chunks(section)

                for chunk_part in chunk_parts:
                    chunk_text = build_chunk_text(
                        chunk_part["heading_path"],
                        chunk_part["content"]
                    )
                    metrics = chunk_length_metrics(chunk_text)

                    record = {
                        "source_file": file_path.name,
                        "document_title": document_title,
                        "heading_path": chunk_part["heading_path"],
                        "audience_tag": audience_tag,
                        "chunk_text": chunk_text,
                        "chunk_chars": metrics["chars"],
                        "chunk_words": metrics["words"],
                        "chunk_lines": metrics["lines"],
                    }

                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    chunk_count += 1
                    all_chunks.append(record)

                    if (
                        smallest_chunk is None
                        or record["chunk_words"] < smallest_chunk["chunk_words"]
                    ):
                        smallest_chunk = record

    print(f"Wrote {chunk_count} chunks to {OUTPUT_PATH}")

    if smallest_chunk:
        print("\nSmallest chunk by words:")
        print(f"  source_file: {smallest_chunk['source_file']}")
        print(f"  heading_path: {' > '.join(smallest_chunk['heading_path'])}")
        print(f"  words: {smallest_chunk['chunk_words']}")
        print(f"  chars: {smallest_chunk['chunk_chars']}")
        print(f"  lines: {smallest_chunk['chunk_lines']}")

    largest_chunks = sorted(
        all_chunks,
        key=lambda x: x["chunk_words"],
        reverse=True
    )[:5]

    if largest_chunks:
        print("\nTop 5 largest chunks by words:")
        for i, chunk in enumerate(largest_chunks, start=1):
            print(f"\n{i}.")
            print(f"  source_file: {chunk['source_file']}")
            print(f"  heading_path: {' > '.join(chunk['heading_path'])}")
            print(f"  words: {chunk['chunk_words']}")
            print(f"  chars: {chunk['chunk_chars']}")
            print(f"  lines: {chunk['chunk_lines']}")


if __name__ == "__main__":
    main()