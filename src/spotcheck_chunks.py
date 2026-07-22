#!/usr/bin/env python
import json
from pathlib import Path

# Config
PROJECT_ROOT = Path(__file__).resolve().parent.parent
input_path = PROJECT_ROOT / "data" / "chunks" / "chunks.jsonl"
output_jsonl = PROJECT_ROOT / "data" / "chunks" / "spotcheck.jsonl"
output_json = PROJECT_ROOT / "data" / "chunks" / "spotcheck.json"

# Sources to include in the spot-check
sources_to_sample = {
    "ai-attacks-small.md": 3,
    "ai-attacks-medium.md": 3,
    "ai-attacks-large.md": 3,
    "ai-small-business.md": 3,
    "agentic-ai-adoption.md": 3,
    "ai-data-security.md": 3,
    "engaging-with-ai.md": 3,
}

def main():
    # Track how many chunks we've taken per source_file
    counts = {src: 0 for src in sources_to_sample}
    sampled_rows = []

    # Read JSONL line by line
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip malformed lines

            src_file = row.get("source_file")
            if src_file not in sources_to_sample:
                continue

            # Check if we still want more from this source
            if counts[src_file] < sources_to_sample[src_file]:
                sampled_rows.append(row)
                counts[src_file] += 1

            # Stop early if we've filled all quotas
            if all(counts[s] >= sources_to_sample[s] for s in sources_to_sample):
                break

    # Write JSONL output
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as f_out:
        for row in sampled_rows:
            f_out.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Write JSON array output
    with output_json.open("w", encoding="utf-8") as f_out_json:
        json.dump(sampled_rows, f_out_json, indent=2, ensure_ascii=False)

    print(f"Wrote {len(sampled_rows)} sampled chunks to:")
    print(f"  - {output_jsonl}")
    print(f"  - {output_json}")

if __name__ == "__main__":
    main()