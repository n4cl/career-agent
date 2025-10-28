# 詳細設計書：ユーザープロフィール管理機能 (Profile Agent)

## 1. 機能概要

Profile Agent は、ユーザーが提供するテキスト情報（貼り付け入力・ファイル指定・インタラクティブ回答）を分析し、求人評価に利用する構造化プロフィールを生成・更新・表示するエージェントである。CLI から `profile create` / `profile update` / `profile show` コマンドで呼び出されるほか、将来的に他エージェントや外部スクリプトから直接利用できる API を提供する。

## 2. 責務

- 入力収集: ユーザーによる貼り付け・ファイル指定・対話回答を統合し、プロフィール生成に必要な原文テキストを構築する。
- 情報補完: 不足フィールドを検出し、ヒアリング質問（LLM 生成）を提示して回答を収集する。対話は既定で有効とし、`--no-interactive` 時にのみスキップする。
- プロフィール生成: 収集した情報を LLM に送信して構造化 JSON を生成し、スキーマ検証を行う。
- 永続化: プロフィールデータ（`profiles/user_profile.json`）と、入力ソースのメタ情報・質疑応答ログを保存する。
- 表示: 保存済みプロフィールをテキスト整形または JSON 形式で出力する。
- 再利用: 部分更新時に既存プロフィールを読み込み、指定フィールドのみを再生成／追記する。

## 3. インターフェース

### 3.1 CLI コマンド

> 注記: オプション仕様は本設計の指針を示すもので、最終的な引数定義は実装段階で微調整する可能性がある。

| コマンド | 主なオプション | 既定挙動 | 概要 |
| --- | --- | --- | --- |
| `profile create` | `--file <path>` (複数可), `--force`, `--no-interactive` | 対話ヒアリングあり | 初期プロフィールを生成。既存ファイルがある場合は `--force` が無ければ中断。貼り付け入力とファイル読込を統合して LLM に渡す。 |
| `profile update` | `--fields <list>`, `--file <path>` (複数可), `--no-interactive` | 対話ヒアリングあり | 既存プロフィールの指定領域を再生成／補完。追加入力の貼り付けやファイルを受け取り、欠損フィールドに対する質問を行う。 |
| `profile show` | `--format text|json`, `--raw` | `text` | 保存済みプロフィールを表示。`--raw` 指定時は保存ファイルの JSON をそのまま出力。 |

### 3.2 内部 API（想定）

| メソッド | 引数 | 返り値 | 説明 |
| --- | --- | --- | --- |
| `create_profile(session: ProfileSession) -> ProfileResult` | 入力ソース、ヒアリング設定、保存先 | プロフィール JSON, メタ情報 | 初回作成フローを実行。既存データがある場合はエラーを返すか `session.force_overwrite` で上書き。 |
| `update_profile(session: ProfileSession, target_fields: list[str]) -> ProfileResult` | ターゲットフィールド、追加入力、ヒアリング設定 | 更新済みプロファイル | 部分更新対象を評価し、差分だけ LLM に再生成させてマージ。 |
| `show_profile(format: Literal['text','json','raw']) -> str` | 表示形式 | 整形済み文字列 | 保存ファイルを読み込み、整形または生データを返す。 |

## 4. 入力モードとセッション管理

### 4.1 入力ソース

- **貼り付け入力**: CLI 実行時に標準入力から受け取るテキストブロック。複数ブロックを順序付けて保持する。
- **ファイル入力 (`--file`)**: Markdown / プレーンテキストなどを読み込み、ファイルパスと共にセッションへ登録する。指定順を保持し、メタデータに格納する。
- **ヒアリング回答**: 対話モードで提示した質問に対するユーザー回答。質問ごとに `question_id`, `prompt`, `answer` を記録する。

### 4.2 セッション構造

