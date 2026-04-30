# Codex作業指示書
## 児童関係手当制度の法改正・国会審議一次資料JSON化プロジェクト

## 0. この作業の目的


## 0.1 実行環境制約と入力方式（重要）

Codex実行環境では `hourei.ndl.go.jp` への直接アクセスが `Tunnel connection failed: 403 Forbidden` になる場合がある。
この場合、Codexは日本法令索引のWeb取得を行わず、ユーザーがブラウザで手動保存したHTML/TXTを入力として処理する。

- 手動配置先: `project/data/manual_sources/hourei/`
- 解析対象: 上記ディレクトリに配置された保存済みファイル
- Codexの責務: 保存済みファイルから法令沿革・改正法リンク・審議経過リンクを抽出し、JSON化する
- 禁止事項: 取得不能分を推測で補完しない（不明値は `null`）

このプロジェクトの目的は、以下の法令について、法改正の変遷と国会審議上の説明・議論を、一次資料に基づいてJSON化することである。

対象法令は次の5本である。

1. 児童手当法  
   https://hourei.ndl.go.jp/#/detail?lawId=0000061613&searchDiv=1&current=5

2. 児童扶養手当法  
   https://hourei.ndl.go.jp/#/detail?lawId=0000053349&searchDiv=1&current=2

3. 児童扶養手当法施行令  
   https://hourei.ndl.go.jp/#/detail?lawId=0000053370&searchDiv=1&current=22

4. 特別児童扶養手当等の支給に関する法律  
   https://hourei.ndl.go.jp/#/detail?lawId=0000055859&searchDiv=1&current=3

5. 特別児童扶養手当等の支給に関する法律施行令  
   https://hourei.ndl.go.jp/#/detail?lawId=0000065214&searchDiv=1&current=3

この作業の最終目的は、Codexが制度史の結論を出すことではない。

Codexの役割は、一次資料をたどり、後からChatGPT 5.5で再分析しやすい構造化データを作ることである。

推測・補完・政策評価は行わないこと。
不明な値は `null` とし、確認が必要な項目は `verification_status: "unverified"` とすること。

---

## 1. 重要な基本方針

### 1.1 一次資料を最優先する

使用する資料は、原則として次の一次資料に限定する。

- 日本法令索引
- 国会会議録検索システム
- 衆議院の法律本文・議案情報
- 参議院の議案情報
- e-Gov法令検索
- 官報・法令全書に相当する公的資料

民間サイト、解説サイト、ブログ、Wikipedia等は使用しない。
使用した場合でも、補助資料としてのみ扱い、JSONの根拠資料にはしない。

### 1.2 「改正内容」と「審議論点」を分ける

この作業では、以下を明確に分離する。

#### A. 改正内容

主に次の審議経過項目から抽出する。

- 趣旨説明
- 提案理由説明
- 修正部分趣旨説明
- 委員長報告
- 法律案要綱
- 法律本文

これは、その改正で何が変わったかを記録するためのデータである。

#### B. 審議論点

主に次の審議経過項目から抽出する。

- 質疑
- 討論
- 附帯決議

これは、その改正をめぐって国会で何が議論されたかを記録するためのデータである。

注意：
質疑の中で制度内容が説明されることはあるが、質疑をそのまま「改正内容」として扱わないこと。
質疑は原則として `discussion_points` に入れる。

### 1.3 Codexは結論を出さない

Codexは、以下をしてはならない。

- 制度史上の重要性を勝手に判断する
- 「おそらく」「たぶん」で制度改正内容を補う
- URLや原文抜粋のない要約を作る
- 複数資料を混ぜて一つの事実のように書く
- 政策評価を行う
- 所得制限の逆転現象などについて独自計算を行う

Codexがやるべきことは、一次資料から以下を取り出すことである。

- 改正法の一覧
- 改正法ごとの審議経過
- 国会会議録URL
- 趣旨説明・修正趣旨説明・質疑等の種別
- 原文抜粋
- 原文に基づく短い要約
- 後で分析しやすいタグ

---

## 2. 成果物の全体構成

以下のディレクトリ構成で出力すること。

