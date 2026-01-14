# Technology Stack

## Architecture

- CLI 駆動の単一プロセス。LangGraph でワークフローを組み立て、StateGraph を用いたステートフル処理。
- プロフィール生成は「CLI → セッション辞書 → LangGraph ノード」の直列パイプライン。未実装ノードは警告のみで終了させることで拡張余地を確保。

## Core Technologies

- **Language**: Python 3.14
- **CLI Framework**: Typer（サブコマンド構成、option callback で version 表示）
- **Workflow**: LangGraph (StateGraph)

## Key Libraries

- `typer` … CLI 定義（profile create/update/show）。
- `langgraph` … ステート管理とノード遷移。

## Development Standards

### Type Safety
- 全関数・メソッドに型ヒント必須。`Literal` と `Annotated` で CLI 引数を明示。

### Code Quality
- `ruff check`（E/W/F/I）で lint。自動整形は原則手動対応。

### Testing
- `pytest -q`。CLI は `typer.testing.CliRunner` でヘルプ/バージョン表示を検証。

## Development Environment

### Required Tools
- Python 3.14
- uv（依存管理）

### Common Commands
```bash
uv sync          # 依存同期
pytest -q        # テスト
```

## Key Technical Decisions

- LangGraph ノードは工場関数で差し替え可能にし、テストや将来の実装差し込みを容易にする。
- プロフィールバリデーションはドラフト/確定の二段階。欠損は `missing_fields` に集約し、確定時に例外化。

---
_Document standards and patterns, not every dependency_