| フィールド | 型の目安 | 説明 |
| --- | --- | --- |
| `mode` | `"create"` / `"update"` | 実行モードの識別子。 |
| `input_chunks` | 配列 | `{id, source, path?, content}` を持つチャンク群。`source` は `paste` / `file` / `qa` のいずれか。 |
| `interactive` | 真偽値 | `false` の場合 `--no-interactive` が指定されたことを表す。 |
| `target_fields` | 文字列配列 (任意) | `profile update` 時に再生成するフィールド名一覧。 |
| `force_overwrite` | 真偽値 (任意) | `profile create` で既存プロフィールを上書きするかどうか。 |
| `profile_path` | 文字列 | 保存先パス。既定値は `profiles/user_profile.json`。 |
| `timestamp` | 文字列 | ISO 8601 形式の実行時刻。ログやバックアップ命名に利用する。 |

セッションは CLI 層で構築し、エージェント内部に渡す。`interactive = true` の場合のみヒアリングフェーズに進む。`target_fields` が指定されない場合、更新対象は LLM に自動検出させる方針としつつ、実装時に許可するか検討する。

### 4.3 ヒアリングフロー

1. **欠損判定**: 既存プロフィールおよび入力テキストから、必須／推奨フィールドの充足度を判定する。
2. **質問生成**: LLM に対して「欠損フィールド」「必要な追加情報」「聞き方のトーン」を渡し、質問リストを生成する。
3. **質問提示**: CLI が質問を表示し、ユーザーの回答を受け取る。回答は逐次 `inputChunks` に追記。
4. **再評価**: 追加回答を反映した後、残りの欠損があれば再度質問生成を行う。最大試行回数やキャンセル条件を設ける。

`--no-interactive` 指定時は 1 の欠損判定までで止め、未充足フィールドリストを警告として出力する（エラー扱いにするかは詳細設計で決定）。

## 5. データ構造

### 5.1 プロフィールデータの全体像

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `metadata` | `Metadata` | 必須 | 入力ソースや更新日時などの付帯情報。 | `{...}` |
| `summary` | `Summary` | 必須 | ユーザー概要、経験年数、ハイライト。 | `{...}` |
| `career` | `Career` | 推奨 | スキル・職務経歴など現在までの実績。 | `{ "skills": [...], "experiences": [...] }` |
| `plan` | `Plan \| None` | 推奨 | 今後の志向や希望条件。情報がなければ `None`。 | `{...}` |

#### 5.1.1 `Metadata`

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `input_sources` | `list[InputSource]` | 必須 | 使用した入力チャンクの一覧。順序を保持。 | `[{"id": "chunk-1", ...}]` |
| `last_updated` | `datetime`（ISO8601文字列） | 必須 | 最終更新日時。 | `"2025-07-30T12:00:00Z"` |
| `version` | `int \| None` | 任意 | スキーマや更新回数の管理に使用。 | `1` |

`InputSource` の詳細:

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `id` | `str` | 必須 | チャンク識別子。 | `"chunk-1"` |
| `type` | `Literal["paste","file","qa"]` | 必須 | 入力種別。 | `"file"` |
| `label` | `str \| None` | 任意 | 人間向けラベル。 | `"cv.md"` |
| `path` | `str \| None` | 任意 | 元ファイルパス。貼り付け入力時は `None`。 | `"docs/cv.md"` |

#### 5.1.2 `Summary`

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `identity` | `str` | 必須 | 自己紹介や肩書き。 | `"バックエンドエンジニア"` |
| `overall_experience_years` | `int \| None` | 推奨 | 実務年数。未知なら `None`。 | `10` |
| `notable_highlights` | `list[str] \| None` | 任意 | 特筆すべき実績。 | `["SaaS開発リード"]` |

#### 5.1.3 `Career`

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `skills` | `list[SkillEntry]` | 推奨 | スキルセットの詳細。空リスト可。 | `[{"name": "Python", ...}]` |
| `experiences` | `list[ExperienceEntry]` | 推奨 | 職務経歴リスト。 | `[{"company": "株式会社A", ...}]` |
| `certifications` | `list[str] \| None` | 任意 | 資格・認定。 | `["AWS Solutions Architect"]` |
| `languages` | `list[str] \| None` | 任意 | 使用言語（自然言語）。 | `["ja", "en"]` |