```text
project/
  README.md
  data/
    manifest.json
    target_laws.json
    amendments.json
    source_events.json
    extracted_change_claims.json
    discussion_points.json
    raw_sources/
      kokkai/
      hourei/
    logs/
      collection_log.json
      errors.json
      unresolved_items.json
  scripts/
    collect_hourei_amendments.py
    collect_deliberation_links.py
    collect_kokkai_texts.py
    extract_claims.py
    validate_json.py
  schemas/
    manifest.schema.json
    target_laws.schema.json
    amendments.schema.json
    source_events.schema.json
    extracted_change_claims.schema.json
    discussion_points.schema.json
```

可能であれば、JSON Lines形式も併用してよい。

```text
data/jsonl/
  amendments.jsonl
  source_events.jsonl
  extracted_change_claims.jsonl
  discussion_points.jsonl
```

---

## 3. 各JSONファイルの役割

## 3.1 `manifest.json`

プロジェクト全体の設定・対象・作業方針を記録する。

```json
{
  "schema_version": "0.1.0",
  "project_name": "児童関係手当制度 法改正・国会審議一次資料JSON化プロジェクト",
  "purpose": "児童手当法、児童扶養手当法、特別児童扶養手当等の支給に関する法律および関連施行令について、法改正履歴と国会審議資料を一次資料ベースで構造化する。",
  "created_by": "Codex",
  "intended_reviewer": "ChatGPT 5.5",
  "rules": {
    "primary_sources_only": true,
    "do_not_invent": true,
    "unknown_values_as_null": true,
    "raw_excerpt_required": true,
    "url_required": true,
    "separate_facts_from_interpretation": true
  },
  "target_files": [
    "target_laws.json",
    "amendments.json",
    "source_events.json",
    "extracted_change_claims.json",
    "discussion_points.json"
  ]
}
```

## 3.2 `target_laws.json`

対象法令の基本情報を入れる。

```json
[
  {
    "target_id": "jidou_teate_hou",
    "law_name": "児童手当法",
    "law_category": "law",
    "ndl_law_id": "0000061613",
    "hourei_ndl_url": "https://hourei.ndl.go.jp/#/detail?lawId=0000061613&searchDiv=1&current=5",
    "simple_url": null,
    "focus_topics": [
      "制度創設",
      "支給対象",
      "所得制限",
      "支給額"
    ],
    "collection_status": "not_started",
    "notes": null
  }
]
```

`target_id` は以下を使うこと。

```json
[
  "jidou_teate_hou",
  "jidou_fuyou_teate_hou",
  "jidou_fuyou_teate_hou_sekourei",
  "tokubetsu_jidou_fuyou_teate_hou",
  "tokubetsu_jidou_fuyou_teate_hou_sekourei"
]
```

## 3.3 `amendments.json`

日本法令索引の「法令沿革」から、各改正履歴を抽出する。

```json
[
  {
    "amendment_id": "tokubetsu_jidou_fuyou_teate_hou__S41_L128",
    "target_id": "tokubetsu_jidou_fuyou_teate_hou",
    "amendment_label": "第一次改正",
    "amendment_law_name": "重度精神薄弱児扶養手当法の一部を改正する法律",
    "amendment_law_number": "昭和41年法律第128号",
    "amendment_law_id": "0000057645",
    "amendment_hourei_ndl_url": "https://hourei.ndl.go.jp/#/detail?lawId=0000057645&current=3",
    "promulgation_date_original": "昭和41年7月15日",
    "promulgation_date_iso": "1966-07-15",
    "history_text_raw": "改正：昭和41年7月15日法律第128号〔第一次改正〕",
    "history_note": "題名改正：特別児童扶養手当法",
    "amendment_type": "改正",
    "is_minor_conforming_amendment": null,
    "is_target_law_main_amendment": null,
    "bill_info": {
      "bill_name": null,
      "diet_session": null,
      "bill_type": null,
      "bill_number": null,
      "submitter": null,
      "submitted_date_original": null,
      "submitted_date_iso": null,
      "passed_date_original": null,
      "passed_date_iso": null
    },
    "collection_status": "unverified",
    "notes": null
  }
]
```

`is_minor_conforming_amendment` や `is_target_law_main_amendment` は、判断できない場合は `null` のままでよい。
Codexが勝手に「これは重要」「これは軽微」と断定しないこと。

