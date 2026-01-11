# Requirements Document

## Introduction
キャリアエージェント全体（プロフィール生成・求人解析・適合度評価）を仕様駆動で整備し、CLI から完結するエージェント群として動作させる。コアとなる Profile Agent は LangGraph ワークフローで入力正規化・構造化・検証・保存を行い、Job Agent は求人を構造化、Evaluate Agent は適合度評価を行う。本仕様では LLM を介した評価結果のメタ評価（比較・要約）までを対象とし、人手向けのレポート表示や単純比較 UI は別スペック（Web アプリ）で扱う。

## Requirements

### Requirement 1: エージェント別の入力と実行コンテキスト構築
**Objective:** 各エージェント呼び出しごとに独立した実行コンテキスト（process context）を組み立て、必要前提を満たした形でワークフローに渡したい。そうすることで、Profile/Job/Evaluate の個別フローが安全に開始できる。

#### Acceptance Criteria
1. When user runs a profile command with text inputs, the system shall normalize non-empty strings, preserve order, and place them in the profile execution context, marking the context as profile mode.
   - ※ profile 実行時は入力を正規化し順序を保ったままプロファイル用の実行コンテキストに格納し、profile モードとして扱う。
2. When user runs `job parse --file <paths...>`, the system shall verify each file is readable, preserve the given order, and record them in the job execution context, marking the context as job mode.
   - ※ job parse ではファイルの存在/読込可否を確認し、順序を保ってジョブ用コンテキストに記録し、job モードとして扱う。
3. When user runs `evaluate score --profile <path> --job <path>`, the system shall require both inputs, record them in the evaluation execution context, mark the context as evaluate mode, and raise a validation error if either is missing.
   - ※ evaluate ではプロフィールと求人の両入力を必須とし、欠けていれば開始前にエラーとする。両方そろった場合に評価用コンテキストとして扱う。
4. Where optional flags are provided (e.g., `--force`, `--target-fields`, `--no-interactive`), the system shall map them into the current execution context and apply sensible defaults for omitted options (e.g., default output path, default interactive mode).
   - ※ 各種オプションは実行中のコンテキストに反映し、未指定は適切なデフォルト（保存先、対話モードなど）を補う。

### Requirement 2: 入出力の構造化（会話ブロック）
**Objective:** ユーザー起点の入力とエージェント応答を単一の順序付き「会話ブロック」として保持し、出所・役割を明示したままノード間で扱えるようにしたい。これによりデバッグやコンテキスト再利用が容易になる。

#### Acceptance Criteria
1. When the workflow begins collecting input and no conversation blocks exist, the Agent Core shall create user blocks with sequential identifiers, role=user, source=text, and the original content.
   - ※ 入力収集開始時にブロックが無ければ、連番・role=user・source=text で元テキストを保持したブロックを作る。
2. Where file inputs are provided via CLI options, the Agent Core shall read file contents, preserve path/label, and add user blocks with source=file in the given order.
   - ※ `--file` 指定の内容は読込み順を保持し、role=user・source=file のブロックとして追加する。
3. Where interactive Q&A answers are provided, the Agent Core shall append user blocks with source=qa that include question id and answer text.
   - ※ ヒアリング回答は role=user・source=qa で質問ID付きブロックとして追記する。
4. When the agent produces intermediate outputs intended for user feedback or logging (e.g., validation warnings, evaluation summaries), the Agent Core shall append agent blocks with source=agent_output containing the message and related metadata.
   - ※ エージェント側の応答（警告や要約など）は role=agent・source=agent_output としてメッセージとメタ情報を含めて追加する。
5. If required user inputs are absent (e.g., no text/file/qa inputs), the Agent Core shall raise an explicit error indicating the missing precondition.
   - ※ ユーザー入力（text/file/qa）が無い場合は前提不足のエラーを出す。
6. The Agent Core shall preserve original ordering of all blocks (user and agent) to reflect the conversation flow.
   - ※ user/agent を含む全ブロックは会話の時系列順を保持する。
7. Allowed block sources are text, file, qa (role=user) and agent_output (role=agent); additional sources require explicit requirement updates.
   - ※ source は text/file/qa（role=user）と agent_output（role=agent）に限定し、拡張は要件追加時に行う。