`SkillEntry` の詳細:

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `name` | `str` | 必須 | スキル名。 | `"Python"` |
| `level` | `int \| None` | 推奨 | 自己評価（1-5 など）。 | `5` |
| `experience_years` | `float \| None` | 任意 | 使用年数。 | `10.0` |
| `details` | `str \| None` | 任意 | 実績詳細。 | `"API開発、データ処理"` |

`ExperienceEntry` の詳細:

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `company` | `str` | 必須 | 企業名／組織名。 | `"株式会社A"` |
| `period` | `str` | 必須 | 在籍期間（自由記述）。 | `"2020-04 - 現在"` |
| `position` | `str \| None` | 推奨 | 役職・担当。 | `"シニアソフトウェアエンジニア"` |
| `achievements` | `list[str] \| None` | 任意 | 代表的な成果。 | `["マイクロサービス移行を主導"]` |
| `summary` | `str \| None` | 任意 | 業務内容の概要。 | `"SaaSプロダクトのバックエンド開発を担当"` |

#### 5.1.4 `Plan`

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `wants_to_do` | `str \| None` | 推奨 | 今後やりたい業務。 | `"技術的負債解消に取り組みたい"` |
| `interests` | `list[str] \| None` | 任意 | 興味領域。 | `["マイクロサービス", "分散システム"]` |
| `preferences` | `PlanPreferences \| None` | 任意 | 働き方や条件面の希望。 | `{...}` |
| `avoid` | `PlanAvoidance \| None` | 任意 | 避けたい条件やNG事項。 | `{...}` |

`PlanPreferences` の詳細:

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `team_size` | `str \| None` | 任意 | 希望するチーム規模。 | `"5-10人"` |
| `work_style` | `str \| None` | 任意 | 働き方（例: ハイブリッド、リモート頻度）。 | `"週2-3日のリモート"` |
| `working_hours` | `str \| None` | 任意 | 勤務時間帯や柔軟性。 | `"フレックス希望"` |
| `location` | `list[str] \| None` | 任意 | 希望勤務地（都市・国・タイムゾーン）。 | `["東京23区内", "リモート"]` |
| `salary_expectation` | `SalaryExpectation \| None` | 任意 | 年収・報酬レンジの希望。 | `{...}` |

`PlanAvoidance` の詳細:

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `must_avoid` | `list[str] \| None` | 任意 | 絶対に避けたい条件。 | `["完全出社", "深夜常駐"]` |
| `cautions` | `list[str] \| None` | 任意 | 可能なら避けたい／留意事項。 | `["SES案件多めの現場", "形骸化したレビュー文化"]` |

`SalaryExpectation` の詳細:

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `currency` | `str \| None` | 任意 | 通貨コード。 | `"JPY"` |
| `minimum` | `int \| None` | 任意 | 希望下限（年収等）。 | `8000000` |
| `target` | `int \| None` | 任意 | 希望目標値。 | `9000000` |
| `maximum` | `int \| None` | 任意 | 許容上限。 | `12000000` |

### 5.2 Python 型定義イメージ

実装時には以下のようなデータクラス／型エイリアスを想定する。

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

InputSourceType = Literal["paste", "file", "qa"]

@dataclass
class InputSource:
    id: str
    type: InputSourceType
    label: Optional[str] = None
    path: Optional[str] = None

@dataclass
class Metadata:
    input_sources: list[InputSource]
    last_updated: datetime
    version: Optional[int] = None

@dataclass
class Summary:
    identity: str
    overall_experience_years: Optional[int] = None
    notable_highlights: Optional[list[str]] = None

@dataclass
class SkillEntry:
    name: str
    level: Optional[int] = None
    experience_years: Optional[float] = None
    details: Optional[str] = None

@dataclass
class ExperienceEntry:
    company: str
    period: str
    position: Optional[str] = None
    achievements: Optional[list[str]] = None
    summary: Optional[str] = None

@dataclass
class Career:
    skills: list[SkillEntry]
    experiences: list[ExperienceEntry]
    certifications: Optional[list[str]] = None
    languages: Optional[list[str]] = None