## 3.4 `source_events.json`

改正法ページの「審議経過」から、国会会議録リンクを抽出する。

```json
[
  {
    "source_event_id": "tokubetsu_jidou_fuyou_teate_hou__S41_L128__event_001",
    "amendment_id": "tokubetsu_jidou_fuyou_teate_hou__S41_L128",
    "target_id": "tokubetsu_jidou_fuyou_teate_hou",
    "source_type": "趣旨説明",
    "source_type_normalized": "趣旨説明",
    "source_system": "国会会議録検索システム",
    "kokkai_ndl_url": "https://kokkai.ndl.go.jp/...",
    "pdf_url": "https://kokkai.ndl.go.jp/...",
    "title": "第51回国会 衆議院 本会議 第25号 昭和41年3月10日",
    "diet_session": "第51回国会",
    "house": "衆議院",
    "meeting_name": "本会議",
    "meeting_number": "第25号",
    "date_original": "昭和41年3月10日",
    "date_iso": "1966-03-10",
    "page_range": "p.419-420",
    "speaker": null,
    "speaker_role": null,
    "raw_excerpt": null,
    "normalized_summary": null,
    "raw_text_file": "data/raw_sources/kokkai/tokubetsu_jidou_fuyou_teate_hou__S41_L128__event_001.txt",
    "collection_status": "url_collected",
    "verification_status": "unverified",
    "notes": null
  }
]
```

`source_type_normalized` の許容値：

```json
[
  "趣旨説明",
  "提案理由説明",
  "修正部分趣旨説明",
  "衆議院修正部分趣旨説明",
  "参議院修正部分趣旨説明",
  "質疑",
  "討論",
  "委員長報告",
  "附帯決議",
  "議案",
  "採決",
  "その他"
]
```

## 3.5 `extracted_change_claims.json`

趣旨説明・提案理由説明・修正趣旨説明・委員長報告などから、改正内容を抽出する。

```json
[
  {
    "claim_id": "tokubetsu_jidou_fuyou_teate_hou__S41_L128__claim_001",
    "target_id": "tokubetsu_jidou_fuyou_teate_hou",
    "amendment_id": "tokubetsu_jidou_fuyou_teate_hou__S41_L128",
    "source_event_id": "tokubetsu_jidou_fuyou_teate_hou__S41_L128__event_001",
    "claim_type": "名称変更",
    "affected_area": "法律名・制度名",
    "fact_summary": "法律の題名を改める内容が説明されている。",
    "raw_basis_quote": "原文抜粋をここに入れる。",
    "quote_start_hint": null,
    "quote_end_hint": null,
    "interpretation_note": null,
    "requires_human_review": true,
    "confidence": "needs_verification"
  }
]
```

`claim_type` の許容値：

```json
[
  "制度創設",
  "名称変更",
  "対象拡大",
  "対象縮小",
  "支給額改定",
  "所得制限改定",
  "所得算定方法変更",
  "障害認定基準変更",
  "併給調整変更",
  "支給停止変更",
  "手続変更",
  "事務移管",
  "施行期日",
  "経過措置",
  "関連制度整備",
  "その他"
]
```

`raw_basis_quote` が空の場合、`fact_summary` を作らないこと。
どうしても要約が必要な場合は、`requires_human_review: true` とし、`confidence: "low"` にすること。

## 3.6 `discussion_points.json`

質疑・討論・附帯決議から、審議論点を抽出する。

```json
[
  {
    "discussion_id": "tokubetsu_jidou_fuyou_teate_hou__S41_L128__discussion_001",
    "target_id": "tokubetsu_jidou_fuyou_teate_hou",
    "amendment_id": "tokubetsu_jidou_fuyou_teate_hou__S41_L128",
    "source_event_id": "tokubetsu_jidou_fuyou_teate_hou__S41_L128__event_002",
    "topic": "所得制限",
    "questioner": null,
    "questioner_party": null,
    "respondent": null,
    "respondent_role": null,
    "question_summary": null,
    "answer_summary": null,
    "raw_basis_quote": null,
    "policy_issue_tags": [
      "所得制限",
      "支給停止",
      "制度趣旨"
    ],
    "requires_human_review": true,
    "importance": "needs_review",
    "notes": null
  }
]
```

