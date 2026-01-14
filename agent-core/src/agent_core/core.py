"""コアロジックの呼び出し口を提供する。"""

from __future__ import annotations

from dataclasses import dataclass

from .context import ExecutionContext


@dataclass(frozen=True)
class CoreAgentService:
    """CLI 以外からも利用できるエージェント入口。"""

    def run_profile(self, context: ExecutionContext) -> ExecutionContext:
        """プロフィール実行の入口。"""
        if context.mode != "profile":
            raise ValueError("profile context is required")
        return context

    def run_job(self, context: ExecutionContext) -> ExecutionContext:
        """求人実行の入口。"""
        if context.mode != "job":
            raise ValueError("job context is required")
        return context

    def run_evaluate(self, context: ExecutionContext) -> ExecutionContext:
        """評価実行の入口。"""
        if context.mode != "evaluate":
            raise ValueError("evaluate context is required")
        return context