@dataclass
class SalaryExpectation:
    currency: Optional[str] = None
    minimum: Optional[int] = None
    target: Optional[int] = None
    maximum: Optional[int] = None

@dataclass
class PlanPreferences:
    team_size: Optional[str] = None
    work_style: Optional[str] = None
    working_hours: Optional[str] = None
    location: Optional[list[str]] = None
    salary_expectation: Optional[SalaryExpectation] = None

@dataclass
class PlanAvoidance:
    must_avoid: Optional[list[str]] = None
    cautions: Optional[list[str]] = None

@dataclass
class Plan:
    wants_to_do: Optional[str] = None
    interests: Optional[list[str]] = None
    preferences: Optional[PlanPreferences] = None
    avoid: Optional[PlanAvoidance] = None
```

### 5.3 サンプル JSON

テーブル仕様に基づく例を参考として掲載する。

```json
{
  "metadata": {
    "input_sources": [
      { "id": "chunk-1", "type": "file", "label": "cv.md", "path": "docs/cv.md" },
      { "id": "chunk-2", "type": "qa", "label": "plan-preferences" }
    ],
    "last_updated": "2025-07-30T12:00:00Z",
    "version": 1
  },
  "summary": {
    "identity": "バックエンドエンジニア",
    "overall_experience_years": 10,
    "notable_highlights": [
      "SaaSプロダクトの開発チームをリード",
      "マイクロサービスへの移行を主導"
    ]
  },
  "career": {
    "skills": [
      {
        "name": "Python",
        "level": 5,
        "experience_years": 10,
        "details": "API設計、バッチ処理、データ解析"
      }
    ],
    "experiences": [
      {
        "company": "株式会社A",
        "period": "2020-04 - 現在",
        "position": "シニアソフトウェアエンジニア",
        "achievements": ["マイクロサービス移行を主導"],
        "summary": "BtoB向けSaaSのバックエンド開発を担当"
      }
    ],
    "certifications": ["AWS Solutions Architect"],
    "languages": ["ja", "en"]
  },
  "plan": {
    "wants_to_do": "技術的負債の解消やスケーラビリティ改善に取り組みたい",
    "interests": ["マイクロサービス", "分散システム"],
    "preferences": {
      "team_size": "5-10人",
      "work_style": "週2-3日のリモートワーク",
      "working_hours": "フレックス希望",
      "location": ["東京23区内", "リモート"],
      "salary_expectation": {
        "currency": "JPY",
        "minimum": 8000000,
        "target": 9000000,
        "maximum": 12000000
      }
    },
    "avoid": {
      "must_avoid": ["完全出社", "長期出張を伴う配属"],
      "cautions": ["夜間シフト中心のチーム", "文化的に閉鎖的な組織"]
    }
  }
}
```

### 5.4 セッションログ

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `session_id` | `str` | 必須 | 実行ごとの一意な識別子。 | `"2025-07-30T12-00-00_create"` |
| `mode` | `Literal["create","update"]` | 必須 | 実行モード。 | `"create"` |
| `questions` | `list[QuestionLog]` | 任意 | ヒアリングで提示した質問と回答。 | `[{"id": "q1", ...}]` |
| `warnings` | `list[str]` | 任意 | 未補完フィールドなどの注意事項。 | `["plan.preferences.location が未入力"]` |

`QuestionLog` の詳細:

| フィールド | Python型の目安 | 必須 | 説明 | 例 |
| --- | --- | --- | --- | --- |
| `id` | `str` | 必須 | 質問 ID。 | `"q1"` |
| `field` | `str` | 必須 | 質問対象のフィールド名。 | `"plan.preferences.location"` |
| `prompt` | `str` | 必須 | 提示した質問文。 | `"希望する勤務地やタイムゾーンがあれば教えてください"` |
| `answer` | `str \| None` | 必須 | ユーザー回答。無回答の場合は `None`。 | `"東京23区内、フルリモート可"` |

セッションログも JSON で保存し、必要に応じて解析・評価に利用する。

## 6. LLM プロンプト設計

### 6.1 プロフィール生成プロンプト

- 入力: セッションのテキストチャンクを結合し、プロフィールスキーマの説明と共に LLM に提示。
- 期待出力: 上記 JSON スキーマに準拠。欠損フィールドは空配列／空文字ではなく `null` を利用するよう指示し、後続処理で補完しやすくする。
- 一貫性: 既存プロフィールがある場合、変更対象フィールドのみ更新し、それ以外は既存値を保持するようプロンプト内で指示する。

### 6.2 質問生成プロンプト

- 入力: 未充足フィールド一覧、既知情報のサマリ、質問トーン（丁寧・簡潔など）。
- 期待出力: `[{"id": "q1", "field": "plan.preferences.location", "question": "..."}]` や `plan.avoid.must_avoid` を問うパターンなど、マルチフィールドに対応可能な形式。
- 応答数: 1 回の生成で 1〜3 個の質問を返す。ユーザー回答後に再度欠損チェックを実施。

### 6.3 バリデーションプロンプト

- プロフィール JSON がスキーマに適合しない場合、エラー詳細を LLM へ渡し再生成を依頼するフォールバックプロンプトを定義する。

## 7. バリデーションとエラーハンドリング

- JSON スキーマ検証: `metadata`, `summary`, `career`, `plan` など必須キーをチェック。欠損時は LLM への再プロンプト。
- 衝突処理: `profile create` で既存ファイルが存在する場合はエラーを出し、`--force` 指定時のみ上書き。
- `profile update` で対象フィールドが存在しない場合、警告を出し新規フィールドとして扱うかエラーとするかを設定で制御。
- ヒアリング中断: ユーザーが空回答を連続した場合、最大試行回数に達したら対話を終了し、未補完フィールド一覧を保存／警告する。

## 8. 永続化と入出力

- プロフィール本体: `profiles/user_profile.json`
- セッションログ: `profiles/session_logs/<timestamp>_<mode>.json`
- バックアップ: `profiles/backups/<timestamp>.json` に直前のプロフィールをコピーし、更新失敗時のロールバックを可能にする。
- エンコーディング: UTF-8。整形出力（2 スペースインデント）を基本とし、人間が参照しやすい形式を維持する。

## 9. 処理フロー

### 9.1 `profile create`

```mermaid
sequenceDiagram
    participant CLI
    participant ProfileAgent
    participant LLM

    CLI->>ProfileAgent: create_profile(session)
    ProfileAgent->>ProfileAgent: 入力チャンク統合
    ProfileAgent->>ProfileAgent: 既存ファイル存在チェック
    ProfileAgent->>LLM: 暫定プロフィール生成プロンプト
    LLM-->>ProfileAgent: プロフィールJSON(暫定)
    ProfileAgent->>ProfileAgent: スキーマ検証・不足判定
    alt 対話ヒアリング有効
        ProfileAgent->>LLM: 欠損フィールドに基づく質問生成
        LLM-->>ProfileAgent: 質問リスト
        loop 各質問
            ProfileAgent->>CLI: 質問提示
            CLI-->>ProfileAgent: 回答または終了希望
            alt ユーザーが終了を宣言
                break ユーザー終了
                    ProfileAgent->>ProfileAgent: 残りの欠損を警告として記録
                end
            else 回答あり
                ProfileAgent->>ProfileAgent: 回答をチャンクに追加
                ProfileAgent->>LLM: 再プロンプト (チャンク追加後)
                LLM-->>ProfileAgent: 更新済みプロフィールJSON
                ProfileAgent->>ProfileAgent: スキーマ検証・不足判定
            end
        end
    end
    ProfileAgent->>ProfileAgent: 最終プロフィールを確定
    ProfileAgent->>ProfileAgent: バックアップ保存
    ProfileAgent->>ProfileAgent: profiles/user_profile.json に書き込み
    ProfileAgent->>ProfileAgent: セッションログ保存
    ProfileAgent-->>CLI: 成功メッセージ
