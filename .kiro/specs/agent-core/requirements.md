# Requirements Document

## Introduction
プロフィール生成・評価の中核エージェントを仕様駆動で整備し、CLI 入力からワークフロー処理、プロフィール構造化・検証までを一貫して扱えるようにする。

## Requirements

### Requirement 1: 入力とセッション構築
**Objective:** As a CLI user, I want text入力とオプションを正規化してセッションに格納したい, so that 後続のワークフローが前提を満たした状態で実行できる

#### Acceptance Criteria
1. When user provides text inputs via CLI, the Agent Core shall normalize non-empty strings, preserve order, and store them in `session.text_inputs`.
2. If `text_inputs` are missing or only whitespace, the Agent Core shall raise a validation error before starting the workflow.
3. When profile_path is not provided, the Agent Core shall set `session.profile_path` to `profiles/user_profile.json`.
4. While `target_fields` are specified, the Agent Core shall store them as a list in the session for downstream nodes.
5. Where `--force` flag is set, the Agent Core shall mark `session.force_overwrite` as true for subsequent save operations.

### Requirement 2: 入力チャンク化
**Objective:** As a workflow, I want text入力をチャンク化してノード間で扱いやすくしたい, so that 解析・生成ノードが入力を安全に消費できる

#### Acceptance Criteria
1. When the workflow enters `collect_input` and `session.input_chunks` is absent, the Agent Core shall create chunks with sequential `id`, `source="text"`, and original content.
2. While `input_chunks` already exist, the Agent Core shall skip chunk recreation to avoid duplication.
3. If `text_inputs` are absent when `collect_input` runs, the Agent Core shall raise an explicit error indicating the missing precondition.
4. The Agent Core shall preserve original ordering of text inputs in generated chunks.
5. Where multiple text inputs are provided, the Agent Core shall include each non-empty input as a distinct chunk.

### Requirement 3: プロフィールドラフト生成と欠損検出
**Objective:** As a profile processor, I want 生データを構造化し欠損を可視化したい, so that 不足項目を埋めるべき箇所を特定できる

#### Acceptance Criteria
1. When `parse_profile` receives mappings for metadata/summary/career, the Agent Core shall construct dataclass instances and return a `ProfileDraft`.
2. If required fields (metadata.name, summary.headline, summary.summary, career entries) are missing or blank, the Agent Core shall list them in `draft.missing_fields` without raising.
3. When `finalize_profile` is invoked with non-empty `missing_fields`, the Agent Core shall raise `ProfileValidationError` containing sorted field names.
4. While `draft.missing_fields` is empty, `finalize_profile` shall return a `Profile` without exceptions.
5. The Agent Core shall coerce primitive types safely (int/str), returning `None` on invalid conversions rather than raising.

### Requirement 4: ワークフロー構築と遷移
**Objective:** As a maintainer, I want LangGraph ワークフローを再現性高く構築・拡張したい, so that ノード差し替えや追加が安全に行える

#### Acceptance Criteria
1. When `build_profile_workflow` is called without custom factories, the Agent Core shall register `collect_input` and `validate_profile` nodes, set entry at `collect_input`, and finish at `validate_profile`.
2. Where custom node factories are provided, the Agent Core shall inject them in place of defaults without altering other edges.
3. If a node is not implemented, the Agent Core shall append a warning message to `state.warnings` and continue execution.
4. The Agent Core shall enforce `ProfileState` schema and shall raise an error if `session.profile_path` is missing at state initialization.
5. While the workflow runs, the Agent Core shall preserve state across nodes without mutating session keys other than those produced by the nodes.

### Requirement 5: CLI インターフェースとユーザー通知
**Objective:** As a CLI user, I want 一貫したコマンド挙動とエラー表示を得たい, so that 操作結果を理解し次の行動を選べる

#### Acceptance Criteria
1. When user invokes `career-agent --version`, the Agent Core shall print the package version and exit with code 0.
2. When user calls a profile subcommand that is not implemented, the Agent Core shall emit a message indicating it is under implementation to stderr and exit with code 1.
3. While help is requested (`--help`), the Agent Core shall list options for create/update/show including `--file`, `--fields`, `--no-interactive`, `--raw`, and format choices.
4. Where user passes `--raw` for show, the Agent Core shall propagate a raw-output indicator to downstream handling (even if the handler is stubbed).
5. If CLI parsing fails on an invalid option, the Agent Core shall rely on Typer to emit usage guidance and return a non-zero exit code.
