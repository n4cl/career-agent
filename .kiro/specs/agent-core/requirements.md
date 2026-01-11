# Requirements Document

## Introduction
キャリアエージェント全体（プロフィール生成・求人解析・適合度評価）を仕様駆動で整備し、CLI から完結するエージェント群として動作させる。コアとなる Profile Agent は LangGraph ワークフローで入力正規化・構造化・検証・保存を行い、Job Agent は求人を構造化、Evaluate Agent は適合度評価を行う。本仕様では LLM を介した評価結果のメタ評価（比較・要約）までを対象とし、人手向けのレポート表示や単純比較 UI は別スペック（Web アプリ）で扱う。

## Requirements

### Requirement 1 (Common): Execution Context per Agent
**Objective:** Ensure each agent run (Profile/Job/Evaluate) starts with a clean, mode-specific execution context so that preconditions are satisfied before the workflow executes.

#### Acceptance Criteria
1. When a profile command is run with text inputs, the system shall normalize non-empty strings, preserve their order, and keep them in a profile-mode context.  
   - ※ profile 実行時は入力を正規化し順序を保ってプロファイル用コンテキストに保持する。
2. When a job-parse command is run with file inputs, the system shall verify readability, preserve order, and keep them in a job-mode context.  
   - ※ job parse ではファイルの存在/読込可否を確認し、順序を保ってジョブ用コンテキストに保持する。
3. When an evaluate command is run with profile and job inputs, the system shall require both, keep them in an evaluate-mode context, and raise an error if either is missing.  
   - ※ evaluate では両入力が必須で、欠けていれば開始前にエラーとする。
4. Where optional flags are provided (e.g., overwrite permission, update targets, interactive mode), the system shall map them into the current context and apply sensible defaults for omitted options.  
   - ※ オプションはコンテキストに反映し、未指定は妥当なデフォルトで補う。

### Requirement 2 (Common): Conversation Block Management
**Objective:** Keep user inputs and agent outputs in a single ordered conversation block list with clear roles and sources, enabling traceability and reuse across nodes.

#### Acceptance Criteria
1. When input collection begins with no existing blocks, the system shall create user blocks with sequential identifiers, role=user, source=text, and original content.  
   - ※ 初期収集時にブロックが無ければ連番・role=user・source=text で保持する。
2. Where file inputs are provided, the system shall add user blocks with source=file, preserving order and file metadata.  
   - ※ ファイル入力は順序とメタを保って role=user・source=file とする。
3. Where interactive answers are provided, the system shall append user blocks with source=qa, including question identifiers and answers.  
   - ※ ヒアリング回答は role=user・source=qa で質問ID付きブロックとして追記する。
4. When the agent emits feedback or intermediate summaries, the system shall append agent blocks with source=agent_output and related metadata.  
   - ※ エージェントの応答は role=agent・source=agent_output として追加する。
5. If required user inputs are absent, the system shall raise an explicit precondition error.  
   - ※ ユーザー入力が無い場合は前提不足エラーとする。
6. While processing, the system shall preserve the chronological order of all blocks.  
   - ※ 会話ブロックは時系列順を保持する。
7. Allowed block sources are text, file, qa (role=user) and agent_output (role=agent); new sources require explicit requirement updates.  
   - ※ source は text/file/qa（user）と agent_output（agent）に限定し、拡張は要件追加で行う。

### Requirement 3 (Common): Workflow Construction
**Objective:** Provide a reproducible LangGraph workflow that can be safely extended or customized.

#### Acceptance Criteria
1. The default workflow shall start with input collection and finish with validation.  
   - ※ デフォルトで開始・終了を定める。
2. Where custom nodes are provided, the system shall replace defaults without altering other transitions.  
   - ※ カスタム指定時も他の遷移は維持する。
3. If an unimplemented step is reached, the system shall record a warning and continue execution.  
   - ※ 未実装は警告を残して継続する。
4. If required prerequisites for initializing state are missing, the system shall raise an error before starting the workflow.  
   - ※ 必須前提が無ければ開始前にエラー。
5. While executing, the system shall mutate only intended state elements, leaving unrelated state unchanged.  
   - ※ 不要な状態を書き換えない。

### Requirement 4 (Common): Persistence, Backup, Logging
**Objective:** Handle saves, backups, and trace logs safely to prevent data loss and unclear operations.

#### Acceptance Criteria
1. If a profile already exists and overwrite is not allowed, the system shall abort saving with an error.  
   - ※ 上書き禁止ならエラーで中断。
2. Where overwriting is allowed, the system shall back up the existing profile before writing a new one.  
   - ※ 上書き時は先にバックアップを取る。
3. The system shall save execution logs (including questions and warnings) to the designated log destination.  
   - ※ 質問・警告を含むログを所定の保存先に残す。
4. The system shall write profiles in a human-readable, UTF-8 formatted form.  
   - ※ 可読な UTF-8 形式で書き出す。
5. If the save destination does not exist, the system shall create it or fail with a clear error.  
   - ※ 保存先が無ければ作成するか明示的にエラーを返す。

### Requirement 5 (Profile Agent): Profile Structuring and Missing Detection
**Objective:** Build a structured profile and surface missing required elements.

#### Acceptance Criteria
1. When raw profile information is provided, the system shall construct a structured profile covering metadata, summary, career, and plan.  
   - ※ 生データをメタデータ・サマリ・経歴・プランを含む構造に組み立てる。
2. If required profile elements are missing or empty, the system shall collect them as a missing list without raising immediately.  
   - ※ 必須欠損は一覧化し、即時エラーにしない。