```

### 9.1.1 処理フロー詳細 (create)

#### セッション初期化
- CLI 層が `ProfileSession` を構築し、貼り付けテキスト・`--file` 指定ファイル・既定値 `interactive=True` などをまとめる。
- `session.input_chunks` を初期化して LangGraph に渡す準備を行う。
- 既存プロフィールが存在する場合は、エージェント側で上書き可否を確認する。

#### 既存ファイル検査とバックアップ準備
- 保存先 (`profiles/user_profile.json`) の存在確認を実施する。
- `session.force_overwrite` が False の場合は処理を中断、True の場合はバックアップ先パスを先に決定する。

#### 入力チャンク統合と前処理
- テキスト入力とファイル内容を読み込み、チャンク ID・ソース種別・オリジナルパスなどのメタ情報を付与する。
- Markdown をプレーンテキストへ正規化するなど、後段のプロンプト生成に備えた整形を行う。

#### 初回プロフィール生成
- 現時点のチャンクを使って暫定プロフィールを生成し、欠損判定の基礎データを得る。
- 基本サイクルは以下の通り。
  - LLM へプロフィール生成を依頼し、JSON を受領する。
  - 受け取った JSON をスキーマ検証する。
  - バリデーション通過後は暫定プロフィールを保持し、欠損フィールド一覧を更新する。

#### ヒアリング（対話モード）
- `session.interactive` が True の場合、欠損候補から追加質問を LLM に生成させる。
- CLI に質問を提示し、ユーザー回答を `type="qa"` のチャンクとして追記する。
- 1 サイクルごとに欠損状況を再評価し、十分に補完できた段階で終了する。
- `--no-interactive` 指定時は質問生成をスキップし、未補完項目を警告として記録する。

#### 逐次プロフィール更新
- 新しい回答が得られるたびに、チャンク統合→プロフィール生成→スキーマ検証を再実行する。
- コストを抑えるための工夫例:
  - 差分プロンプトで更新対象フィールドだけを指示する。
  - 質問数件分をまとめて再生成する。
  - 同一チャンク構成時には結果キャッシュを再利用する。

#### 終了判定
- 欠損リストが空になった、またはユーザーが補足終了を宣言した時点でヒアリングを終える。
- 未補完項目が残る場合は `warnings` に記録して後段へ引き継ぐ。

#### 最終バリデーション
- 保存前に改めてプロフィール生成とスキーマ検証を実行し、結果が整合していることを確認する。
- 検証に連続で失敗する場合はエラーを返却し処理を中断する。

#### バックアップと書き込み
- 既存プロフィールがある場合は `profiles/backups/<timestamp>.json` にコピーしてから上書きする。
- 新しい JSON を `profiles/user_profile.json` に保存し、UTF-8 かつ 2 スペースインデントで整形する。

#### セッションログ保存
- 質問と回答、欠損補完状況などを `profiles/session_logs/<timestamp>_create.json` に記録する。
- `--no-interactive` の場合は未補完フィールド一覧をログに残す。

#### 結果返却
- CLI へ成功メッセージと保存先パスを返し、必要に応じて警告情報も伝える。

### 9.2 `profile update`

```mermaid
sequenceDiagram
    participant CLI
    participant ProfileAgent
    participant LLM

    CLI->>ProfileAgent: update_profile(session, target_fields)
    ProfileAgent->>ProfileAgent: 既存プロフィール読み込み
    ProfileAgent->>ProfileAgent: 追加入力チャンク統合
    ProfileAgent->>ProfileAgent: ターゲットフィールド欠損チェック
    alt 対話ヒアリング有効
        ProfileAgent->>LLM: 欠損フィールドに対する質問生成
        LLM-->>ProfileAgent: 質問リスト
        loop 各質問
            ProfileAgent->>CLI: 質問提示
            CLI-->>ProfileAgent: 回答受領
            ProfileAgent->>ProfileAgent: 回答をチャンクに追加
        end
    end
    ProfileAgent->>LLM: 対象フィールド更新用プロンプト
    LLM-->>ProfileAgent: 部分更新 JSON
    ProfileAgent->>ProfileAgent: マージ・整合性チェック
    ProfileAgent->>ProfileAgent: バックアップ保存
    ProfileAgent->>ProfileAgent: profiles/user_profile.json を上書き
    ProfileAgent->>ProfileAgent: セッションログ保存
    ProfileAgent-->>CLI: 更新結果を返す
