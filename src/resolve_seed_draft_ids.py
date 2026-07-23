from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple

SEED_DRAFT_PATH = Path("data/ground_truth_seed_draft.json")
CHUNKS_PATH = Path("data/chunks/chunks.jsonl")
OUTPUT_PATH = Path("data/seed_chunk_candidates.json")


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_loose(text: str) -> str:
    text = normalize(text)
    text = re.sub(r"[“”\"'`]", "", text)
    text = re.sub(r"[^a-z0-9\s>.:-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def similarity(a: str, b: str) -> float:
    a_n = normalize_loose(a)
    b_n = normalize_loose(b)
    if not a_n or not b_n:
        return 0.0
    return SequenceMatcher(None, a_n, b_n).ratio()


def load_chunks(path: Path) -> List[dict]:
    chunks = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunks.append(json.loads(line))
    return chunks


def load_seed_draft(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def group_chunks_by_source_id(chunks: List[dict]) -> Dict[str, List[dict]]:
    grouped: Dict[str, List[dict]] = {}
    for chunk in chunks:
        source_id = chunk.get("source_id")
        if not source_id:
            source_file = chunk.get("source_file", "")
            source_id = Path(source_file).stem if source_file else None
        if not source_id:
            continue
        grouped.setdefault(source_id, []).append(chunk)

    for source_id in grouped:
        grouped[source_id] = sorted(
            grouped[source_id],
            key=lambda c: c.get("chunk_index", 10**9),
        )
    return grouped


def get_last_heading(chunk: dict) -> str:
    heading_path = chunk.get("heading_path", [])
    return heading_path[-1] if heading_path else ""


def chunk_matches_numbered_item(chunk: dict, numbered_item_title_guess: str | None) -> bool:
    if not numbered_item_title_guess:
        return False
    last_heading = get_last_heading(chunk)
    if not last_heading:
        return False
    return normalize_loose(numbered_item_title_guess) == normalize_loose(last_heading)


def score_candidate(seed: dict, chunk: dict) -> dict:
    best_heading_path_guess = seed.get("best_heading_path_guess", "") or ""
    numbered_item_title_guess = seed.get("numbered_item_title_guess")
    anchor_quote = seed.get("anchor_quote", "") or ""

    heading_path = chunk.get("heading_path", [])
    heading_path_str = " > ".join(heading_path)
    chunk_text = chunk.get("chunk_text", "")

    heading_sim = similarity(best_heading_path_guess, heading_path_str)

    guess_parts = [part.strip() for part in best_heading_path_guess.split(">") if part.strip()]
    last_heading_guess = guess_parts[-1] if guess_parts else ""
    last_heading = heading_path[-1] if heading_path else ""

    last_heading_sim = similarity(last_heading_guess, last_heading)
    last_heading_exact = False
    if last_heading_guess and last_heading:
        last_heading_exact = normalize_loose(last_heading_guess) == normalize_loose(last_heading)

    numbered_title_sim = 0.0
    numbered_exact = False
    if numbered_item_title_guess:
        numbered_title_sim = similarity(numbered_item_title_guess, last_heading)
        numbered_exact = normalize_loose(numbered_item_title_guess) == normalize_loose(last_heading)

    anchor_norm = normalize_loose(anchor_quote)
    chunk_text_norm = normalize_loose(chunk_text)

    anchor_contains = False
    anchor_sim = 0.0
    if anchor_norm and chunk_text_norm:
        anchor_contains = anchor_norm in chunk_text_norm
        if anchor_contains:
            anchor_sim = 1.0
        else:
            if len(anchor_norm) > 40:
                window = chunk_text_norm[: max(len(anchor_norm) * 3, 1200)]
                anchor_sim = similarity(anchor_norm, window)
            else:
                anchor_sim = similarity(anchor_norm, chunk_text_norm)

    score = 0.0
    score += 0.35 * heading_sim
    score += 0.20 * last_heading_sim
    score += 0.10 * (1.0 if last_heading_exact else 0.0)
    score += 0.15 * numbered_title_sim
    score += 0.05 * (1.0 if numbered_exact else 0.0)
    score += 0.15 * anchor_sim

    return {
        "heading_path_str": heading_path_str,
        "last_heading_guess": last_heading_guess,
        "last_heading": last_heading,
        "heading_sim": round(heading_sim, 4),
        "last_heading_sim": round(last_heading_sim, 4),
        "last_heading_exact": last_heading_exact,
        "numbered_item_title_guess": numbered_item_title_guess,
        "numbered_title_sim": round(numbered_title_sim, 4),
        "numbered_exact": numbered_exact,
        "anchor_contains": anchor_contains,
        "anchor_sim": round(anchor_sim, 4),
        "score": round(score, 4),
    }


def classify_candidate_selection(best_score: float, second_score: float | None) -> Tuple[str, float]:
    margin = round(best_score - second_score, 4) if second_score is not None else round(best_score, 4)

    if best_score >= 0.85 and margin >= 0.10:
        return "high", margin
    if best_score >= 0.70 and margin >= 0.05:
        return "medium", margin
    return "low", margin


def compact_candidate_chunk(chunk: dict) -> dict:
    return {
        "chunk_id": chunk.get("chunk_id"),
        "chunk_index": chunk.get("chunk_index"),
        "source_id": chunk.get("source_id"),
        "source_file": chunk.get("source_file"),
        "chunking_version": chunk.get("chunking_version"),
        "document_title": chunk.get("document_title"),
        "heading_path": chunk.get("heading_path"),
        "size_audience_tag": chunk.get("size_audience_tag"),
        "role_audience_tags": chunk.get("role_audience_tags"),
        "chunk_words": chunk.get("chunk_words"),
        "chunk_chars": chunk.get("chunk_chars"),
        "chunk_lines": chunk.get("chunk_lines"),
        "chunk_text": chunk.get("chunk_text"),
    }


def build_seed_id(seed: dict, seed_index: int) -> str:
    source_id = seed.get("source_id", f"seed-{seed_index}")
    target_size = seed.get("target_size", "unknown_size")
    target_role = seed.get("target_role", "unknown_role")
    passage_type = seed.get("passage_type", "unknown_type")
    return f"{source_id}::{target_size}::{target_role}::{passage_type}::{seed_index:03d}"


def main() -> None:
    seeds = load_seed_draft(SEED_DRAFT_PATH)
    chunks = load_chunks(CHUNKS_PATH)
    chunks_by_source_id = group_chunks_by_source_id(chunks)

    results = []
    with_candidate_chunk = 0
    no_source_count = 0

    for i, seed in enumerate(seeds):
        source_id = seed.get("source_id")
        source_chunks = chunks_by_source_id.get(source_id, [])
        seed_id = build_seed_id(seed, i)
        numbered_item_title_guess = seed.get("numbered_item_title_guess")

        if not source_chunks:
            results.append(
                {
                    "seed_id": seed_id,
                    "seed_index": i,
                    "source_id": source_id,
                    "target_size": seed.get("target_size"),
                    "target_role": seed.get("target_role"),
                    "passage_type": seed.get("passage_type"),
                    "why_this_passage": seed.get("why_this_passage"),
                    "best_heading_path_guess": seed.get("best_heading_path_guess"),
                    "numbered_item_title_guess": numbered_item_title_guess,
                    "anchor_quote": seed.get("anchor_quote"),
                    "candidate_chunk": None,
                    "candidate_debug": None,
                    "match_score": None,
                    "selection_confidence": "none",
                    "score_margin": 0.0,
                    "selection_strategy": "no_source_candidates",
                }
            )
            no_source_count += 1
            continue

        matched_numbered_chunks = []
        if numbered_item_title_guess:
            matched_numbered_chunks = [
                chunk
                for chunk in source_chunks
                if chunk_matches_numbered_item(chunk, numbered_item_title_guess)
            ]

        candidate_pool = matched_numbered_chunks if matched_numbered_chunks else source_chunks
        selection_strategy = (
            "numbered_item_exact_subset" if matched_numbered_chunks else "all_source_chunks"
        )

        scored = []
        for chunk in candidate_pool:
            debug = score_candidate(seed, chunk)
            scored.append({"chunk": chunk, "debug": debug})

        scored = sorted(scored, key=lambda x: x["debug"]["score"], reverse=True)

        top = scored[0]
        second_score = scored[1]["debug"]["score"] if len(scored) > 1 else None
        selection_confidence, score_margin = classify_candidate_selection(
            top["debug"]["score"],
            second_score,
        )

        results.append(
            {
                "seed_id": seed_id,
                "seed_index": i,
                "source_id": source_id,
                "target_size": seed.get("target_size"),
                "target_role": seed.get("target_role"),
                "passage_type": seed.get("passage_type"),
                "why_this_passage": seed.get("why_this_passage"),
                "best_heading_path_guess": seed.get("best_heading_path_guess"),
                "numbered_item_title_guess": numbered_item_title_guess,
                "anchor_quote": seed.get("anchor_quote"),
                "candidate_chunk": compact_candidate_chunk(top["chunk"]),
                "candidate_debug": top["debug"],
                "match_score": top["debug"]["score"],
                "selection_confidence": selection_confidence,
                "score_margin": score_margin,
                "selection_strategy": selection_strategy,
            }
        )
        with_candidate_chunk += 1

    with OUTPUT_PATH.open("w", encoding="utf-8") as out:
        json.dump(results, out, ensure_ascii=False, indent=2)

    print(f"Wrote seed chunk candidates to {OUTPUT_PATH}")
    print(f"With candidate chunk: {with_candidate_chunk}")
    print(f"No source candidates: {no_source_count}")


if __name__ == "__main__":
    main()