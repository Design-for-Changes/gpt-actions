#!/usr/bin/env python3
"""Parse manually saved NDL Hourei HTML files and build amendment events.

The script does not fetch network resources. It only reads files placed under
project/data/manual_sources/hourei and leaves missing values as null.
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
LOG_DIR = DATA_DIR / "logs"
UNRESOLVED_PATH = LOG_DIR / "unresolved_items.json"
PARSE_LOG_PATH = LOG_DIR / "manual_parse_log.json"

TARGETS = [
    {
        "target_id": "jidou_teate_hou",
        "benefit_id": "child_allowance",
        "law_name": "児童手当法",
        "law_id": "0000061613",
        "source_kind": "法律",
        "file_name": "jidou_teate_hou.html",
    },
    {
        "target_id": "jidou_fuyou_teate_hou",
        "benefit_id": "child_support",
        "law_name": "児童扶養手当法",
        "law_id": "0000053349",
        "source_kind": "法律",
        "file_name": "jidou_fuyou_teate_hou.html",
    },
    {
        "target_id": "jidou_fuyou_teate_hou_sekourei",
        "benefit_id": "child_support",
        "law_name": "児童扶養手当法施行令",
        "law_id": "0000053370",
        "source_kind": "施行令",
        "file_name": "jidou_fuyou_teate_hou_sekourei.html",
    },
    {
        "target_id": "tokubetsu_jidou_fuyou_teate_hou",
        "benefit_id": "special_child",
        "law_name": "特別児童扶養手当等の支給に関する法律",
        "law_id": "0000055859",
        "source_kind": "法律",
        "file_name": "tokubetsu_jidou_fuyou_teate_hou.html",
    },
    {
        "target_id": "tokubetsu_jidou_fuyou_teate_hou_sekourei",
        "benefit_id": "special_child",
        "law_name": "特別児童扶養手当等の支給に関する法律施行令",
        "law_id": "0000065214",
        "source_kind": "施行令",
        "file_name": "tokubetsu_jidou_fuyou_teate_hou_sekourei.html",
    },
]

ERA_BASE = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def strip_tags(value: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", value, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&#160;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return re.sub(r"\s+", " ", text).strip()


def parse_japanese_date(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"(明治|大正|昭和|平成|令和)(元|\d+)年(\d+)月(\d+)日", text)
    if not match:
        return None
    era, year_text, month, day = match.groups()
    era_year = 1 if year_text == "元" else int(year_text)
    year = ERA_BASE[era] + era_year
    return f"{year:04d}-{int(month):02d}-{int(day):02d}"


def match_field(html: str, label: str) -> str | None:
    match = re.search(rf"<span>\s*{re.escape(label)}：([\s\S]*?)</span>", html)
    if not match:
        return None
    value = strip_tags(match.group(1))
    return value or None


def split_law_number(text: str) -> tuple[str, str | None]:
    match = re.match(r"^(.+?(?:法律|政令|勅令|府令|省令|規則)第\d+号)(?:〔(.+)〕)?$", text)
    if not match:
        return text.strip(), None
    return match.group(1).strip(), match.group(2).strip() if match.group(2) else None


def extract_history_items(html: str) -> list[str]:
    section = re.search(r'<h2><a name="history"[\s\S]*?</section>', html)
    if not section:
        return []
    return re.findall(r"<li>[\s\S]*?</li>", section.group(0))


def parse_target(target: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    file_path = MANUAL_DIR / target["file_name"]
    log_entry: dict[str, Any] = {
        "timestamp_utc": now_utc(),
        "target_id": target["target_id"],
        "law_name": target["law_name"],
        "law_id": target["law_id"],
        "source_file": str(file_path.relative_to(ROOT)),
        "source_file_exists": file_path.exists(),
        "history_items_detected": 0,
        "events_extracted": 0,
        "status": None,
        "notes": None,
    }
    unresolved: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    if not file_path.exists():
        log_entry["status"] = "manual_source_missing"
        log_entry["notes"] = "Input HTML file is missing"
        unresolved.append(
            {
                "related_target_id": target["target_id"],
                "problem_type": "manual_source_missing",
                "source_url": f"https://hourei.ndl.go.jp/simple/detail?lawId={target['law_id']}",
                "description": f"Manual source file not found: {target['file_name']}",
                "severity": "high",
            }
        )
        return events, log_entry, unresolved

    html = file_path.read_text(encoding="utf-8", errors="ignore")
    source_law_name = strip_tags((re.search(r"<h1>([\s\S]*?)</h1>", html) or ["", target["law_name"]])[1])
    law_number = match_field(html, "法律番号") or match_field(html, "政令番号")
    promulgated_text = match_field(html, "公布年月日")
    promulgated_date = parse_japanese_date(promulgated_text)
    bill_name = match_field(html, "法律案名")
    bill_session = match_field(html, "提出回次")
    passed_date = parse_japanese_date(match_field(html, "成立年月日"))

    if promulgated_date:
        detail_parts = [
            f"{law_number or '法令番号不明'}を公布。",
            f"法案名：{bill_name}。" if bill_name else None,
            f"提出回次：{bill_session}。" if bill_session else None,
            f"成立日：{passed_date}。" if passed_date else None,
        ]
        events.append(
            {
                "target_id": target["target_id"],
                "benefit_id": target["benefit_id"],
                "event_id": f"{target['target_id']}__promulgated",
                "event_type": "制定",
                "source_kind": target["source_kind"],
                "source": "日本法令索引",
                "source_file": target["file_name"],
                "source_law_name": source_law_name,
                "amendment_law_name": source_law_name,
                "amendment_law_number": law_number,
                "amendment_law_id": target["law_id"],
                "promulgation_date_original": promulgated_text,
                "promulgation_date_iso": promulgated_date,
                "title": f"制定：{source_law_name}",
                "detail": " ".join(part for part in detail_parts if part),
                "verification_status": "source_extracted",
            }
        )
    else:
        unresolved.append(
            {
                "related_target_id": target["target_id"],
                "problem_type": "promulgation_date_unparsed",
                "source_url": f"file://{file_path}",
                "description": "Could not parse promulgation date from basic law information.",
                "severity": "medium",
            }
        )

    history_items = extract_history_items(html)
    log_entry["history_items_detected"] = len(history_items)
    for index, item in enumerate(history_items, start=1):
        heading = strip_tags((re.search(r"<h3>([\s\S]*?)</h3>", item) or ["", ""])[1])
        if not heading:
            continue
        event_type = (re.match(r"^([^：]+)：", heading) or ["", "沿革"])[1]
        body = re.sub(r"^([^：]+)：\s*", "", heading)
        date = parse_japanese_date(body)
        number, note = split_law_number(body)
        if not date:
            unresolved.append(
                {
                    "related_target_id": target["target_id"],
                    "problem_type": "history_date_unparsed",
                    "source_url": f"file://{file_path}",
                    "description": heading,
                    "severity": "medium",
                }
            )
            continue

        events.append(
            {
                "target_id": target["target_id"],
                "benefit_id": target["benefit_id"],
                "event_id": f"{target['target_id']}__history_{index:03d}",
                "event_type": event_type,
                "source_kind": target["source_kind"],
                "source": "日本法令索引",
                "source_file": target["file_name"],
                "source_law_name": source_law_name,
                "amendment_law_name": None,
                "amendment_law_number": number,
                "amendment_law_id": None,
                "promulgation_date_original": re.search(r"(明治|大正|昭和|平成|令和)(元|\d+)年\d+月\d+日", body).group(0),
                "promulgation_date_iso": date,
                "title": f"{event_type}：{number}",
                "detail": note or f"{source_law_name}の{event_type}。",
                "verification_status": "source_extracted",
            }
        )

    log_entry["events_extracted"] = len(events)
    log_entry["status"] = "parsed" if events else "no_events_detected"
    return events, log_entry, unresolved


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    all_events: list[dict[str, Any]] = []
    parse_log: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for target in TARGETS:
        events, log_entry, target_unresolved = parse_target(target)
        all_events.extend(events)
        parse_log.append(log_entry)
        unresolved.extend(target_unresolved)

    all_events.sort(
        key=lambda item: (
            item.get("promulgation_date_iso") or "",
            item.get("benefit_id") or "",
            item.get("event_id") or "",
        )
    )
    for index, item in enumerate(unresolved, start=1):
        item["item_id"] = f"unresolved_{index:03d}"

    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "schema_version": "0.2.0",
                "generated_at_utc": now_utc(),
                "input_mode": "manual_saved_html",
                "source_directory": str(MANUAL_DIR.relative_to(ROOT)),
                "count": len(all_events),
                "amendments": all_events,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    PARSE_LOG_PATH.write_text(json.dumps(parse_log, ensure_ascii=False, indent=2), encoding="utf-8")
    UNRESOLVED_PATH.write_text(json.dumps(unresolved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote: {OUTPUT_PATH}")
    print(f"events: {len(all_events)}")
    print(f"unresolved: {len(unresolved)}")


if __name__ == "__main__":
    main()