```

### 9.3 `profile show`

```mermaid
sequenceDiagram
    participant CLI
    participant ProfileAgent

    CLI->>ProfileAgent: show_profile(format)
    ProfileAgent->>ProfileAgent: profiles/user_profile.json を読み込み
    alt format == "json"
        ProfileAgent->>ProfileAgent: JSON 整形
    else format == "raw"
        ProfileAgent->>ProfileAgent: 加工なしで返却
    else format == "text"
        ProfileAgent->>ProfileAgent: ハイライト付テキスト整形
    end
    ProfileAgent-->>CLI: 出力文字列
```

## 10. モジュール構成とアーキテクチャ

### 10.1 モジュール一覧

- `profile_agent.cli`
  - Typer ベースの CLI コマンド群。
  - セッションビルダー呼び出しと LangGraph ワークフロー実行のエントリーポイント。
- `profile_agent.session`
  - CLI からの入力値を正規化してセッション辞書を組み立てる。
  - 今後、セッション ID・タイムスタンプ・LangSmith 連携用メタデータの注入もこの層で担う。
- `profile_agent.workflow`
  - LangGraph グラフ定義 (`graph.py`) とステート (`state.py`)、各処理フェーズのノード (`nodes/`) を保持。
  - ノードは「入力収集」「欠損検知」「質問生成」「回答取り込み」「プロフィール生成」「スキーマ検証」「永続化」などで分割する。
- `profile_agent.schema`
  - プロフィール JSON のスキーマ定義とバリデーションロジックを集約する。
  - 現段階では `load_profile` で辞書入力をデータクラスへ変換し、必須フィールドの検証を行う。
  - Pydantic / JSON Schema など、採用するバリデーションツールの境界面を提供する。
- `profile_agent.prompts`
  - LLM 向けプロンプトテンプレートとプロファイル特有のフォーマット調整を保持する領域。
  - 他エージェントで共通化しづらい部分を閉じ込める。
- `agent_core.io`
  - ファイル入出力やバックアップ作成を担当する共通ユーティリティ。
  - プロフィールエージェント以外からも再利用できる抽象 API を提供する。
- `agent_core.llm`
  - LLM 呼び出し、LangSmith トレーシング、外部 API 連携などの共通サービス層。
  - プロンプト生成は各エージェント側（`profile_agent.prompts`）で行い、このモジュールにはモデル選定・リトライ制御・モニタリングといった横断的処理を収める。
- `profile_agent.main`
  - CLI 以外から利用する際の高レベル API を提供するファサードを想定。
  - `agent_core` の抽象コンポーネントと `profile_agent.workflow` を組み合わせて公開する。

### 10.2 モジュール間の関係

```mermaid
graph TD
    CLI["CLI<br/>profile_agent.cli"] --> Session["Session<br/>profile_agent.session"]
    Session --> Workflow["Workflow<br/>workflow.graph"]
    Workflow --> Collect["Collect<br/>nodes.collect_input"]
    Workflow --> Detect["Missing<br/>nodes.detect_missing"]
    Workflow --> Ask["Questions<br/>nodes.generate_questions"]
    Workflow --> Ingest["Answers<br/>nodes.ingest_answers"]
    Workflow --> Profile["Profile<br/>nodes.build_profile"]
    Workflow --> Validate["Validate<br/>nodes.validate_schema"]
    Workflow --> Persist["Persist<br/>nodes.persist_profile"]
    Collect --> IO["IO<br/>agent_core.io"]
    Persist --> IO
    Profile --> Services["LLM<br/>agent_core.llm"]
    Ask --> Services
    SchemaMod["Schema<br/>profile_agent.schema"] --> Validate
    SchemaMod --> Profile
    Prompts["Prompts<br/>profile_agent.prompts"] --> Profile
    Prompts --> Ask
    Services -.-> LangSmith["Tracing<br/>LangSmith"]
    IO -.-> Storage["Storage<br/>profiles/ etc."]
```