`policy_issue_tags` の候補：

```json
[
  "所得制限",
  "支給停止",
  "支給額",
  "対象児童",
  "障害程度",
  "扶養義務者",
  "母子家庭",
  "父子家庭",
  "ひとり親",
  "公的年金",
  "併給調整",
  "生活保護",
  "地方自治体",
  "事務負担",
  "財源",
  "物価スライド",
  "逆転現象",
  "制度趣旨",
  "児童福祉",
  "障害福祉",
  "その他"
]
```

---

## 4. 作業手順

## Step 1：対象法令ページの取得

各対象法令について、日本法令索引のURLを開く。

通常表示ページがJavaScript依存で取得しにくい場合は、シンプル表示URLを試す。

例：

```text
https://hourei.ndl.go.jp/simple/detail?lawId=0000055859
```

取得したHTMLまたはテキストを保存する。

```text
data/raw_sources/hourei/{target_id}.html
data/raw_sources/hourei/{target_id}.txt
```

## Step 2：法令沿革の抽出

各対象法令ページの「法令沿革」から、改正履歴を全件抽出する。

抽出する項目は以下。

- 改正・廃止等の種別
- 日付
- 法律番号または政令番号
- 改正法名
- 改正法へのリンク
- ラベル
- 題名改正等の注記
- 本文情報リンクがある場合はそのURL

この時点では、改正内容を要約しない。
まずは改正履歴を機械的に `amendments.json` に入れる。

## Step 3：各改正法ページの取得

`amendments.json` に入れた改正法URLを順番に開き、改正法ページを保存する。

```text
data/raw_sources/hourei/amendments/{amendment_id}.html
data/raw_sources/hourei/amendments/{amendment_id}.txt
```

そこから、法案情報を抽出する。

- 法律案名
- 提出回次
- 種別
- 提出番号
- 提出者
- 提出年月日
- 成立年月日

これを `amendments.json` の `bill_info` に追記する。

## Step 4：審議経過URLの抽出

改正法ページの「審議経過」から、国会会議録リンクを全件抽出する。

各リンクについて、以下を `source_events.json` に入れる。

- 国会会議録URL
- PDF URL
- タイトル
- 回次
- 院
- 会議名
- 会議番号
- 開催日
- 審議項目種別
- ページ範囲

対象とする審議項目は以下。

- 趣旨説明
- 提案理由説明
- 衆議院修正部分趣旨説明
- 参議院修正部分趣旨説明
- 質疑
- 討論
- 委員長報告
- 附帯決議
- 議案
- 採決

## Step 5：国会会議録本文の取得

`source_events.json` の `kokkai_ndl_url` を開き、本文を保存する。

```text
data/raw_sources/kokkai/{source_event_id}.txt
```

取得できる場合は、次も保存する。

```text
data/raw_sources/kokkai/{source_event_id}.json
data/raw_sources/kokkai/{source_event_id}.html
data/raw_sources/kokkai/{source_event_id}.pdf
```

ただし、PDFしか取れない場合、OCRは原則として行わない。
テキスト表示またはAPIから取得できる本文を優先する。

## Step 6：趣旨説明・修正趣旨説明から改正内容を抽出

対象は次の `source_type_normalized`。

- 趣旨説明
- 提案理由説明
- 修正部分趣旨説明
- 衆議院修正部分趣旨説明
- 参議院修正部分趣旨説明
- 委員長報告

これらから、改正内容に関する記述を抽出し、`extracted_change_claims.json` に入れる。

抽出時のルール：

- 1つの改正内容につき1 claim とする
- 原文抜粋を必ず入れる
- 要約は短くする
- 解釈は `interpretation_note` に分離する
- 判断に迷う場合は `requires_human_review: true`
- 制度史上の意味づけはしない

## Step 7：質疑から審議論点を抽出

対象は次の `source_type_normalized`。

- 質疑
- 討論
- 附帯決議

これらから、制度上重要そうな論点を抽出し、`discussion_points.json` に入れる。

抽出する論点は、特に以下を優先する。

