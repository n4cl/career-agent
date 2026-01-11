# Requirements Document

## Introduction
キャリアエージェント全体（プロフィール生成・求人解析・適合度評価）を仕様駆動で整備し、CLI から完結するエージェント群として動作させる。コアとなる Profile Agent は LangGraph ワークフローで入力正規化・構造化・検証・保存を行い、Job Agent は求人を構造化、Evaluate Agent は適合度評価を行う。本仕様では LLM を介した評価結果のメタ評価（比較・要約）までを対象とし、人手向けのレポート表示や単純比較 UI は別スペック（Web アプリ）で扱う。

## Requirements

### Requirement 1 (Common): Execution Context per Agent
**Objective:** 各エージェント実行（Profile/Job/Evaluate）が前提を満たした状態で開始できるよう、モード別の実行コンテキストを用意する。

#### Acceptance Criteria
1. When a profile command is run with text inputs, the system shall normalize non-empty strings, preserve their order, and keep them in a profile-mode execution context.  
   - ※ profile 実行時は入力を正規化し順序を保ってプロファイル用コンテキストに保持する。
2. When a job-parse command is run with file inputs, the system shall verify readability, preserve order, and keep them in a job-mode context.  
   - ※ job parse ではファイルの存在/読込可否を確認し、順序を保ってジョブ用コンテキストに保持する。
3. When an evaluate command is run with profile and job inputs, the system shall require both, keep them in an evaluate-mode context, and raise an error if either is missing.  
   - ※ evaluate では両入力が必須で、欠けていれば開始前にエラーとする。
4. Where optional flags are provided (e.g., overwrite permission, update targets, interactive mode), the system shall map them into the current context and apply sensible defaults for omitted options.  
   - ※ オプションはコンテキストに反映し、未指定は妥当なデフォルトで補う。

### Requirement 2 (Common): Conversation Block Management
**Objective:** ユーザー入力とエージェント応答を、役割と出所が明示された順序付きの会話ブロックとして一元管理し、追跡性と再利用性を高める。

#### Acceptance Criteria
1. The system shall manage exactly two block roles: user input and agent output.  
   - ※ ブロックの役割は「ユーザー入力」と「エージェント応答」の2種類に限定する。
2. All user-origin inputs (initial text, files, interactive answers) shall be recorded as user blocks; any additional metadata is optional.  
   - ※ ユーザー起点の入力はユーザーブロックとして一元管理し、付加情報は必要に応じて任意で付与する。
3. Agent responses (warnings, summaries, prompts, etc.) shall be recorded as agent blocks with relevant metadata.  
   - ※ エージェントの応答は必要なメタを付けたエージェントブロックとして記録する。
4. The system shall preserve chronological order across all blocks (user and agent).  
   - ※ ユーザー/エージェント双方のブロックは時系列順を維持する。
5. If required user inputs are absent, the system shall raise an explicit precondition error.  
   - ※ ユーザー入力が無い場合は前提不足エラーとする。
6. Introducing additional block roles shall require a requirements update.  
   - ※ 新たなブロック役割を導入する場合は要件更新を要する。

### Requirement 3 (Common): Workflow Construction
**Objective:** LangGraph ワークフローを再現性高く組み立て、拡張・差し替えを安全に行えるようにする。

#### Acceptance Criteria
1. The default workflow shall provide at least input collection followed by validation as a minimal runnable path.  
   - ※ 入力収集→検証の最小フローをデフォルトで持つ。
2. If required prerequisites for initializing state are missing, the system shall raise an error before starting the workflow.  
   - ※ 必須前提が無ければ開始前にエラー。
3. While executing, the system shall mutate only the state elements intended for that step, leaving unrelated state unchanged.  
   - ※ 各ステップは担当する状態のみを更新し、不要な状態を書き換えない。

### Requirement 4 (Common): Persistence, Backup, Logging
**Objective:** 保存・バックアップ・ログを安全に扱い、データ損失や不明瞭な操作を防ぐ。

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

### Requirement 5 (Profile Agent): Profile Lifecycle (Build, Complete, Update)
**Objective:** プロフィールを構造化し、欠損を明示し、対話で補完し、必要な領域のみを安全に更新して整合性を保つ。

#### Acceptance Criteria
1. When raw profile information is provided, the system shall construct a structured profile covering metadata, summary, career, and plan.  
   - ※ 生データをメタデータ・サマリ・経歴・プランを含む構造に組み立てる。
2. If required profile elements are missing or empty, the system shall collect them as a missing list without raising immediately.  
   - ※ 必須欠損は一覧化し、即時エラーにしない。
3. When finalizing the profile and missing items remain, the system shall report an error.  
   - ※ 確定時に欠損が残ればエラー。
