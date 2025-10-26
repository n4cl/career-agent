career-agent
===

`career-agent` は、あなたのプロフィールと求人情報を基に、求人との適合性を評価するツールです。
これにより、客観的な視点からキャリア選択の意思決定を支援します。

## 開発環境セットアップ

このリポジトリでは Python 3.13 (`.python-version` 参照) と uv を前提とします。uv のインストール済みであることを想定し、以下の手順で環境を準備してください。

1. **依存関係の同期**
   ```bash
   uv sync
   ```

2. **仮想環境の有効化**
   - macOS / Linux: `source .venv/bin/activate`
   - Windows (PowerShell): `.\.venv\Scripts\activate`

3. **動作確認**
   ```bash
   pytest -q
   ```
   テストが通ればセットアップ完了です。

### 依存追加時のルール

- 本番依存: `uv add <package>`
- 開発依存 (lint/テスト用など): `uv add --dev <package>`
- 依存を更新したら `uv lock` を実行し、`uv.lock` をコミットしてください。