- 所得制限
- 支給停止
- 支給額
- 対象児童
- 障害程度
- 併給調整
- 公的年金との関係
- 生活保護との関係
- 扶養義務者
- 地方自治体の事務
- 財源
- 制度趣旨
- 逆転現象に関する言及

ただし、すべての質疑を網羅的に要約する必要はない。
後でChatGPT 5.5が再分析できるよう、関連しそうな発言をURL・原文抜粋付きで残すことを優先する。

## Step 8：未解決項目の記録

取得できなかったもの、判断できなかったもの、リンク切れ、本文未取得、会議録本文が見つからないものは、以下に記録する。

```text
data/logs/unresolved_items.json
data/logs/errors.json
```

形式は以下。

```json
[
  {
    "item_id": "unresolved_001",
    "related_target_id": "tokubetsu_jidou_fuyou_teate_hou",
    "related_amendment_id": "tokubetsu_jidou_fuyou_teate_hou__S41_L128",
    "problem_type": "kokkai_text_not_found",
    "source_url": "https://kokkai.ndl.go.jp/...",
    "description": "国会会議録URLは取得できたが、本文テキストを取得できなかった。",
    "next_action_suggestion": "手動でURLを確認する。",
    "severity": "medium"
  }
]
```

---

## 5. ID命名規則

IDは、後から結合しやすいように機械的に作る。

### 5.1 `amendment_id`

```text
{target_id}__{era_year_law_number}
```

例：

```text
tokubetsu_jidou_fuyou_teate_hou__S41_L128
jidou_fuyou_teate_hou__S60_L34
```

政令の場合：

```text
jidou_fuyou_teate_hou_sekourei__S36_C405
```

`L` は法律、`C` は政令を表す。

### 5.2 `source_event_id`

```text
{amendment_id}__event_{3桁連番}
```

例：

```text
tokubetsu_jidou_fuyou_teate_hou__S41_L128__event_001
```

### 5.3 `claim_id`

```text
{amendment_id}__claim_{3桁連番}
```

例：

```text
tokubetsu_jidou_fuyou_teate_hou__S41_L128__claim_001
```

### 5.4 `discussion_id`

```text
{amendment_id}__discussion_{3桁連番}
```

例：

```text
tokubetsu_jidou_fuyou_teate_hou__S41_L128__discussion_001
```

---

## 6. 日付の扱い

日付は必ず原文表記とISO形式を両方持つ。

```json
{
  "date_original": "昭和41年7月15日",
  "date_iso": "1966-07-15"
}
```

変換できない場合は、ISO形式を `null` にする。

```json
{
  "date_original": "昭和41年頃",
  "date_iso": null
}
```

---

## 7. 原文抜粋の扱い

原文抜粋は、過剰に長くしない。
ただし、後で意味が確認できる程度には残す。

推奨：

- 1 claim あたり 1〜5文程度
- 複数箇所に根拠がある場合は、claimを分ける
- 発言者が分かる場合は `speaker` を入れる
- ページ範囲が分かる場合は `page_range` を入れる

---

## 8. 出力後に必ず行う検証

以下の検証スクリプトを作成すること。

```text
scripts/validate_json.py
```

検証内容：

- 全JSONが構文エラーなく読める
- `amendment_id` が重複していない
- `source_event_id` が重複していない
- `claim_id` が重複していない
- `discussion_id` が重複していない
- `source_events.amendment_id` が `amendments.amendment_id` に存在する
- `extracted_change_claims.source_event_id` が `source_events.source_event_id` に存在する
- `discussion_points.source_event_id` が `source_events.source_event_id` に存在する
- `kokkai_ndl_url` が空の `source_events` を一覧化する
- `raw_basis_quote` が空の `extracted_change_claims` を一覧化する
- `verification_status` が `verified` なのに `raw_basis_quote` が空のものをエラーにする

---

## 9. ChatGPT 5.5で再分析しやすくするための追加出力

最後に、ChatGPT 5.5へ渡すための要約インデックスを作る。

```text
data/review_pack/
  review_index.json
  amendment_overview.md
  source_event_overview.md
  claims_needing_review.md
  discussion_points_needing_review.md
```

### 9.1 `review_index.json`