### Requirement 3: プロフィールドラフト生成と欠損検出
**Objective:** プロフィール処理者として、生データを構造化し欠損を可視化したい。そうすることで、不足項目を埋めるべき箇所を特定できる。

#### Acceptance Criteria
1. When `parse_profile` receives mappings for metadata/summary/career, the Agent Core shall construct dataclass instances and return a `ProfileDraft`.
   - ※ metadata/summary/career のマッピングを受け取ったら dataclass に組み立て `ProfileDraft` を返す。
2. If required fields (metadata.name, summary.headline, summary.summary, career entries) are missing or blank, the Agent Core shall list them in `draft.missing_fields` without raising.
   - ※ 必須項目が欠けていたら例外にせず `draft.missing_fields` に列挙する。
3. When `finalize_profile` is invoked with non-empty `missing_fields`, the Agent Core shall raise `ProfileValidationError` containing sorted field names.
   - ※ `missing_fields` が残ったまま `finalize_profile` を呼ぶと、欠損フィールド名を含む `ProfileValidationError` を投げる。
4. While `draft.missing_fields` is empty, `finalize_profile` shall return a `Profile` without exceptions.
   - ※ 欠損が空なら例外なく `Profile` を返す。
5. The Agent Core shall coerce primitive types safely (int/str), returning `None` on invalid conversions rather than raising.
   - ※ int/str への変換は安全に行い、失敗時は例外でなく `None` を返す。

### Requirement 4: ヒアリングと欠損補完
**Objective:** エージェントとして、欠損情報を対話で補完し、ユーザーの判断で打ち切れるようにしたい。そうすることで、必要十分なプロフィールを得つつユーザー負荷を抑えられる。

#### Acceptance Criteria
1. When `missing_fields` is non-empty and `session.interactive` is true, the Agent Core shall prepare follow-up questions targeting the missing fields before finalizing the profile.
   - ※ 欠損があり対話モードなら、確定前に不足フィールド向けの質問を用意する。
2. When answers to prepared questions are received, the Agent Core shall append them as `source="qa"` chunks and re-evaluate `missing_fields`.
   - ※ 質問への回答を受けたら QA チャンクとして追記し、欠損を再評価する。
3. If the user opts to end the interview or the maximum attempt count is reached, the Agent Core shall stop asking and record remaining `missing_fields` in warnings.
   - ※ ユーザー終了宣言または最大試行超過で質問を打ち切り、残りの欠損を warnings に記録する。
4. Where `session.interactive` is false, the Agent Core shall skip question generation and record `missing_fields` as warnings without halting the workflow.
   - ※ 非対話モードでは質問生成をスキップし、欠損を警告として記録したまま処理を進める。
5. The Agent Core shall log each asked question with `id`, `field`, `prompt`, and `answer` into the session log.
   - ※ 質問ID・対象フィールド・質問文・回答をセッションログに残す。

### Requirement 4: ワークフロー構築と遷移
**Objective:** メンテナとして、LangGraph ワークフローを再現性高く構築・拡張したい。そうすることで、ノード差し替えや追加を安全に行える。

#### Acceptance Criteria
1. When `build_profile_workflow` is called without custom factories, the Agent Core shall register `collect_input` and `validate_profile` nodes, set entry at `collect_input`, and finish at `validate_profile`.
   - ※ デフォルトでは `collect_input` を開始、`validate_profile` を終了として登録する。
2. Where custom node factories are provided, the Agent Core shall inject them in place of defaults without altering other edges.
   - ※ カスタムノードが渡された場合は既存エッジを保ったまま差し替える。
3. If a node is not implemented, the Agent Core shall append a warning message to `state.warnings` and continue execution.
   - ※ 未実装ノードは `state.warnings` に警告を追加しつつ処理を続行する。
4. The Agent Core shall enforce `ProfileState` schema and shall raise an error if `session.profile_path` is missing at state initialization.
   - ※ State 初期化時に `session.profile_path` が無ければエラーを上げる。
5. While the workflow runs, the Agent Core shall preserve state across nodes without mutating session keys other than those produced by the nodes.
   - ※ 実行中はノードが生成するキー以外のセッション値を不要に書き換えない。