4. When finalizing the profile and no missing items remain, the system shall return the profile without exception.  
   - ※ 欠損がなければ正常に返す。
5. If primitive value conversion fails, the system shall treat the result as empty rather than throwing an exception.  
   - ※ 型変換失敗は空扱いとし例外にしない。
6. If required profile items are missing and interactive mode is enabled, the system shall prepare follow-up questions for those gaps before finalizing.  
   - ※ 欠損＋対話モード時は不足項目への追質問を用意する。
7. When answers are received, the system shall record them in the conversation history and re-evaluate missing items.  
   - ※ 回答を記録し、欠損を再判定する。
8. If the user ends the interview or attempts are exhausted, the system shall stop questioning and record remaining gaps as warnings.  
   - ※ 打ち切り時は残りの欠損を警告として残す。
9. Where interactive mode is disabled, the system shall skip question generation and keep missing items as warnings while continuing processing.  
   - ※ 非対話モードでは質問せず、欠損を警告として残したまま進める。
10. When running in update mode, the system shall load the existing profile before applying changes.  
    - ※ 更新開始時に現行プロフィールを読む。
11. Where update targets are specified, the system shall limit regeneration and merging to those areas, leaving others unchanged.  
    - ※ 指定範囲のみ書き換え、他は保持する。
12. If no existing profile is found in update mode, the system shall stop with an error before regeneration.  
    - ※ 既存が無ければ開始せずエラー。
13. When merging regenerated parts, the system shall keep untouched parts and return a coherent profile.  
    - ※ マージ後も整合したプロフィールを返す。
14. If update targets are unknown, the system shall warn and create or skip them according to policy (never silently drop them).  
    - ※ 未知指定は警告し、方針に従い生成またはスキップする。

### Requirement 6 (Job Agent): Job Parsing
**Objective:** 求人入力を、後続の評価で利用できる構造化データに変換する。

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

### Requirement 7 (Evaluate Agent): Suitability Scoring and LLM Summary
**Objective:** プロフィールと求人の構造化データ（Requirement 5/6 で得られた出力と同等スキーマ）を用いて適合度を算出し、LLM による自動フィルタ・重み付け・比較要約を通じて意思決定に活用できる形で提供する。

#### Acceptance Criteria
1. When `evaluate score --profile <path> --job <path>` is run, the system shall load both inputs and produce evaluation data including scores and rationale.  
   - ※ プロフィールと求人を読み込み、スコアと根拠を含む評価データを生成する。
2. If either input is missing or invalid, the system shall return an error without emitting partial results.  
   - ※ いずれかが無効ならエラーとし部分的な結果を出さない。
3. Where an output path is provided, the system shall write the evaluation there; otherwise it shall save to a default evaluations location, following the persistence policy in Requirement 4.  
   - ※ 出力先未指定なら既定の評価保存先に保存し、保存ポリシーは Requirement 4 に従う。
4. The system shall record references to the profile/job sources in the evaluation output.  
   - ※ 評価結果に利用元の参照情報を含める。
5. If scoring cannot be completed (e.g., missing critical fields), the system shall emit a clear error and may list blocking fields.  
   - ※ 必須欠損などでスコア不可なら阻害要因を示すエラーを返す。
6. When `evaluate summarize --evals <path...>` is run, the system shall load evaluation results and use LLM to: (a) auto-select relevant evaluations via natural-language filters, (b) apply weighting/ordering, and (c) produce a comparative summary (strengths, risks, rationale).  
   - ※ `evaluate summarize` で評価結果を読み込み、LLM が自然言語フィルタや重み付けを自動適用しつつ比較要約を生成する。
7. If only one evaluation is provided, the system shall produce a summary (not a comparison) and note that a single source was used.  
   - ※ 1件のみなら要約とし、単一ソースである旨を明記する。
8. If any evaluation input is missing or invalid, the system shall fail with a clear error before calling LLM.  
   - ※ 不正/欠落があれば LLM 呼び出し前にエラーとする。
9. The system shall include provenance (sources, timestamp) in the LLM prompt and returned summary metadata.  
   - ※ ソースと時刻をプロンプトと結果メタに含める。
10. The system shall save the LLM-produced summary/comparison to a comparisons output path (default timestamped) without altering source evaluations, following the persistence policy in Requirement 4.  
    - ※ 要約/比較を既定または指定の保存先に書き出し、元の評価は変更しない（保存ポリシーは Requirement 4 に従う）。
11. Human-facing rendering (e.g., HTML/Markdown UI) is out of scope and handled in a separate Web application specification.  
    - ※ 表示UIは別スペックで扱う。
