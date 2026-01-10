# Project Structure

## Organization Philosophy

- シンプルなパッケージ分割のレイヤー構造。`profile_agent` 配下に CLI / セッション構築 / ワークフロー / スキーマを明示的に分離。
- LangGraph ノードは `workflow/nodes/` に集約し、State と Graph 構築は別モジュールで責務分離。

## Directory Patterns

### CLI コマンド
**Location**: `src/profile_agent/cli/`
**Purpose**: Typer でサブコマンドを定義。オプションは `Annotated` で型と説明を併記。
**Example**: `app.py` で `profile create/update/show` を登録し、実装未満は `_not_implemented` で終了コード 1 を返す。

### ワークフロー
**Location**: `src/profile_agent/workflow/`
**Purpose**: LangGraph の State 定義 (`state.py`) と Graph 組立 (`graph.py`)、具体ノード (`nodes/`) を分離。
**Example**: `build_profile_workflow` はエントリと終了を明示し、未実装ノードは警告を state.warnings に積む。

### セッション構築
**Location**: `src/profile_agent/session/`
**Purpose**: CLI から渡す生入力を正規化し、ワークフロー向けの `session` 辞書を組み立てる。
**Example**: `builder.py` で空入力を禁止し、デフォルトパスやフラグを付与。

### スキーマ
**Location**: `src/profile_agent/schema/`
**Purpose**: プロフィール構造体（dataclass）とバリデーションロジックを一箇所にまとめる。
**Example**: `parse_profile` は欠損を集約した `ProfileDraft` を返し、確定時は `ProfileValidationError` を投げる。

## Naming Conventions

- モジュール: スネークケース（例: `session/builder.py`）。
- クラス: パスカルケース（`ProfileState`, `ProfileDraft`）。
- 定数: スクリームスネーク（`DEFAULT_PROFILE_PATH`）。
- テスト: 対応するモジュールに `test_*.py` を鏡写し配置。

## Import Organization

- パッケージ内は相対インポートで局所性を保つ（例: `from ..state import ProfileState`）。
- 外部ライブラリは標準→サードパーティ→ローカルの順でグルーピング。

## Code Organization Principles

- CLI とビジネスロジックを分離し、入力検証はセッションビルダーで早期に行う。
- LangGraph ノードは「入力前提が欠けたら例外」「未実装は warnings に残す」の二種類で明確化。
- ドメインデータ（プロフィール）は dataclass + 明示的バリデーションで一元管理。

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_
