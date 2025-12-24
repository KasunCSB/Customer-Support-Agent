"""Build a normalized KB file for ingestion.

Reads JSONL files from `data/raw/lankatel/` and writes a single
`data/processed/lankatel/kb.jsonl` with a consistent `text` field.

Why:
- Improves retrieval quality (FAQ entries embed Question+Answer)
- Keeps raw data unchanged (processed data is reproducible)

Usage:
  python scripts/build_processed_kb.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable


RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "lankatel"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed" / "lankatel"
OUT_FILE = OUT_DIR / "kb.jsonl"


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def to_text(item: Dict[str, Any]) -> str | None:
    def _as_lines(prefix: str, values: list[str]) -> str:
        cleaned = [v.strip() for v in values if isinstance(v, str) and v.strip()]
        if not cleaned:
            return ""
        return prefix + "\n" + "\n".join(f"- {v}" for v in cleaned)

    # 1) Direct text fields
    text = item.get("text") or item.get("content") or item.get("body")
    if isinstance(text, str) and text.strip():
        header: list[str] = []
        for k in ("topic", "name", "title"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                header.append(f"{k.capitalize()}: {v.strip()}")
        return ("\n".join(header) + ("\n\n" if header else "") + text.strip()).strip()

    # 2) FAQ style
    q = item.get("question")
    a = item.get("answer")
    if isinstance(q, str) or isinstance(a, str):
        q_s = (q or "").strip() if isinstance(q, str) else ""
        a_s = (a or "").strip() if isinstance(a, str) else ""
        if q_s or a_s:
            return f"Question: {q_s}\n\nAnswer: {a_s}".strip()

    # 3) Common structured knowledge schemas
    description = item.get("description")
    if isinstance(description, str) and description.strip():
        header: list[str] = []
        for k in ("topic", "name", "service_id", "package_id", "channel", "category"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                header.append(f"{k.replace('_', ' ').title()}: {v.strip()}")
            elif isinstance(v, (int, float, bool)):
                header.append(f"{k.replace('_', ' ').title()}: {v}")
        return ("\n".join(header) + ("\n\n" if header else "") + description.strip()).strip()

    scenario = item.get("scenario")
    resolution = item.get("resolution")
    if isinstance(scenario, str) or isinstance(resolution, str):
        s = scenario.strip() if isinstance(scenario, str) else ""
        r = resolution.strip() if isinstance(resolution, str) else ""
        topic = item.get("topic")
        t = topic.strip() if isinstance(topic, str) else ""
        parts: list[str] = []
        if t:
            parts.append(f"Topic: {t}")
        if s:
            parts.append(f"Scenario: {s}")
        if r:
            parts.append(f"Resolution: {r}")
        if parts:
            return "\n\n".join(parts).strip()

    variants = item.get("variants")
    if isinstance(variants, list):
        block = _as_lines("Variants:", [str(v) for v in variants])
        key = item.get("key")
        k = key.strip() if isinstance(key, str) else ""
        if block:
            return (f"Message Key: {k}\n\n{block}" if k else block).strip()

    messages = item.get("messages")
    if isinstance(messages, list) and messages:
        lines: list[str] = []
        for m in messages:
            if not isinstance(m, dict):
                continue
            role = m.get("role")
            content = m.get("content")
            if isinstance(role, str) and isinstance(content, str) and content.strip():
                lines.append(f"{role.strip()}: {content.strip()}")
        if lines:
            return "\n".join(lines).strip()

    # 4) Generic fallback: flatten primitives into key: value lines
    pairs: list[str] = []
    for k, v in item.items():
        if k in {"id", "source", "index"}:
            continue
        if v is None:
            continue
        if isinstance(v, str) and v.strip():
            pairs.append(f"{k.replace('_', ' ').title()}: {v.strip()}")
        elif isinstance(v, (int, float, bool)):
            pairs.append(f"{k.replace('_', ' ').title()}: {v}")
        elif isinstance(v, list) and v:
            simple = [str(x).strip() for x in v if str(x).strip()]
            if simple:
                pairs.append(f"{k.replace('_', ' ').title()}: {', '.join(simple)}")

    return "\n".join(pairs).strip() if pairs else None


def normalize_record(source_file: str, index: int, item: Dict[str, Any]) -> Dict[str, Any] | None:
    text = to_text(item)
    if not text:
        return None

    out: Dict[str, Any] = {
        "id": item.get("id") or f"{Path(source_file).stem}_{index:06d}",
        "text": text,
        "source": source_file,
    }

    # Keep common metadata fields as top-level primitives (DocumentLoader will capture them).
    for key in ("category", "topic"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()

    tags = item.get("tags")
    if isinstance(tags, list):
        tags_str = ",".join(str(t).strip() for t in tags if str(t).strip())
        if tags_str:
            out["tags"] = tags_str

    # Preserve any other primitive metadata fields
    for k, v in item.items():
        if k in out or k in {"text", "content", "body", "question", "answer", "tags"}:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v

    return out


def main() -> None:
    if not RAW_DIR.exists():
        raise SystemExit(f"Raw directory not found: {RAW_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in RAW_DIR.glob("*.jsonl") if p.is_file())
    if not files:
        raise SystemExit(f"No .jsonl files found in {RAW_DIR}")

    written = 0
    scanned_files = 0
    per_file_written: dict[str, int] = {}
    skipped_invalid_json = 0
    skipped_no_text = 0
    with OUT_FILE.open("w", encoding="utf-8") as out:
        for path in files:
            scanned_files += 1
            file_written = 0
            with path.open("r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        skipped_invalid_json += 1
                        continue
                    rec = normalize_record(path.name, i, item)
                    if not rec:
                        skipped_no_text += 1
                        continue
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    written += 1
                    file_written += 1

            per_file_written[path.name] = file_written

    print(f"Wrote {written} records to {OUT_FILE}")
    print(f"Scanned {scanned_files} JSONL files from {RAW_DIR}")

    zero_files = [name for name, n in per_file_written.items() if n == 0]
    if zero_files:
        preview = ", ".join(zero_files[:8])
        suffix = "" if len(zero_files) <= 8 else f" (+{len(zero_files) - 8} more)"
        print(
            "Files with 0 KB records (no text/content/body or question/answer fields): "
            f"{preview}{suffix}"
        )

    if skipped_invalid_json or skipped_no_text:
        parts = []
        if skipped_invalid_json:
            parts.append(f"{skipped_invalid_json} invalid JSON lines")
        if skipped_no_text:
            parts.append(f"{skipped_no_text} lines without supported text fields")
        print("Skipped: " + ", ".join(parts))


if __name__ == "__main__":
    main()