```json
{
  "generated_for": "ChatGPT 5.5 review",
  "purpose": "一次資料から抽出した改正内容・審議論点を再分析するための索引",
  "files": {
    "target_laws": "../target_laws.json",
    "amendments": "../amendments.json",
    "source_events": "../source_events.json",
    "extracted_change_claims": "../extracted_change_claims.json",
    "discussion_points": "../discussion_points.json"
  },
  "review_priorities": [
    "所得制限に関する改正",
    "支給停止に関する改正",
    "支給額改定",
    "対象拡大・対象縮小",
    "併給調整",
    "逆転現象に関する質疑"
  ],
  "known_limitations": []
}
```

### 9.2 `amendment_overview.md`

対象法令ごとに、改正履歴を簡潔に並べる。

ただし、ここでは長文要約しない。
ChatGPT 5.5が元JSONへ戻れるよう、IDとURLを中心にする。

例：

```text
## 特別児童扶養手当等の支給に関する法律

- tokubetsu_jidou_fuyou_teate_hou__S41_L128
  - 昭和41年法律第128号
  - 重度精神薄弱児扶養手当法の一部を改正する法律
  - 趣旨説明あり
  - 質疑あり
  - 修正趣旨説明あり
```

### 9.3 `claims_needing_review.md`

`requires_human_review: true` の claim を一覧化する。

### 9.4 `discussion_points_needing_review.md`

`importance: "needs_review"` の discussion を一覧化する。

---

## 10. 最終成果物

最終的に以下を納品すること。

```text
data/
  manifest.json
  target_laws.json
  amendments.json
  source_events.json
  extracted_change_claims.json
  discussion_points.json
  logs/
    collection_log.json
    errors.json
    unresolved_items.json
  review_pack/
    review_index.json
    amendment_overview.md
    source_event_overview.md
    claims_needing_review.md
    discussion_points_needing_review.md
schemas/
scripts/
README.md
```

---

## 11. README.md に書くこと

READMEには、以下を書くこと。

```text
# 児童関係手当制度 法改正・国会審議一次資料JSON化プロジェクト

## 対象法令

## 収集方法

## データ構造

## 各JSONファイルの説明

## ID命名規則

## 未解決項目

## ChatGPT 5.5での再分析方法

## 注意事項
- このデータは一次資料の抽出結果であり、制度史としての最終解釈ではない。
- 改正内容と審議論点は分離している。
- raw_basis_quote と source_url のない主張は検証済み扱いしない。
```

---

## 12. 絶対に守ること

以下は絶対に守ること。

```text
- 推測で埋めない。
- URLなしの主張を作らない。
- 原文抜粋なしの改正内容 claim を作らない。
- 趣旨説明と質疑を混同しない。
- 改正内容と審議論点を混同しない。
- 「制度史上重要」と勝手に判断しない。
- 不明なものは null にする。
- 確認が必要なものは requires_human_review: true にする。
- 後でChatGPT 5.5が再分析できるよう、ID・URL・原文抜粋を必ず残す。
```

---

## 13. 最初に実行するタスク

まず以下だけを行うこと。

```text
1. project/ ディレクトリを作成する。
2. data/, scripts/, schemas/ を作成する。
3. manifest.json と target_laws.json を作成する。
4. 各 target_law の日本法令索引シンプル表示ページを取得できるか確認する。
5. 取得結果を data/logs/collection_log.json に記録する。
6. まだ改正内容の抽出は始めない。
```

その後、次の順で進める。

```text
Phase 1: 法令沿革の全件取得
Phase 2: 改正法ページの取得
Phase 3: 審議経過URLの取得
Phase 4: 国会会議録本文の取得
Phase 5: 趣旨説明・修正趣旨説明から改正内容抽出
Phase 6: 質疑から審議論点抽出
Phase 7: 検証・review_pack作成
```

---

## 14. 期待する作業結果の性格

この作業結果は、完成された制度史ではない。

これは、ChatGPT 5.5が次に以下を行うための材料である。

- 法改正の時系列整理
- 所得制限の変遷分析
- 支給停止・所得逆転現象の分析
- 児童手当・児童扶養手当・特別児童扶養手当の比較
- 国会審議上の論点整理
- 改正内容と審議論点の対応関係の分析
- 最終的なタイムライン作成

したがって、Codexの成果物では、結論よりも検証可能性を優先すること。
