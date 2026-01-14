# Requirements Document

## Introduction
キャリアエージェント全体（プロフィール生成・求人解析・適合度評価）を仕様駆動で整備し、CLI から完結するツール/エージェント群として動作させる。コアとなる Profile Tool は LangGraph ワークフローで入力正規化・構造化・検証・保存を行い、Job Tool は求人を構造化する。対話補完は Profile Agent が担い、Evaluate Agent は適合度評価と LLM 要約を担当する。本仕様では LLM を介した評価結果のメタ評価（比較・要約）までを対象とし、人手向けのレポート表示や単純比較 UI は別スペック（Web アプリ）で扱う。

## Requirements

### Requirement 1 (Common): Execution Context per Component
**Objective:** 各実行ユニット（Profile Tool/Job Tool/Evaluate Agent）が前提を満たした状態で開始できるよう、モード別の実行コンテキストを用意する。

#### Acceptance Criteria
1. When a profile command is run with text inputs, the system shall normalize non-empty strings, preserve their order, and keep them in a profile-mode execution context.  
   - ※ profile 実行時は入力を正規化し順序を保ってプロファイル用コンテキストに保持する。
2. If a profile command is run with no user-provided inputs, the system shall start the interview flow with an empty input set instead of raising a precondition error.  
   - ※ profile 実行で入力が無くても、空入力のままヒアリングを開始する。
3. When a job-parse command is run with file inputs, the system shall verify readability, preserve order, and keep them in a job-mode context.  
   - ※ job parse ではファイルの存在/読込可否を確認し、順序を保ってジョブ用コンテキストに保持する。
4. When an evaluate command is run with profile and job inputs, the system shall require both, keep them in an evaluate-mode context, and raise an error if either is missing.  
   - ※ evaluate では両入力が必須で、欠けていれば開始前にエラーとする。
5. Where optional flags are provided (e.g., overwrite permission, update targets), the system shall map them into the current context and apply sensible defaults for omitted options.  
   - ※ オプションはコンテキストに反映し、未指定は妥当なデフォルトで補う。
6. The system shall expose core agent logic through a callable interface independent of the CLI, and the CLI shall invoke that interface.  
   - ※ コアロジックは CLI 非依存の呼び出し口として提供し、CLI はそれを呼び出す。

### Requirement 2 (Common): Conversation Block Management
**Objective:** ユーザー入力とエージェント応答を、役割と出所が明示された順序付きの会話ブロックとして一元管理し、追跡性と再利用性を高める。

#### Acceptance Criteria
1. The system shall manage exactly two block roles: user input and agent output.  
   - ※ ブロックの役割は「ユーザー入力」と「エージェント応答」の2種類に限定する。
2. All user-origin inputs (initial text, files, interview answers) shall be recorded as user blocks; any additional metadata is optional.  
   - ※ ユーザー起点の入力はユーザーブロックとして一元管理し、付加情報は必要に応じて任意で付与する。
3. Agent responses (warnings, summaries, prompts, etc.) shall be recorded as agent blocks with relevant metadata.  
   - ※ エージェントの応答は必要なメタを付けたエージェントブロックとして記録する。
4. The system shall preserve chronological order across all blocks (user and agent).  
   - ※ ユーザー/エージェント双方のブロックは時系列順を維持する。
5. If required user inputs are absent for modes that demand them (e.g., job parsing, evaluation), the system shall raise an explicit precondition error.  
   - ※ 入力が必須のモード（求人解析・評価など）では、入力欠如時に前提不足エラーとする。
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
3. The system shall save execution logs to the designated log destination, including questions, warnings, and a reference to the user inputs consumed in that run; sensitive data shall follow the project’s masking/hash policy.  
   - ※ 質問・警告に加え、その実行で消費したユーザー入力の参照を所定の保存先に残す（機微情報はマスク/ハッシュのポリシーに従う）。
4. The system shall write profiles in a human-readable, UTF-8 formatted form.  
   - ※ 可読な UTF-8 形式で書き出す。
5. If the save destination does not exist, the system shall create it or fail with a clear error.  
   - ※ 保存先が無ければ作成するか明示的にエラーを返す。

### Requirement 5 (Profile Tool): Profile Lifecycle (Build, Complete, Update)
**Objective:** Profile Tool はプロフィールを「構造化する → 必須欠損を洗い出す → 必要な領域だけ安全に更新する」一連の流れで扱い、常に整合性のとれたプロフィールを返す。対話補完は Profile Agent が担い、Tool は質問対象の欠損リストを提供する。

