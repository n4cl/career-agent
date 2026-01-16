"""CLI アプリケーションを提供する。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

from agent_core.profile.profile_agent import InterviewQuestion, ProfileAgentImpl
from agent_core.profile.profile_tool import ProfileToolImpl
from agent_core.shared.context import ExecutionContext, build_execution_context
from agent_core.shared.conversation import ConversationStore

app = typer.Typer()
profile_app = typer.Typer()
app.add_typer(profile_app, name="profile")

_STOP_WORDS = {"exit", "quit"}


@dataclass
class _InterviewState:
    payload: dict[str, Any]
    attempt: int


def _seed_payload(text_inputs: list[str] | None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if text_inputs:
        summary = " ".join(text_inputs).strip()
        if summary:
            payload["summary"] = summary
    return payload


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


def _build_context(
    *,
    text_inputs: list[str] | None,
    payload: dict[str, Any],
) -> ExecutionContext:
    return build_execution_context(
        mode="profile",
        text_inputs=text_inputs,
        file_inputs=None,
        options={"profile_payload": payload},
    )


@profile_app.command("interview")
def profile_interview(
    text_inputs: list[str] | None = typer.Argument(None),
    output: Path = typer.Option(
        Path("profiles/profile.json"),
        "--output",
    ),
    max_attempts: int = typer.Option(3, "--max-attempts"),
    non_interactive: bool = typer.Option(False, "--non-interactive"),
) -> None:
    """プロフィールの対話補完を実行する。"""
    payload = _seed_payload(text_inputs)
    state = _InterviewState(payload=payload, attempt=1)

    store = ConversationStore()
    tool = ProfileToolImpl(output_path=output)
    agent = ProfileAgentImpl(tool=tool, store=store, max_attempts=max_attempts)

    if non_interactive:
        context = _build_context(text_inputs=text_inputs, payload=state.payload)
        agent.run_step(context, answers=None, stop=True, attempt=state.attempt)
        return

    answers: dict[str, Any] | None = None
    while True:
        context = _build_context(text_inputs=text_inputs, payload=state.payload)
        step = agent.run_step(
            context,
            answers=answers,
            stop=False,
            attempt=state.attempt,
        )
        if step.status == "complete":
            return

        answers, stop = _prompt_answers(step.questions)
        _merge_payload(state.payload, answers)
        if stop:
            context = _build_context(text_inputs=text_inputs, payload=state.payload)
            agent.run_step(
                context,
                answers=answers or None,
                stop=True,
                attempt=state.attempt,
            )
            return

        state.attempt += 1
