"""CLI アプリケーションを提供する。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import uuid

import typer

from agent_core.profile.profile_agent import (
    InterviewQuestion,
    ProfileAgentImpl,
    ProfileInterviewResult,
)
from agent_core.profile.profile_tool import ProfileToolImpl
from agent_core.shared.context import ExecutionContext, build_execution_context
from agent_core.shared.conversation import ConversationStore, build_log_record
from agent_core.shared.log_writer import JsonLineLogWriter

app = typer.Typer()
profile_app = typer.Typer()
app.add_typer(profile_app, name="profile")

_STOP_WORDS = {"exit", "quit"}


@dataclass
class _InterviewState:
    payload: dict[str, Any]
    attempt: int
    run_id: str


def _seed_payload(text_inputs: list[str] | None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if text_inputs:
        summary = " ".join(text_inputs).strip()
        if summary:
            payload["summary"] = summary
    return payload


def _build_state(text_inputs: list[str] | None) -> _InterviewState:
    payload = _seed_payload(text_inputs)
    return _InterviewState(payload=payload, attempt=1, run_id=uuid.uuid4().hex)


def _merge_payload(payload: dict[str, Any], answers: dict[str, Any]) -> None:
    if "summary" in answers:
        payload["summary"] = str(answers["summary"])
    if "career" in answers:
        value = answers["career"]
        if isinstance(value, list):
            payload["career"] = [str(item) for item in value]
        else:
            payload["career"] = [str(value)]


def _prompt_answers(questions: list[InterviewQuestion]) -> tuple[dict[str, Any], bool]:
    answers: dict[str, Any] = {}
    for question in questions:
        response = typer.prompt(question.prompt)
        normalized = response.strip().lower()
        if normalized in _STOP_WORDS:
            return answers, True
        answers[question.field] = response
    return answers, False


def _format_missing(missing: list[str]) -> str:
    if not missing:
        return "なし"
    return ", ".join(missing)


def _print_summary(*, status: str, missing: list[str], output: Path) -> None:
    typer.echo(f"状態: {status}")
    typer.echo(f"欠損: {_format_missing(missing)}")
    typer.echo(f"保存先: {output}")


def _build_context(
    *,
    text_inputs: list[str] | None,
    payload: dict[str, Any],
    run_id: str,
) -> ExecutionContext:
    return build_execution_context(
        mode="profile",
        text_inputs=text_inputs,
        file_inputs=None,
        options={"profile_payload": payload},
        run_id=run_id,
    )


def _write_conversation_log(
    *,
    store: ConversationStore,
    run_id: str,
    log_path: Path,
) -> None:
    record = build_log_record(store, run_id=run_id)
    writer = JsonLineLogWriter(log_path=log_path, create_dirs=True)
    writer.write(record)


def _finalize_interview(
    *,
    step: ProfileInterviewResult,
    output: Path,
    store: ConversationStore,
    run_id: str,
    log_path: Path,
) -> None:
    assert step.result is not None
    _print_summary(status=step.result.status, missing=step.result.missing, output=output)
    _write_conversation_log(store=store, run_id=run_id, log_path=log_path)


def _run_non_interactive(
    *,
    agent: ProfileAgentImpl,
    store: ConversationStore,
    state: _InterviewState,
    text_inputs: list[str] | None,
    output: Path,
    log_path: Path,
) -> None:
    context = _build_context(
        text_inputs=text_inputs,
        payload=state.payload,
        run_id=state.run_id,
    )
    step = agent.run_step(context, answers=None, stop=True, attempt=state.attempt)
    _finalize_interview(
        step=step,
        output=output,
        store=store,
        run_id=state.run_id,
        log_path=log_path,
    )


def _run_interactive(
    *,
    agent: ProfileAgentImpl,
    store: ConversationStore,
    state: _InterviewState,
    text_inputs: list[str] | None,
    output: Path,
    log_path: Path,
) -> None:
    answers: dict[str, Any] | None = None
    while True:
        context = _build_context(
            text_inputs=text_inputs,
            payload=state.payload,
            run_id=state.run_id,
        )
        step = agent.run_step(
            context,
            answers=answers,
            stop=False,
            attempt=state.attempt,
        )
        if step.status == "complete":
            _finalize_interview(
                step=step,
                output=output,
                store=store,
                run_id=state.run_id,
                log_path=log_path,
            )
            return

        answers, stop = _prompt_answers(step.questions)
        _merge_payload(state.payload, answers)
        if stop:
            context = _build_context(
                text_inputs=text_inputs,
                payload=state.payload,
                run_id=state.run_id,
            )
            final_step = agent.run_step(
                context,
                answers=answers or None,
                stop=True,
                attempt=state.attempt,
            )
            _finalize_interview(
                step=final_step,
                output=output,
                store=store,
                run_id=state.run_id,
                log_path=log_path,
            )
            return

        state.attempt += 1


@profile_app.command("interview")
def profile_interview(
    text_inputs: list[str] | None = typer.Argument(None),
    output: Path = typer.Option(
        Path("profiles/profile.json"),
        "--output",
    ),
    log_path: Path = typer.Option(
        Path("logs/profile_interview.jsonl"),
        "--log-path",
    ),
    max_attempts: int = typer.Option(3, "--max-attempts"),
    non_interactive: bool = typer.Option(False, "--non-interactive"),
) -> None:
    """プロフィールの対話補完を実行する。"""
    state = _build_state(text_inputs)

    store = ConversationStore()
    tool = ProfileToolImpl(output_path=output)
    agent = ProfileAgentImpl(tool=tool, store=store, max_attempts=max_attempts)

    if non_interactive:
        _run_non_interactive(
            agent=agent,
            store=store,
            state=state,
            text_inputs=text_inputs,
            output=output,
            log_path=log_path,
        )
        return
    _run_interactive(
        agent=agent,
        store=store,
        state=state,
        text_inputs=text_inputs,
        output=output,
        log_path=log_path,
    )
