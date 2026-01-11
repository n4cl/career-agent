# Requirements Document

## Introduction
キャリアエージェント全体（プロフィール生成・求人解析・適合度評価）を仕様駆動で整備し、CLI から完結するエージェント群として動作させる。コアとなる Profile Agent は LangGraph ワークフローで入力正規化・構造化・検証・保存を行い、Job Agent は求人を構造化、Evaluate Agent は適合度評価を行う。本仕様では LLM を介した評価結果のメタ評価（比較・要約）までを対象とし、人手向けのレポート表示や単純比較 UI は別スペック（Web アプリ）で扱う。

## Requirements

### Requirement 1: エージェント別の入力と実行コンテキスト構築
**Objective:** 各エージェント呼び出しごとに独立した実行コンテキスト（process context）を組み立て、必要前提を満たした形でワークフローに渡したい。そうすることで、Profile/Job/Evaluate の個別フローが安全に開始できる。

#### Acceptance Criteria
1. When a profile command is run with text inputs, the system shall normalize non-empty strings, preserve their order, and keep them in a profile-mode execution context.
   - ※ profile 実行時は入力を正規化し順序を保ってプロファイル用コンテキストに保持する。
2. When `job parse --file <paths...>` is run, the system shall verify each file is readable, preserve the given order, and keep them in a job-mode context.
   - ※ job parse ではファイルの存在/読込可否を確認し、順序を保ってジョブ用コンテキストに保持する。
3. When `evaluate score --profile <path> --job <path>` is run, the system shall require both inputs, keep them in an evaluation-mode context, and raise a validation error if either is missing.
   - ※ evaluate では両入力が必須で、欠けていれば開始前にエラーとする。
4. Where optional flags are provided (e.g., overwrite permission, update targets, interactive mode), the system shall map them into the current context and apply sensible defaults for omitted options.
   - ※ オプションはコンテキストに反映し、未指定は妥当なデフォルトで補う。

### Requirement 2: 入出力の構造化（会話ブロック）
**Objective:** ユーザー起点の入力とエージェント応答を単一の順序付き「会話ブロック」として保持し、出所・役割を明示したままノード間で扱えるようにしたい。これによりデバッグやコンテキスト再利用が容易になる。

#### Acceptance Criteria
1. When the workflow begins collecting input and no conversation blocks exist, the system shall create user blocks with sequential identifiers, role=user, source=text, and original content.
   - ※ 開始時にブロックが無ければ連番・role=user・source=text で元テキストを保持する。
2. Where file inputs are provided, the system shall read their contents, preserve path/label, and add user blocks with source=file in the given order.
   - ※ ファイル入力は順序とパス/ラベルを保ったまま role=user・source=file として追加する。
3. Where interactive Q&A answers are provided, the system shall append user blocks with source=qa that include question identifiers and answers.
   - ※ ヒアリング回答は role=user・source=qa で質問ID付きブロックとして追記する。
4. When the agent produces intermediate outputs for feedback or logging, the system shall append agent blocks with source=agent_output containing the message and related metadata.
   - ※ エージェントの応答（警告・要約など）は role=agent・source=agent_output で追加する。
5. If required user inputs are absent (e.g., no text/file/qa), the system shall raise an explicit error indicating the missing precondition.
   - ※ ユーザー入力が無い場合は前提不足エラーとする。
6. While processing conversation blocks, the system shall preserve their original ordering to reflect the conversation flow.
   - ※ 会話ブロックは時系列順を保持する。
7. The system shall limit block sources to text, file, qa (role=user) and agent_output (role=agent); additional sources require explicit requirement updates.
   - ※ source は text/file/qa（user）と agent_output（agent）に限定し、拡張は要件追加で行う。

### Requirement 3: プロフィールドラフト生成と欠損検出
**Objective:** プロフィール処理者として、生データを構造化し欠損を可視化したい。そうすることで、不足項目を埋めるべき箇所を特定できる。

#### Acceptance Criteria
1. When raw profile information is provided, the system shall construct a structured profile that covers metadata, summary, career, and plan sections.
   - ※ 生データをメタデータ・サマリ・経歴・プランを含む構造に組み立てる。
2. If required profile elements are missing or empty, the system shall collect them as a missing list without raising immediately.
   - ※ 必須欠損は一覧化し、即時エラーにしない。
3. When finalizing the profile and missing items remain, the system shall report an error.
   - ※ 確定時に欠損が残ればエラーとする。
4. When finalizing the profile and no missing items remain, the system shall return the profile without exception.
   - ※ 欠損がなければ例外なく返す。
5. If primitive value conversion fails, the system shall treat the result as empty rather than throwing an exception.
   - ※ 型変換失敗は空扱いとし例外にしない。

### Requirement 4: ヒアリングと欠損補完
**Objective:** エージェントとして、欠損情報を対話で補完し、ユーザーの判断で打ち切れるようにしたい。そうすることで、必要十分なプロフィールを得つつユーザー負荷を抑えられる。

#### Acceptance Criteria
1. If required items are missing and interactive mode is enabled, the system shall prepare follow-up questions for those gaps before finalizing.
   - ※ 欠損＋対話モード時は不足項目への追質問を用意する。
2. When answers are received, the system shall record them in the conversation history and re-evaluate missing items.
   - ※ 回答を記録し、欠損を再判定する。
3. If the user ends the interview or attempts are exhausted, the system shall stop questioning and record remaining gaps as warnings.
   - ※ 打ち切り時は残りの欠損を警告として残す。
