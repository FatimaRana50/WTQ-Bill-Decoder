"""Level 2: fact sheet extraction + question answering with a calculator tool."""
from __future__ import annotations

import ast
import logging
import math
import operator
from typing import Any

from . import prompts
from .llm import LLMClient, LLMError, parse_json

log = logging.getLogger(__name__)

# ---- safe calculator exposed to the model as a tool -------------------------------------------

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {
    "sum": lambda *a: sum(a[0]) if len(a) == 1 and isinstance(a[0], (list, tuple)) else sum(a),
    "avg": lambda *a: (sum(a[0]) / len(a[0])) if len(a) == 1 and isinstance(a[0], (list, tuple)) else sum(a) / len(a),
    "mean": lambda *a: (sum(a[0]) / len(a[0])) if len(a) == 1 and isinstance(a[0], (list, tuple)) else sum(a) / len(a),
    "min": min, "max": max, "abs": abs, "round": round, "len": len, "sqrt": math.sqrt,
    # list helpers so that counting/filtering is done by code, not by the model
    "count_gt": lambda xs, t: sum(1 for x in xs if x > t),
    "count_ge": lambda xs, t: sum(1 for x in xs if x >= t),
    "count_lt": lambda xs, t: sum(1 for x in xs if x < t),
    "count_le": lambda xs, t: sum(1 for x in xs if x <= t),
    "filter_gt": lambda xs, t: [x for x in xs if x > t],
    "filter_lt": lambda xs, t: [x for x in xs if x < t],
    "index_of_max": lambda xs: xs.index(max(xs)),
    "index_of_min": lambda xs: xs.index(min(xs)),
}


def _eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e) for e in node.elts]
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and not node.keywords:
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise ValueError("unsupported expression")


def calculate(expression: str) -> str:
    """Evaluate an arithmetic expression exactly. Supports + - * / ** %, parentheses, lists,
    and the functions sum, avg, min, max, abs, round, len, sqrt, count_gt/ge/lt/le(list, threshold),
    filter_gt/lt(list, threshold), index_of_max(list), index_of_min(list).
    Example: calculate("avg([239, 203, 187])") or calculate("569.62 / 3430.24 * 100").
    Returns the result as text."""
    try:
        result = _eval(ast.parse(expression.strip(), mode="eval").body)
    except Exception as exc:
        return f"error: {exc}"
    if isinstance(result, float):
        result = round(result, 6)
    return str(result)


# ---- fact sheet + answers ---------------------------------------------------------------------

def extract_facts(llm: LLMClient, image: tuple[bytes, str]) -> dict[str, Any]:
    try:
        facts = llm.generate_json(
            "Transcribe this bill into the fact sheet JSON described in your instructions.",
            images=[image], system=prompts.FACTS_SYSTEM,
        )
        if not isinstance(facts, dict):
            return {}
        for row in facts.get("usage_history") or []:  # units are never negative; a stray '-' belongs to the bill column
            if isinstance(row, dict) and isinstance(row.get("units"), (int, float)):
                row["units"] = abs(row["units"])
        return facts
    except LLMError as exc:
        log.warning("fact sheet failed (%s); answering from the image and Level 1 data only", exc)
        return {}


def plan_calculations(
    llm: LLMClient, image: tuple[bytes, str], bill: dict, facts: dict, questions: list[tuple[str, str]]
) -> dict[str, list[dict]]:
    """Ask the model WHAT to calculate, then run every expression in code (the model never does the maths)."""
    try:
        plan = llm.generate_json(prompts.plan_user_prompt(bill, facts, questions), images=[image], system=prompts.PLAN_SYSTEM)
    except Exception as exc:
        log.warning("calculation planning failed (%s); answering without computed values", exc)
        return {}
    results: dict[str, list[dict]] = {}
    for qid, items in (plan.items() if isinstance(plan, dict) else []):
        results[str(qid)] = [
            {"name": str(i.get("name", "")), "expression": str(i.get("expression", "")), "result": calculate(str(i.get("expression", "")))}
            for i in (items if isinstance(items, list) else []) if isinstance(i, dict)
        ]
    return results


def _parse_answers(text: str) -> dict[str, str]:
    data = parse_json(text)
    if isinstance(data, dict):  # tolerate {"Q1": "...", ...} or {"answers": [...]}
        data = data.get("answers", [{"question_id": k, "answer": v} for k, v in data.items()])
    return {str(d["question_id"]).strip(): str(d["answer"]).strip() for d in data if isinstance(d, dict) and d.get("answer")}


def answer_questions(
    llm: LLMClient, image: tuple[bytes, str], bill: dict, facts: dict, questions: list[tuple[str, str]]
) -> dict[str, str]:
    """Return {question_id: answer}. Every id is present; failures get an honest fallback sentence."""
    return answer_with_trace(llm, image, bill, facts, questions)[0]


def answer_with_trace(
    llm: LLMClient, image: tuple[bytes, str], bill: dict, facts: dict, questions: list[tuple[str, str]]
) -> tuple[dict[str, str], dict[str, list[dict]]]:
    """Like answer_questions, but also returns the calculations (expression + result) behind the answers."""
    calcs = plan_calculations(llm, image, bill, facts, questions)
    answers: dict[str, str] = {}
    try:
        text = llm.generate(prompts.qa_user_prompt(bill, facts, questions, calcs),
                            images=[image], system=prompts.QA_SYSTEM)
        answers = _parse_answers(text)
    except Exception as exc:
        log.warning("QA call failed: %s", exc)

    missing = [(qid, q) for qid, q in questions if qid not in answers]
    for qid, question in missing:  # retry stragglers one at a time
        try:
            text = llm.generate(prompts.qa_user_prompt(bill, facts, [(qid, question)], {qid: calcs.get(qid, [])}),
                                images=[image], system=prompts.QA_SYSTEM)
            answers.update(_parse_answers(text))
        except Exception as exc:
            log.warning("%s retry failed: %s", qid, exc)
        answers.setdefault(
            qid, "I could not produce a reliable answer to this question from the bill image, so I am not guessing."
        )
    return answers, calcs
