from __future__ import annotations

import re

from backend.models.schemas import ProcessedPaper, UserLevel


def _equation_snippets(text: str) -> list[str]:
    candidates = re.findall(r"[^\n]{0,120}[=][^\n]{0,120}", text)
    unique: list[str] = []
    for item in candidates:
        cleaned = " ".join(item.split())
        if cleaned and cleaned not in unique:
            unique.append(cleaned)
    return unique[:3]


def _beginner_rewrite(text: str) -> str:
    return f"In plain language: {text}"


def _intermediate_rewrite(text: str) -> str:
    return f"Conceptually: {text}"


def _advanced_rewrite(text: str) -> str:
    return f"Technical detail: {text}"


def adapt_level(paper: ProcessedPaper) -> ProcessedPaper:
    adapted = paper.model_copy(deep=True)

    if adapted.user_level == UserLevel.beginner:
        adapted.core_idea.summary = _beginner_rewrite(adapted.core_idea.summary)
        adapted.core_idea.intuition = (
            "Think of the model as a recipe: each stage transforms raw ingredients into a final prediction."
        )
        adapted.problem.description = _beginner_rewrite(adapted.problem.description)
        adapted.problem.why_it_matters = _beginner_rewrite(adapted.problem.why_it_matters)
        for step in adapted.implementation.steps:
            step.description = _beginner_rewrite(step.description)
            step.level_notes = "Focus on what each step does before worrying about implementation details."
        adapted.architecture.description = _beginner_rewrite(adapted.architecture.description)
        adapted.tools.notes = "Tooling names are listed only when explicitly mentioned in the paper text."
        adapted.analogy = "Imagine building a house from a blueprint: each section tells you what to build next."

    elif adapted.user_level == UserLevel.intermediate:
        adapted.core_idea.summary = _intermediate_rewrite(adapted.core_idea.summary)
        adapted.problem.description = _intermediate_rewrite(adapted.problem.description)
        for step in adapted.implementation.steps:
            step.description = _intermediate_rewrite(step.description)
            step.level_notes = "Track data flow and component responsibilities between steps."
        adapted.architecture.description = _intermediate_rewrite(adapted.architecture.description)
        adapted.analogy = "Like assembling modular services: each block has a clear interface and role."

    else:
        adapted.core_idea.summary = _advanced_rewrite(adapted.core_idea.summary)
        adapted.problem.description = _advanced_rewrite(adapted.problem.description)
        for step in adapted.implementation.steps:
            step.description = _advanced_rewrite(step.description)
            step.level_notes = "Evaluate optimization choices, assumptions, and trade-offs for each stage."
        adapted.architecture.description = _advanced_rewrite(adapted.architecture.description)
        eq_text = " ".join(chunk.text for chunk in adapted.chunks)
        equations = _equation_snippets(eq_text)
        if equations:
            adapted.architecture.description = (
                f"{adapted.architecture.description} Equations referenced in paper: {'; '.join(equations)}"
            )
        adapted.analogy = "No analogy applied for advanced level."

    return adapted
