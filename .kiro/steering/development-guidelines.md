# Development Guidelines (Domain-Specific)

開発ルールの要約を steering として保持する。詳細は `development_guidelines.md` を参照。

## Workflow & Testing
- TDD 前提：テスト起点で書き、失敗確認 → 実装 → 再テスト → リファクタ。
- テストは `tests/` をプロダクトと鏡写しパスで配置し、主要ケースはパラメタライズで網羅。
- `pytest -q` を基本コマンド。外部依存（LLM など）はモックで隔離。
- 各テストに目的と前提を docstring で明示。

## Coding Standards
- Python 3.14 / uv 管理。全シンボルに型ヒント必須、公開 API は mypy `--strict` を目標。
- PEP8 の主要ルールを尊重しつつレビューで例外判断。アウトパラメータ的な副作用は禁止（複数戻りはタプル/結果オブジェクト）。
- 公開/複雑処理には簡潔な docstring を付ける。必要に応じプライベートにも目的を補足。
- コードコメントとテストの docstring は日本語で記述する（エラーメッセージは英語でも可）。

## Quality Tools
- `ruff check` で E/W/F/I を検出。`ruff --fix`/`ruff format` はデフォルト不使用（手動修正）。
- 依存追加は `uv add` / `uv add --dev`、更新後は `uv lock` をコミット。

## Exceptions & Logging
- CLI/エージェント層は `logging` 利用、`print` はデバッグ/テスト専用。
- `except Exception` で握りつぶさず、標準 or 独自例外にマッピングして再送出。
- 例外メッセージにはユーザー影響とリカバリー手段を含め、セッションログに必要情報を残す。

## Repo Conventions
- 実装は `src/` 直下で機能単位に分割。テストは鏡写しパス。共通テストデータは `tests/fixtures/`（実データ厳禁）。
- ブランチは原則 1 機能 1 ブランチ、`feature/<short-desc>` 命名。

## Security & Data
- API キーや個人情報は `.env` など外部管理し、リポジトリに含めない。
- プロフィール/セッションログはダミーデータで扱い、本番データを入れない。

---
_Patterns over lists_