4. Where interactive mode is disabled, the system shall skip question generation and keep missing items as warnings while continuing processing.
   - ※ 非対話モードでは質問を出さず、欠損を警告として残したまま進める。
5. The system shall log asked questions and answers for later traceability.
   - ※ 質問と回答を履歴に残す。

### Requirement 4: ワークフロー構築と遷移
**Objective:** メンテナとして、LangGraph ワークフローを再現性高く構築・拡張したい。そうすることで、ノード差し替えや追加を安全に行える。

#### Acceptance Criteria
1. The default workflow shall start with input collection and finish with validation.
   - ※ デフォルトで開始・終了を定める。
2. Where custom nodes are provided, the system shall replace defaults without altering other transitions.
   - ※ カスタム指定時も他の遷移は維持する。
3. If an unimplemented step is reached, the system shall record a warning and continue execution.
   - ※ 未実装は警告を残して継続する。
4. If required prerequisites for initializing state are missing, the system shall raise an error before starting the workflow.
   - ※ 必須前提が無ければ開始前にエラー。
5. While executing, the system shall mutate only the intended state elements, leaving unrelated state unchanged.
   - ※ 不要な状態を書き換えない。

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
1. When running in update mode, the system shall load the existing profile before applying changes.
   - ※ 更新開始時に現行プロフィールを読む。
2. Where update targets are specified, the system shall limit regeneration and merging to those areas, leaving others unchanged.
   - ※ 指定範囲だけ書き換え、他は保持する。
3. If no existing profile is found in update mode, the system shall stop with an error before regeneration.
   - ※ 既存が無ければ開始せずエラー。
4. When merging regenerated parts, the system shall keep untouched parts and return a coherent profile.
   - ※ マージ後も整合したプロフィールを返す。
5. If update targets are unknown, the system shall warn and create or skip them according to policy (never silently drop them).
   - ※ 未知指定は警告し、方針に従い生成またはスキップする。

### Requirement 7: 永続化・バックアップ・ログ
**Objective:** システムとして、保存時の衝突やロールバック、トレースを安全に扱いたい。そうすることで、データ破損や操作不明瞭を防げる。

#### Acceptance Criteria
1. If a profile already exists and overwrite is not allowed, the system shall abort saving with an error.
   - ※ 上書き禁止ならエラーで中断する。
2. Where overwriting is allowed, the system shall back up the existing profile before writing the new one.
   - ※ 上書き時は先にバックアップを取る。
3. The system shall save execution logs (including questions and warnings) to the designated log destination.
   - ※ 質問・警告を含むログを所定の保存先に残す。
4. The system shall write profiles in a human-readable, UTF-8 formatted form.
   - ※ 可読な UTF-8 形式で書き出す。
5. If the save destination does not exist, the system shall create it or fail with a clear error.
   - ※ 保存先が無ければ作成するか明示的にエラーを返す。

### Requirement 8: 求人解析（Job Agent）
**Objective:** 求人入力を構造化データに変換し、後続の評価で再利用したい。そうすることで、求人情報を一貫した形式で扱える。

#### Acceptance Criteria
1. When user runs `job parse --file <path>`, the system shall read the file and produce structured job data.
   - ※ `job parse --file` で求人ファイルを読み込み、構造化データを生成する。
2. If no output path is provided, the system shall save the result to a default job-data location.
   - ※ 出力先未指定なら既定の求人データ保存先に保存する。
3. If the input file is missing or unreadable, the system shall emit an error and stop without creating output.
   - ※ 入力ファイルが無い/読めない場合はエラーを出し、出力を作らない。
4. The system shall include metadata such as source path and parsing timestamp in the job output.
   - ※ 解析結果に元パスと解析時刻をメタデータとして含める。
5. Where multiple job files are provided, the system shall process each and write separate outputs without overwriting unless explicitly directed.
   - ※ 複数ファイル指定時は個別に出力し、明示されない限り上書きしない。

### Requirement 9: 適合度評価（Evaluate Agent）
**Objective:** プロフィールと求人データから適合度を算出し、機械可読な結果を得たい。そうすることで、後続レポートや比較に利用できる。

#### Acceptance Criteria
1. When user runs `evaluate score --profile <path> --job <path>`, the system shall load both inputs and produce evaluation data including scores and rationale.
   - ※ `evaluate score` でプロフィールと求人を読み込み、スコアと根拠を含む評価データを生成する。
2. If either input is missing or invalid, the system shall return an error without emitting partial results.
   - ※ いずれかの入力が無効ならエラーとし、中途半端な結果を出さない。
3. Where an output path is provided, the system shall write the evaluation there; otherwise it shall save to a default evaluations location.
   - ※ 出力先指定が無ければ既定の evaluations 保存先に保存する。
4. The system shall record references to the profile/job sources in the evaluation output.
   - ※ 評価結果に使用したプロフィール/求人の参照情報を含める。
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
5. The system shall save the LLM-produced summary/comparison to a comparisons output path (default timestamped) without altering source evaluation files.
   - ※ 生成した要約/比較を既定または指定の保存先に書き出し、元の評価ファイルは変更しない。
6. Human-facing rendering (HTML/Markdown UI) is out of scope for this spec and will be handled in a separate Web application specification.
   - ※ 人向けの表示（HTML/Markdown UI）は別の Web アプリ仕様で扱う。