#### Acceptance Criteria
1. When raw profile information is provided, the system shall construct a structured profile covering metadata, summary, career, and plan.  
   - ※ 生のプロフィール情報を受け取ったら、メタデータ・サマリ・経歴・プランの4セクションを持つ構造化プロフィールに組み立てる。
2. If required profile elements are missing or empty, the system shall collect them as a missing list without raising immediately.  
   - ※ 必須項目の抜けや空値はエラーにせず「欠損リスト」として蓄える。
3. When finalizing the profile and missing items remain, the system shall save it as incomplete (with the missing list) rather than raising an error.  
   - ※ 確定時に欠損が残っていてもエラーにせず、欠損リスト付きの「未完了」として保存する。
4. When finalizing the profile and no missing items remain, the system shall save it as complete and return it.  
   - ※ 欠損がなければ「完了」として保存し、返す。
5. If primitive value conversion fails, the system shall treat the result as empty rather than throwing an exception.  
   - ※ 数値/文字列などの型変換に失敗しても例外にせず「空」として扱う。
6. If required profile items are missing, the system shall prepare follow-up questions for those gaps to be used by the Profile Agent before finalizing.  
   - ※ 欠損がある場合は、確定前に Profile Agent が使う不足項目の質問を用意する。
7. When answers are received, the system shall record them in the conversation history and re-evaluate missing items.  
   - ※ 回答を会話履歴に記録し、欠損リストを再計算する。
8. If the user ends the interview or attempts are exhausted, the system shall stop questioning and save the profile as incomplete with remaining gaps recorded.  
   - ※ ユーザーが終了する/試行上限に達したら質問を止め、残欠損を記録した未完了状態で保存する。
9. If no initial inputs are provided, the system shall initiate the interview to gather profile information and proceed with the same missing-field handling rules.  
   - ※ 初期入力が空の場合でもヒアリングを開始し、欠損処理は同じルールで行う。
10. When running in update mode, the system shall load the existing profile before applying changes.  
    - ※ 更新モードでは必ず既存プロフィールを読み込んでから変更を始める。
11. Where update targets are specified, the system shall limit regeneration and merging to those areas, leaving others unchanged.  
    - ※ 更新対象が指定されていれば、その範囲だけ再生成・マージし、他の部分は保護する。
12. If no existing profile is found in update mode, the system shall stop with an error before regeneration.  
    - ※ 既存プロフィールが無ければ再生成を始めずエラーにする。
13. When merging regenerated parts, the system shall keep untouched parts and return a coherent profile.  
    - ※ マージ後も未変更部分を保持した整合性のあるプロフィールを返す。
14. If update targets are unknown, the system shall warn and create or skip them according to policy (never silently drop them).  
    - ※ 更新対象が不明な場合は警告し、ポリシーに従って生成またはスキップする（黙殺しない）。
15. When no existing profile is present and a new profile is requested, the system shall build a profile from user inputs alone, apply the same missing-field handling, and save to the default profile destination.  
    - ※ 既存プロフィールが無い状態で新規作成する場合、ユーザー入力だけで組み立て、欠損処理は同じルールで行い、既定の保存先に保存する。
16. When age or address information is provided, the system shall store age as an age band and address as a prefecture-level value only.  
    - ※ 年齢や住所情報がある場合、年齢は年齢帯、住所は都道府県レベルに丸めて保持する。
17. When certifications are provided, the system shall store them as a list of strings in the profile.  
    - ※ 資格情報がある場合、文字列リストとしてプロフィールに保持する。

### Requirement 6 (Job Tool): Job and Company Parsing
**Objective:** Job Tool は求人入力を後続評価で使える構造化データに変換し、入力に含まれる会社情報を分離保持しつつ、必要に応じて許可された情報源から会社情報を補完する。求人検索はポリシーに反しない範囲でオプションとする。

#### Acceptance Criteria
1. When a job parsing request is issued with one or more job inputs, the system shall read each input and produce structured job data.  
   - ※ 求人入力を受けたら読み込み、構造化データを生成する。
2. If company-related information is present, the system shall extract it into a separate company section within the same job output.  
   - ※ 会社情報が含まれる場合は同一出力内で会社セクションとして分離して保持する。