3. When finalizing and missing items remain, the system shall report an error.  
   - ※ 確定時に欠損が残ればエラー。
4. When finalizing and no missing items remain, the system shall return the profile without exception.  
   - ※ 欠損がなければ正常に返す。
5. If primitive value conversion fails, the system shall treat the result as empty rather than throwing an exception.  
   - ※ 型変換失敗は空扱いとし例外にしない。

### Requirement 6 (Profile Agent): Interactive Completion
**Objective:** Fill missing profile information through optional dialogue and allow the user to stop.

#### Acceptance Criteria
1. If required items are missing and interactive mode is enabled, the system shall prepare follow-up questions for those gaps before finalizing.  
   - ※ 欠損＋対話モード時は不足項目への追質問を用意する。
2. When answers are received, the system shall record them in the conversation history and re-evaluate missing items.  
   - ※ 回答を記録し欠損を再判定する。
3. If the user ends the interview or attempts are exhausted, the system shall stop questioning and record remaining gaps as warnings.  
   - ※ 打ち切り時は残りの欠損を警告として残す。
4. Where interactive mode is disabled, the system shall skip question generation and keep missing items as warnings while continuing processing.  
   - ※ 非対話モードでは質問せず警告のみ残す。
5. The system shall log asked questions and answers for traceability.  
   - ※ 質問と回答を履歴に残す。

### Requirement 7 (Profile Agent): Partial Update
**Objective:** Update only requested profile parts without harming other areas.

#### Acceptance Criteria
1. When running in update mode, the system shall load the existing profile before applying changes.  
   - ※ 更新開始時に現行プロフィールを読む。
2. Where update targets are specified, the system shall limit regeneration and merging to those areas, leaving others unchanged.  
   - ※ 指定範囲のみ書き換え、他は保持する。
3. If no existing profile is found, the system shall stop with an error before regeneration.  
   - ※ 既存が無ければ開始せずエラー。
4. When merging regenerated parts, the system shall keep untouched parts and return a coherent profile.  
   - ※ マージ後も整合したプロフィールを返す。
5. If update targets are unknown, the system shall warn and create or skip them according to policy (never silently drop them).  
   - ※ 未知指定は警告し、方針に従い生成またはスキップする。

### Requirement 8 (Job Agent): Job Parsing
**Objective:** Convert job inputs into structured data usable by later evaluation.

#### Acceptance Criteria
1. When `job parse --file <path>` is run, the system shall read the job input and produce structured job data.  
   - ※ 求人入力を読み込み、構造化データを生成する。
2. If no output path is provided, the system shall save the result to a default job-data location.  
   - ※ 出力先未指定なら既定の保存先に保存する。
3. If the input file is missing or unreadable, the system shall emit an error and stop without creating output.  
   - ※ 入力が無い/読めない場合はエラーで中断し出力しない。
4. The system shall include metadata such as source path and parsing timestamp in the job output.  
   - ※ 元パスと解析時刻をメタとして含める。
5. Where multiple job inputs are provided, the system shall process each and write separate outputs without unintended overwrites.  
   - ※ 複数入力は個別に出力し、意図しない上書きをしない。

### Requirement 9 (Evaluate Agent): Suitability Scoring
**Objective:** Produce evaluation data from profile and job inputs with clear rationale.

#### Acceptance Criteria
1. When `evaluate score --profile <path> --job <path>` is run, the system shall load both inputs and produce evaluation data including scores and rationale.  
   - ※ プロフィールと求人を読み込み、スコアと根拠を含む評価データを生成する。
2. If either input is missing or invalid, the system shall return an error without emitting partial results.  
   - ※ いずれかが無効ならエラーとし部分的な結果を出さない。
3. Where an output path is provided, the system shall write the evaluation there; otherwise it shall save to a default evaluations location.  
   - ※ 出力先未指定なら既定の評価保存先に保存する。
4. The system shall record references to the profile/job sources in the evaluation output.  
   - ※ 評価結果に利用元の参照情報を含める。
5. If scoring cannot be completed (e.g., missing critical fields), the system shall emit a clear error and may list blocking fields.  
   - ※ 必須欠損などでスコア不可なら阻害要因を示すエラーを返す。

### Requirement 10 (Meta Evaluation): LLM-Based Comparison and Summary
**Objective:** Provide LLM-generated comparisons/summaries of evaluation results for downstream decision-making.

#### Acceptance Criteria
1. When `evaluate summarize --evals <path...>` is run, the system shall load the evaluation results and prompt LLM to produce a comparative summary (strengths, risks, rationale).  
   - ※ 評価結果を読み込み、LLM に強み・リスク・適合理由の比較要約を生成させる。
2. If only one evaluation is provided, the system shall produce a summary (not a comparison) and note that a single source was used.  
   - ※ 1件のみなら要約とし、単一ソースである旨を明記する。
3. If any evaluation input is missing or invalid, the system shall fail with a clear error before calling LLM.  
   - ※ 不正/欠落があれば LLM 呼び出し前にエラーとする。
4. The system shall include provenance (sources, timestamp) in the LLM prompt and returned summary metadata.  
   - ※ ソースと時刻をプロンプトと結果メタに含める。
5. The system shall save the LLM-produced summary/comparison to a comparisons output path (default timestamped) without altering source evaluations.  
   - ※ 要約/比較を既定または指定の保存先に書き出し、元の評価は変更しない。
6. Human-facing rendering (e.g., HTML/Markdown UI) is out of scope and handled in a separate Web application specification.  
   - ※ 表示UIは別スペックで扱う。