### Requirement 5: CLI インターフェースとユーザー通知
**Objective:** CLI 利用者として、一貫したコマンド挙動とエラー表示を得たい。そうすることで、操作結果を理解し次の行動を選べる。

#### Acceptance Criteria
1. When user invokes `career-agent --version`, the Agent Core shall print the package version and exit with code 0.
   - ※ `--version` でパッケージバージョンを表示し、終了コード0で終了する。
2. When user calls a profile subcommand that is not implemented, the Agent Core shall emit a message indicating it is under implementation to stderr and exit with code 1.
   - ※ 未実装サブコマンドは「実装中」と stderr に出し、終了コード1で終了する。
3. While help is requested (`--help`), the Agent Core shall list options for create/update/show including `--file`, `--fields`, `--no-interactive`, `--raw`, and format choices.
   - ※ `--help` では create/update/show の各オプション（`--file`, `--fields`, `--no-interactive`, `--raw`, 表示形式）を案内する。
4. Where user passes `--raw` for show, the Agent Core shall propagate a raw-output indicator to downstream handling (even if the handler is stubbed).
   - ※ show の `--raw` 指定は後続処理に「生出力」フラグとして伝播させる（ハンドラがスタブでも保持）。
5. If CLI parsing fails on an invalid option, the Agent Core shall rely on Typer to emit usage guidance and return a non-zero exit code.
   - ※ 無効オプションでのパース失敗時は Typer のメッセージを出し、非0で終了する。

### Requirement 6: プロフィール更新（部分更新）
**Objective:** 既存プロフィールを持つ利用者として、指定フィールドだけを安全に更新したい。そうすることで、不要な領域を壊さずに差分反映できる。

#### Acceptance Criteria
1. When running in update mode, the Agent Core shall load the existing profile from `profile_path` before applying any changes.
   - ※ update モードでは処理開始前に既存プロフィールを読み込む。
2. Where `target_fields` are specified, the Agent Core shall limit regeneration and merging to those fields, preserving other fields unchanged.
   - ※ `target_fields` があれば、その範囲だけ再生成・マージし、他は保持する。
3. If the existing profile file is missing in update mode, the Agent Core shall raise an error before attempting regeneration.
   - ※ プロフィールが存在しない場合は再生成を始める前にエラーとする。
4. When merging regenerated fields, the Agent Core shall retain untouched fields and return/update a coherent Profile structure.
   - ※ マージ時は未対象フィールドを保持したまま整合した Profile を返す／保存する。
5. Where `target_fields` reference unknown paths, the Agent Core shall surface a warning and either create or skip them according to configuration (without silently discarding input).
   - ※ 不明なフィールド指定は警告し、設定に従い生成またはスキップする（黙殺しない）。

### Requirement 7: 永続化・バックアップ・ログ
**Objective:** システムとして、保存時の衝突やロールバック、トレースを安全に扱いたい。そうすることで、データ破損や操作不明瞭を防げる。

#### Acceptance Criteria
1. When creating a profile and a file already exists at `profile_path` without `force_overwrite`, the Agent Core shall abort with an error.
   - ※ 作成時に既存ファイルがあり `--force` が無ければエラーで中断する。
2. Where a profile file exists and overwrite is allowed, the Agent Core shall first copy it to `profiles/backups/<timestamp>.json` before writing the new file.
   - ※ 上書き時は先にバックアップへコピーしてから新規を書き込む。
3. The Agent Core shall save session logs to `profiles/session_logs/<timestamp>_<mode>.json` including `session_id`, `mode`, questions, and warnings.
   - ※ セッションログを `session_id`・モード・質問・警告入りで `profiles/session_logs/` に保存する。
4. The Agent Core shall write profile files in UTF-8 with human-readable formatting (e.g., 2-space indent).
   - ※ プロフィール出力は UTF-8 かつ可読フォーマット（例: 2 スペースインデント）で保存する。
5. If the target directories for profile, backup, or session logs are missing, the Agent Core shall create them or raise a clear error before writing.
   - ※ 保存先ディレクトリが無ければ作成するか、明示的エラーを返す。