3. If company information is missing or partial and the company-lookup option is enabled, the system shall attempt to enrich the company section using permitted sources (user-provided inputs or approved APIs) and record provenance; if no permitted source is available, it shall warn and proceed without enrichment.  
   - ※ 会社情報が不足しており会社参照オプションが有効な場合、許可された情報源（ユーザー提供や承認済みAPI）で補完を試み、出所を記録する。取得不能なら警告を出して補完せず続行する。
4. If no output destination is specified, the system shall save the result to the default job-data location.  
   - ※ 出力先未指定なら既定の求人データ保存先に保存する。
5. If a job input is missing or unreadable, the system shall emit an error and stop without creating output.  
   - ※ 入力が無い/読めない場合はエラーで中断し出力しない。
6. The system shall include source metadata (e.g., input identifier/path) and parsing timestamp in the output.  
   - ※ 元の識別子やパス、解析時刻などのメタを結果に含める。
7. Where multiple job inputs are provided, the system shall process each and write separate outputs without unintended overwrites.  
   - ※ 複数入力は個別に出力し、意図しない上書きをしない。
8. The system shall not crawl or scrape external job sites; job data and any company enrichment must come from user-supplied inputs or explicitly permitted APIs/sources.  
   - ※ 外部求人サイトのクローリングやスクレイピングは行わず、求人・会社補完ともユーザー提供または明示的に許可されたAPI/ソースのみを扱う。
9. Manually provided job text (e.g., user copy-paste) is accepted for processing, subject to the source’s terms of use.  
   - ※ ユーザーが手動で取得した求人テキスト（コピペ等）は、元サイトの利用規約に従う前提で受け付ける。

### Requirement 7 (Evaluate Agent): Suitability Scoring and LLM Summary
**Objective:** プロフィールと求人の構造化データ（Requirement 5/6 に準拠したスキーマ）を用いて適合度を算出し、LLM による自動フィルタ・重み付け・比較要約を通じて意思決定に活用できる形で提供する。

#### Acceptance Criteria
1. When an evaluation is requested with both profile data and job data, the system shall load them and produce evaluation results that include scores and rationale.  
   - ※ プロフィールと求人の両データを読み込み、スコアと根拠を含む評価結果を生成する。
2. If either required input is missing or invalid, the system shall return an error without emitting partial results.  
   - ※ どちらかが欠落・不正なら部分結果を出さずにエラーとする。
3. Where an output destination is specified, the system shall write the evaluation there; otherwise it shall save to the default evaluation storage, following the persistence policy in Requirement 4.  
   - ※ 出力先指定が無い場合は既定の評価保存先に保存し、保存ポリシーは Requirement 4 に従う。
4. The system shall record references to the profile and job sources in every evaluation output.  
   - ※ 評価結果には必ずプロフィール／求人の参照情報を含める。
5. If scoring cannot be completed (e.g., missing critical fields), the system shall emit a clear error and may list blocking elements.  
   - ※ 必須欠損などでスコア不可なら阻害要因を示すエラーを返す。
6. When a summary/comparison is requested over one or more evaluations, the system shall load the evaluations and use LLM to: (a) auto-select relevant items via natural-language filters, (b) apply weighting/ordering, and (c) produce a comparative summary of strengths, risks, and rationale.  
   - ※ 複数評価の要約/比較要求時は、LLM が自然言語フィルタと重み付けを適用し、強み・リスク・根拠を含む比較要約を生成する。
7. If only one evaluation is provided, the system shall generate a summary (not a comparison) and note that a single source was used.  
   - ※ 1件のみの場合は比較ではなく要約とし、単一ソース利用である旨を明記する。
8. If any evaluation input is missing or invalid, the system shall fail with a clear error before invoking LLM.  
   - ※ 不正/欠落があれば LLM 呼び出し前にエラーとする。
9. The system shall include provenance (sources, timestamp) in both the LLM prompt and the returned summary metadata.  
   - ※ ソースと時刻をプロンプトと結果メタに含める。
10. The system shall save LLM-produced summaries/comparisons to comparison storage (default timestamped) without altering source evaluations, following the persistence policy in Requirement 4.  
    - ※ 要約/比較は既定または指定の保存先に書き出し、元の評価は変更しない（保存ポリシーは Requirement 4 に従う）。
11. Human-facing rendering (e.g., HTML/Markdown UI) is out of scope and handled in a separate Web application specification.  
    - ※ 表示UIは別スペックで扱う。
