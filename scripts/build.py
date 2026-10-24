"""Generate a fully offline interview study page from the Markdown source."""

from __future__ import annotations

import html
from pathlib import Path
import re

import markdown


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "近期面试问题分类与参考答案.md"
OUTPUT = ROOT / "index.html"


def extract_questions(source: str) -> tuple[list[tuple[str, list[dict[str, str]]]], list[str]]:
    categories: list[tuple[str, list[dict[str, str]]]] = []
    questions: list[dict[str, str]] | None = None
    extras: list[str] = []
    current_title: str | None = None
    current_number: str | None = None
    current_lines: list[str] = []
    in_extra = False

    def finish() -> None:
        nonlocal current_title, current_number, current_lines
        if current_title is None:
            return
        if questions is None:
            raise ValueError(f"Question {current_number} has no category")
        body = "\n".join(current_lines).strip()
        questions.append({
            "number": current_number or "",
            "title": current_title,
            "body": markdown.markdown(body, extensions=["tables", "fenced_code"]),
        })
        current_title, current_number, current_lines = None, None, []

    for line in source.splitlines():
        category_match = re.match(r"^## ([一二三四五六]、.+)$", line)
        question_match = re.match(r"^### (\d+)\. (.+)$", line)
        if category_match:
            finish()
            questions = []
            categories.append((category_match.group(1), questions))
            in_extra = False
        elif question_match:
            finish()
            current_number, current_title = question_match.groups()
            in_extra = False
        elif line.startswith("## "):
            finish()
            in_extra = True
        elif current_title is not None:
            current_lines.append(line)
        elif in_extra:
            extras.append(line)

    finish()
    numbers = [int(q["number"]) for _, group in categories for q in group]
    if numbers != list(range(1, 34)):
        raise ValueError(f"Expected questions 1–33 exactly once, got {numbers}")
    return categories, extras


def build() -> None:
    categories, _ = extract_questions(SOURCE.read_text(encoding="utf-8"))
    nav = []
    sections = []
    for index, (name, group) in enumerate(categories, start=1):
        category_id = f"category-{index}"
        display_name = "六、大模型分布式与推理优化" if index == 6 else name
        safe_name = html.escape(display_name)
        nav.append(f'<a class="nav-link" href="#{category_id}"><span>{safe_name}</span><small>{len(group)}</small></a>')
        cards = []
        for question in group:
            number = question["number"]
            title = html.escape(question["title"])
            cards.append(
                f'<details class="qa-card" id="q-{number}" data-category="{index}">'
                f'<summary><span class="q-number">{int(number):02d}</span><span class="q-title">{title}</span>'
                '<span class="chevron" aria-hidden="true"></span></summary>'
                f'<div class="answer">{question["body"]}</div></details>'
            )
        sections.append(
            f'<section class="category" id="{category_id}"><div class="section-heading">'
            f'<h2>{safe_name}</h2><span class="section-count">{len(group)} 题</span></div>'
            + "\n".join(cards) + "</section>"
        )

    template = (ROOT / "scripts" / "template.html").read_text(encoding="utf-8")
    page = template.replace("<!-- NAV -->", "\n".join(nav)).replace("<!-- QUESTIONS -->", "\n".join(sections))
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Generated {OUTPUT} ({sum(len(group) for _, group in categories)} questions)")


if __name__ == "__main__":
    build()
