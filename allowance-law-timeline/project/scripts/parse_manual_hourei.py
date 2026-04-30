#!/usr/bin/env python3
"""Parse manually saved NDL Hourei HTML files and build amendments draft.

This script intentionally creates a conservative draft with nulls for unknown fields.
It does not fetch network resources.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MANUAL_DIR = DATA_DIR / "manual_sources" / "hourei"
OUTPUT_PATH = DATA_DIR / "amendments_draft.json"

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
