#!/usr/bin/env python3
"""Parse manually saved NDL Hourei HTML files and build amendments draft.

This script intentionally creates a conservative draft with nulls for unknown fields.
It does not fetch network resources.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MANUAL_DIR = DATA_DIR / "manual_sources" / "hourei"
OUTPUT_PATH = DATA_DIR / "amendments_draft.json"
UNRESOLVED_PATH = DATA_DIR / "logs" / "unresolved_items.json"
PARSE_LOG_PATH = DATA_DIR / "logs" / "manual_parse_log.json"

TARGETS = [
    ("jidou_teate_hou", "児童手当法", "0000061613", "jidou_teate_hou.html"),
    ("jidou_fuyou_teate_hou", "児童扶養手当法", "0000053349", "jidou_fuyou_teate_hou.html"),
    ("jidou_fuyou_teate_hou_sekourei", "児童扶養手当法施行令", "0000053370", "jidou_fuyou_teate_hou_sekourei.html"),
    ("tokubetsu_jidou_fuyou_teate_hou", "特別児童扶養手当等の支給に関する法律", "0000055859", "tokubetsu_jidou_fuyou_teate_hou.html"),
    ("tokubetsu_jidou_fuyou_teate_hou_sekourei", "特別児童扶養手当等の支給に関する法律施行令", "0000065214", "tokubetsu_jidou_fuyou_teate_hou_sekourei.html"),
]

ERA_BASE = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def html_to_text(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def convert_jp_date_to_iso(date_text: str | None) -> str | None:
    if not date_text:
        return None
    m = re.search(r"(明治|大正|昭和|平成|令和)(元|\d+)年(\d+)月(\d+)日", date_text)
    if not m:
        return None
    era, y, mo, d = m.groups()
    year = 1 if y == "元" else int(y)
    western = ERA_BASE[era] + year
    return f"{western:04d}-{int(mo):02d}-{int(d):02d}"


def extract_law_id(line: str) -> str | None:
    m = re.search(r"lawId=(\d{10})", line)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{10})\b", line)
    return m.group(1) if m else None


def parse_history_line(target_id: str, line: str, idx: int) -> dict[str, Any]:
    amendment_type = None
    for t in ("改正", "廃止", "制定", "施行"):
        if t in line:
            amendment_type = t
            break

    date_m = re.search(r"((明治|大正|昭和|平成|令和)(元|\d+)年\d+月\d+日)", line)
    promulgation_date_original = date_m.group(1) if date_m else None

    law_number = None
    num_m = re.search(r"((明治|大正|昭和|平成|令和)(元|\d+)年(?:法律|政令)第\d+号)", line)
    if num_m:
        law_number = num_m.group(1)

    name = None
    name_m = re.search(r"「([^」]+)」", line)
    if name_m:
        name = name_m.group(1)

    law_id = extract_law_id(line)
    law_url = f"https://hourei.ndl.go.jp/#/detail?lawId={law_id}" if law_id else None

    era_year = None
    kind_code = None
    num = None
    am = re.search(r"(昭和|平成|令和|大正|明治)(元|\d+)年(法律|政令)第(\d+)号", law_number or "")
    if am:
        era = am.group(1)
        y = "1" if am.group(2) == "元" else am.group(2)
        era_initial = {"明治": "M", "大正": "T", "昭和": "S", "平成": "H", "令和": "R"}[era]
        era_year = f"{era_initial}{y}"
        kind_code = "L" if am.group(3) == "法律" else "C"
        num = am.group(4)

    amendment_id = f"{target_id}__{era_year}_{kind_code}{num}" if era_year and kind_code and num else f"{target_id}__unparsed_{idx:04d}"

    return {
        "target_id": target_id,
        "amendment_id": amendment_id,
        "amendment_type": amendment_type,
        "history_text_raw": line,
        "amendment_law_name": name,
        "amendment_law_number": law_number,
        "amendment_law_id": law_id,
        "amendment_hourei_ndl_url": law_url,
        "promulgation_date_original": promulgation_date_original,
        "promulgation_date_iso": convert_jp_date_to_iso(promulgation_date_original),
        "history_note": None,
        "extraction_status": "parsed_with_gaps",
    }


def collect_history_candidates(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = []
    for ln in lines:
        if any(k in ln for k in ["改正", "廃止", "制定", "法律第", "政令第", "法令沿革"]):
            out.append(ln)
    return out


def main() -> None:
    unresolved = []
    parse_entries = []
    amendments = []

    for target_id, law_name, law_id, file_name in TARGETS:
        file_path = MANUAL_DIR / file_name
        entry = {
            "timestamp_utc": now_utc(),
            "target_id": target_id,
            "law_name": law_name,
            "law_id": law_id,
            "source_file": str(file_path.relative_to(ROOT)),
            "source_file_exists": file_path.exists(),
            "history_line_candidates": 0,
            "amendments_extracted": 0,
            "status": None,
            "notes": None,
        }

        if not file_path.exists():
            entry["status"] = "manual_source_missing"
            entry["notes"] = "Input HTML file is missing"
            unresolved.append({
                "item_id": f"unresolved_{len(unresolved)+1:03d}",
                "related_target_id": target_id,
                "related_amendment_id": None,
                "problem_type": "manual_source_missing",
                "source_url": f"https://hourei.ndl.go.jp/simple/detail?lawId={law_id}",
                "description": f"Manual source file not found: {file_name}",
                "next_action_suggestion": "指定URLをブラウザで開き、HTMLを保存して配置する。",
                "severity": "high",
            })
            parse_entries.append(entry)
            continue

        raw = file_path.read_text(encoding="utf-8", errors="ignore")
        text = html_to_text(raw)
        candidates = collect_history_candidates(text)
        entry["history_line_candidates"] = len(candidates)

        extracted_count = 0
        for i, line in enumerate(candidates, start=1):
            item = parse_history_line(target_id, line, i)
            amendments.append(item)
            extracted_count += 1
            if item["amendment_law_number"] is None and item["amendment_law_name"] is None:
                unresolved.append({
                    "item_id": f"unresolved_{len(unresolved)+1:03d}",
                    "related_target_id": target_id,
                    "related_amendment_id": item["amendment_id"],
                    "problem_type": "history_line_unparsed",
                    "source_url": f"file://{file_path}",
                    "description": f"Could not parse key fields from history line: {line[:200]}",
                    "next_action_suggestion": "手動確認で改正法名・法令番号を補う。",
                    "severity": "medium",
                })

        entry["amendments_extracted"] = extracted_count
        entry["status"] = "parsed" if extracted_count > 0 else "no_history_detected"
        if extracted_count == 0:
            unresolved.append({
                "item_id": f"unresolved_{len(unresolved)+1:03d}",
                "related_target_id": target_id,
                "related_amendment_id": None,
                "problem_type": "no_history_detected",
                "source_url": f"file://{file_path}",
                "description": "History candidates were not detected from source text.",
                "next_action_suggestion": "保存形式を確認し、テキスト抽出方法を調整する。",
                "severity": "medium",
            })

        parse_entries.append(entry)

    OUTPUT_PATH.write_text(json.dumps({
        "schema_version": "0.1.0",
        "generated_at_utc": now_utc(),
        "input_mode": "manual_saved_html",
        "source_directory": str(MANUAL_DIR.relative_to(ROOT)),
        "amendments": amendments,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    UNRESOLVED_PATH.write_text(json.dumps(unresolved, ensure_ascii=False, indent=2), encoding="utf-8")
    PARSE_LOG_PATH.write_text(json.dumps(parse_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote: {OUTPUT_PATH}")
    print(f"wrote: {UNRESOLVED_PATH}")
    print(f"wrote: {PARSE_LOG_PATH}")

TARGETS = [
    {
        "target_id": "jidou_teate_hou",
        "law_name": "児童手当法",
        "law_id": "0000061613",
        "file_name": "jidou_teate_hou.html",
    },
    {
        "target_id": "jidou_fuyou_teate_hou",
        "law_name": "児童扶養手当法",
        "law_id": "0000053349",
        "file_name": "jidou_fuyou_teate_hou.html",
    },
    {
        "target_id": "jidou_fuyou_teate_hou_sekourei",
        "law_name": "児童扶養手当法施行令",
        "law_id": "0000053370",
        "file_name": "jidou_fuyou_teate_hou_sekourei.html",
    },
    {
        "target_id": "tokubetsu_jidou_fuyou_teate_hou",
        "law_name": "特別児童扶養手当等の支給に関する法律",
        "law_id": "0000055859",
        "file_name": "tokubetsu_jidou_fuyou_teate_hou.html",
    },
    {
        "target_id": "tokubetsu_jidou_fuyou_teate_hou_sekourei",
        "law_name": "特別児童扶養手当等の支給に関する法律施行令",
        "law_id": "0000065214",
        "file_name": "tokubetsu_jidou_fuyou_teate_hou_sekourei.html",
    },
]


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def extract_history_lines(html_text: str) -> list[str]:
    plain = strip_tags(html_text)
    lines = [line.strip() for line in plain.splitlines()]
    history_like = []
    for line in lines:
        if not line:
            continue
        if any(key in line for key in ("改正", "廃止", "法令沿革", "法律第", "政令第")):
            history_like.append(line)
    return history_like


def parse_target(target: dict[str, str]) -> dict[str, Any]:
    path = MANUAL_DIR / target["file_name"]
    if not path.exists():
        return {
            "target_id": target["target_id"],
            "law_name": target["law_name"],
            "ndl_law_id": target["law_id"],
            "source_file": str(path.relative_to(ROOT)),
            "source_file_exists": False,
            "law_basic_info": {
                "law_name_in_source": None,
                "promulgation_info": None,
                "enforcement_info": None,
                "notes": None,
            },
            "history_candidates": [],
            "collection_status": "manual_source_missing",
            "verification_status": "unverified",
            "notes": "manual source file not found",
        }

    html_text = path.read_text(encoding="utf-8", errors="ignore")
    history_candidates = extract_history_lines(html_text)

    return {
        "target_id": target["target_id"],
        "law_name": target["law_name"],
        "ndl_law_id": target["law_id"],
        "source_file": str(path.relative_to(ROOT)),
        "source_file_exists": True,
        "law_basic_info": {
            "law_name_in_source": None,
            "promulgation_info": None,
            "enforcement_info": None,
            "notes": None,
        },
        "history_candidates": [
            {
                "history_text_raw": line,
                "amendment_law_name": None,
                "amendment_law_number": None,
                "amendment_law_id": None,
                "amendment_hourei_ndl_url": None,
                "amendment_type": None,
                "note": None,
                "verification_status": "unverified",
            }
            for line in history_candidates
        ],
        "collection_status": "draft_extracted",
        "verification_status": "unverified",
        "notes": None,
    }


def main() -> None:
    result = {
        "schema_version": "0.1.0",
        "generated_by": "parse_manual_hourei.py",
        "input_mode": "manual_saved_html",
        "source_directory": str(MANUAL_DIR.relative_to(ROOT)),
        "targets": [parse_target(t) for t in TARGETS],
    }
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
