"""プロフィール対話エージェント."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ..shared.context import ExecutionContext
from ..shared.conversation import ConversationStore
from .profile_tool import ProfileDraft, ProfileResult, ProfileToolImpl, detect_missing
from .prompts import profile_question


@dataclass(frozen=True)
class InterviewQuestion:
    """欠損項目に対する質問."""

    field: str
    prompt: str


def _build_questions(missing: list[str]) -> list[InterviewQuestion]:
    """欠損項目から質問を生成する。"""
    return [
        InterviewQuestion(field=item, prompt=profile_question(item))
        for item in missing
    ]


def _apply_answers(draft: ProfileDraft, answers: dict[str, Any]) -> ProfileDraft:
    """回答をドラフトに反映する。"""
    summary = draft.summary
    if "summary" in answers:
        summary = str(answers["summary"])

    career = list(draft.career)
    if "career" in answers:
        value = answers["career"]
        if isinstance(value, list):
            career = [str(item) for item in value]
        else:
            career = [str(value)]

    return ProfileDraft(
        metadata=draft.metadata,
        summary=summary,
        career=career,
        plan=list(draft.plan),
        age_band=draft.age_band,
        prefecture=draft.prefecture,
        certifications=list(draft.certifications),
    )


class ProfileAgentImpl:
    """対話補完フローを実装する。"""

    def __init__(
        self,
        *,
        tool: ProfileToolImpl,
        store: ConversationStore,
        max_attempts: int = 3,
    ) -> None:
        self._tool = tool
        self._store = store
        self._max_attempts = max_attempts

    def run_step(
        self,
        context: ExecutionContext,
        *,
        answers: dict[str, Any] | None,
        stop: bool,
        attempt: int,
    ) -> "ProfileInterviewResult":
        """対話フローの1ステップを実行して結果を返す。"""
        draft = self._tool.build(context)

        if answers:
            self._record_answers(answers)
            draft = _apply_answers(draft, answers)
        missing = detect_missing(draft)

        should_finalize = stop or attempt >= self._max_attempts or not missing
        if should_finalize:
            result = self._tool.finalize(draft)
            return ProfileInterviewResult(
                status="complete",
                questions=[],
                result=result,
                missing=list(result.missing),
            )

        questions = _build_questions(missing)
        self._record_questions(questions)
        return ProfileInterviewResult(
            status="in_progress",
            questions=questions,
            result=None,
            missing=missing,
        )

    def run(
        self,
        context: ExecutionContext,
        *,
        answers: dict[str, Any] | None,
        stop: bool,
        attempt: int,
    ) -> ProfileResult:
        """後方互換のため対話を完了させる。"""
        result = self.run_step(
            context,
            answers=answers,
            stop=True,
            attempt=attempt,
        )
        assert result.result is not None
        return result.result

    def _record_questions(self, questions: list[InterviewQuestion]) -> None:
        """質問を会話履歴に記録する。"""
        for question in questions:
            self._store.append(
                role="agent",
                content=question.prompt,
                metadata={"field": question.field},
            )

    def _record_answers(self, answers: dict[str, Any]) -> None:
        """回答を会話履歴に記録する。"""
        for field, answer in answers.items():
            self._store.append(
                role="user",
                content=str(answer),
                metadata={"field": field},
            )


@dataclass(frozen=True)
class ProfileInterviewResult:
    """対話ステップの実行結果."""

    status: Literal["in_progress", "complete"]
    questions: list[InterviewQuestion]
    result: ProfileResult | None
    missing: list[str]