### Requirement 8: 求人解析（Job Agent）
**Objective:** 求人入力を構造化データに変換し、後続の評価で再利用したい。そうすることで、求人情報を一貫した形式で扱える。

#### Acceptance Criteria
1. When user runs `job parse --file <path>`, the system shall read the file and produce structured job JSON.
   - ※ `job parse --file` で求人ファイルを読み込み、構造化 JSON を生成する。
2. If `--out` is not provided, the system shall save output to `job_data/<job-id or timestamp>.json`.
   - ※ `--out` 未指定時は `job_data/<job-id または timestamp>.json` に保存する。
3. If the input file is missing or unreadable, the system shall emit an error and stop without creating output.
   - ※ 入力ファイルが無い/読めない場合はエラーを出し、出力を作らない。
4. The system shall preserve metadata such as source path and parsing timestamp in the job JSON.
   - ※ 解析結果に元パスと解析時刻をメタデータとして含める。
5. Where multiple job files are provided, the system shall process each and write separate outputs without overwriting unless explicitly directed.
   - ※ 複数ファイル指定時は個別に出力し、明示されない限り上書きしない。

### Requirement 9: 適合度評価（Evaluate Agent）
**Objective:** プロフィールと求人データから適合度を算出し、機械可読な結果を得たい。そうすることで、後続レポートや比較に利用できる。

#### Acceptance Criteria
1. When user runs `evaluate score --profile <path> --job <path>`, the system shall load both JSONs and produce an evaluation JSON including scores and rationale.
   - ※ `evaluate score` でプロフィールと求人 JSON を読み込み、スコアと根拠を含む評価 JSON を生成する。
2. If either input path is missing or invalid, the system shall return an error without emitting partial results.
   - ※ いずれかの入力が無効ならエラーとし、中途半端な結果を出さない。
3. Where `--out` is provided, the system shall write the evaluation to that path; otherwise it shall default to `evaluations/<timestamp>.json`.
   - ※ `--out` 指定がなければ `evaluations/<timestamp>.json` に保存する。
4. The system shall record references to the profile/job sources (paths or IDs) inside the evaluation JSON.
   - ※ 評価 JSON に使用したプロフィール/求人のパスやIDを記録する。
5. If scoring cannot be completed (e.g., missing critical fields), the system shall emit a clear error and may include a list of blocking fields.
   - ※ 重要フィールド欠損などでスコアできない場合は、阻害要因を示したエラーを返す。

### Requirement 10: 評価結果の LLM メタ評価（比較・要約）
**Objective:** 複数の適合度評価結果を LLM で要約・比較し、洞察をテキスト出力したい。そうすることで、Web アプリ側での表示や意思決定に活用できる。

#### Acceptance Criteria
1. When user runs `evaluate summarize --evals <path...>`, the system shall load the evaluation JSON files and prompt LLM to produce a comparative summary (strengths, risks, suitability rationale).
   - ※ `evaluate summarize` で複数評価JSONを読み込み、LLM に強み/リスク/適合理由の比較要約を生成させる。
2. If only one evaluation is provided, the system shall produce an LLM summary (not a comparison) and note that only a single source was available.
   - ※ 1件のみなら比較ではなく要約を生成し、単一ソースである旨を明記する。
3. If any evaluation file is missing or invalid, the system shall fail with a clear error listing offending paths before calling LLM.
   - ※ 不正・欠落ファイルがあれば LLM 呼び出し前にエラーで止め、問題パスを示す。
4. The system shall include provenance (source paths/IDs, timestamp) in the LLM prompt and in the returned summary metadata.
   - ※ プロンプトと結果メタにソースパス/IDと生成時刻を含める。
5. The system shall save the LLM-produced summary/comparison to `comparisons/<timestamp>.json` (or `--out` if provided) without altering source evaluation files.
   - ※ 生成した要約/比較を `comparisons/<timestamp>.json`（`--out`指定時はそのパス）に保存し、元評価ファイルは変更しない。
6. Human-facing rendering (HTML/Markdown UI) is out of scope for this spec and will be handled in a separate Web application specification.
   - ※ 人向けの表示（HTML/Markdown UI）は別の Web アプリ仕様で扱う。
