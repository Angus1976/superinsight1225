#!/usr/bin/env python3
"""
Replay StrReplace chain for 文档/开发流程/生产上线综合测试计划表-2026.md from a Cursor
agent transcript (.jsonl). Used to restore the doc when git has no history for it.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TRANSCRIPT_DEFAULT = Path.home() / ".cursor/projects/Users-angusliu-superdata/agent-transcripts/7fac7030-e5a8-4a48-8f34-81345e3fbace/7fac7030-e5a8-4a48-8f34-81345e3fbace.jsonl"
OUT_DEFAULT = Path(__file__).resolve().parents[1] / "文档/开发流程/生产上线综合测试计划表-2026.md"
TARGET_SUFFIX = "生产上线综合测试计划表-2026.md"


def get_initial_write(transcript: Path) -> str:
    best = ""
    best_len = 0
    with transcript.open() as f:
        for line in f:
            if TARGET_SUFFIX not in line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = o.get("message", {})
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") != "tool_use":
                    continue
                if part.get("name") != "Write":
                    continue
                inp = part.get("input")
                if not isinstance(inp, dict):
                    continue
                p = inp.get("path", "")
                if not p.endswith(TARGET_SUFFIX):
                    continue
                c = inp.get("contents")
                if isinstance(c, str) and len(c) > best_len:
                    best, best_len = c, len(c)
    if not best:
        sys.exit("No Write found for plan doc in transcript")
    return best


def iter_str_replaces(transcript: Path):
    with transcript.open() as f:
        for lineno, line in enumerate(f, 1):
            if TARGET_SUFFIX not in line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("role") != "assistant":
                continue
            msg = o.get("message", {})
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") != "tool_use":
                    continue
                if part.get("name") != "StrReplace":
                    continue
                inp = part.get("input")
                if not isinstance(inp, dict):
                    continue
                p = inp.get("path", "")
                if not p.endswith(TARGET_SUFFIX):
                    continue
                old = inp.get("old_string")
                new = inp.get("new_string")
                if not isinstance(old, str) or not isinstance(new, str):
                    continue
                yield lineno, old, new


def replace_a6_line(text: str, new_line: str) -> str:
    lines = text.splitlines(keepends=True)
    out = []
    for line in lines:
        if re.match(r"^\| A6\s*\|", line.lstrip()):
            out.append(new_line.strip() + ("\n" if line.endswith("\n") else ""))
            continue
        out.append(line)
    return "".join(out)


def replace_section4_p0_p1(text: str, new_section: str) -> str | None:
    pat = (
        r"## 4\. 待执行项（新计划：分优先级与分桶）\s*\n"
        r"\s*### P0 — 发布阻断（必须先闭环）\s*\n"
        r"\s*.*?\s*"
        r"### P1 — 预发布环境（类生产配置）\s*\n"
    )
    m = re.search(pat, text, flags=re.DOTALL)
    if not m:
        return None
    return text[: m.start()] + new_section.rstrip() + "\n\n" + text[m.end() :]


def insert_after_tc_p1_04(text: str, new_string: str) -> str | None:
    pat = r"(\| TC-P1-04 \|[^\n]+)\n\n(### P2 — 上线后 72 小时\s*\n)"
    m = re.search(pat, text)
    if not m:
        return None
    lines = new_string.split("\n")
    tail = "\n".join(lines[1:]).lstrip("\n")
    return text[: m.start()] + m.group(1) + "\n\n" + tail + text[m.end() :]


def replace_section6(text: str, new: str) -> str | None:
    pat = r"## 6\. 执行顺序建议（单周可落地）\s*\n[\s\S]*?(?=\n---\s*\n\n## 7\. 命令速查)"
    m = re.search(pat, text)
    if not m:
        return None
    return text[: m.start()] + new.rstrip() + "\n\n" + text[m.end() :]


def replace_p1_suggestion_through_finish(text: str, new: str) -> str | None:
    """Replace TC-P1-04 row + P1 建议 + 完成定义 block (before ### P2)."""
    pat = r"\| TC-P1-04 \|[^\n]+\n\n\*\*P1 建议执行顺序（后续任务）\*\*[\s\S]*?\*\*完成定义（P1）\*\*：[^\n]+(?=\n\n### P2 — 上线后 72 小时)"
    m = re.search(pat, text)
    if not m:
        return None
    return text[: m.start()] + new.lstrip() + text[m.end() :]


def replace_tc_h05_before_tc_api(text: str, new: str) -> str | None:
    pat = r"\| TC-H-05 \|[^\n]+\n+\n*\*\*API-抽样（TC-API）\*\*："
    m = re.search(pat, text)
    if not m:
        return None
    return text[: m.start()] + new.strip() + text[m.end() :]


def replace_tc_p2_03_before_section5(text: str, new: str) -> str | None:
    """Insert P2 留痕 block: match TC-P2-03 row through ## 5 heading (padding/newlines may differ)."""
    pat = r"\| TC-P2-03 \|[^\n]+\n+\n*---\s*\n\n## 5\. 用例样例（可直接分配给测试执行）"
    m = re.search(pat, text)
    if not m:
        return None
    return text[: m.start()] + new.strip() + text[m.end() :]


def replace_two_markdown_table_rows(text: str, old: str, new: str) -> str | None:
    """Replace two consecutive single-line table rows (e.g. A1 + A2) when padding differs."""
    ol = old.strip().split("\n")
    if len(ol) != 2 or not ol[0].strip().startswith("|") or not ol[1].strip().startswith("|"):
        return None
    m1 = re.match(r"^\|\s*([^|]+?)\s*\|", ol[0].strip())
    m2 = re.match(r"^\|\s*([^|]+?)\s*\|", ol[1].strip())
    if not m1 or not m2:
        return None
    k1, k2 = re.escape(m1.group(1).strip()), re.escape(m2.group(1).strip())
    pat = re.compile(rf"^\|\s*{k1}\s*\|[^\n]+\n\|\s*{k2}\s*\|[^\n]+$", re.MULTILINE)
    if not pat.search(text):
        return None
    return pat.sub(new.strip(), text, count=1)


def replace_table_row_by_first_cell(text: str, old: str, new: str) -> str | None:
    """Match markdown table row by first cell (e.g. A3, A5, TC-P0-01) when column padding differs."""
    o = old.strip()
    if "\n" in o or not o.startswith("|") or not o.endswith("|"):
        return None
    m = re.match(r"^\|\s*([^|]+?)\s*\|", o)
    if not m:
        return None
    first = re.escape(m.group(1).strip())
    pat = re.compile(rf"^\|\s*{first}\s*\|[^\n]+$", re.MULTILINE)
    if not pat.search(text):
        return None
    return pat.sub(new.strip(), text, count=1)


def replace_last_footer_line(text: str, old: str, new: str) -> str | None:
    """**最后更新**：…  often unique at EOF; try last occurrence first."""
    idx = text.rfind(old)
    if idx == -1:
        return None
    return text[:idx] + new + text[idx + len(old) :]


def apply_one(text: str, lineno: int, old: str, new: str) -> tuple[str, bool]:
    if old in text:
        return text.replace(old, new, 1), True

    if "| A6" in old and "前端生产构建" in old and old.count("\n") == 0:
        before = text
        text = replace_a6_line(text, new)
        if text != before:
            return text, True

    if old.startswith("## 4. 待执行项（新计划：分优先级与分桶）") and "### P0 — 发布阻断" in old:
        n = replace_section4_p0_p1(text, new)
        if n is not None:
            return n, True

    if "| TC-P1-04 |" in old and "### P2 — 上线后 72 小时" in old and "P1 建议执行顺序" in new:
        n = insert_after_tc_p1_04(text, new)
        if n is not None:
            return n, True

    if old.startswith("## 6. 执行顺序建议（单周可落地）") and "P0 分桶" in old:
        n = replace_section6(text, new)
        if n is not None:
            return n, True

    if (
        "| TC-P1-04 |" in old
        and "**P1 建议执行顺序（后续任务）**" in old
        and "**完成定义（P1）**" in old
        and len(old) > 300
    ):
        n = replace_p1_suggestion_through_finish(text, new)
        if n is not None:
            return n, True

    if old.strip().startswith("**最后更新**：") and new.strip().startswith("**最后更新**："):
        n = replace_last_footer_line(text, old, new)
        if n is not None:
            return n, True

    n = replace_two_markdown_table_rows(text, old, new)
    if n is not None:
        return n, True

    n = replace_table_row_by_first_cell(text, old, new)
    if n is not None:
        return n, True

    if (
        "| TC-P2-03 |" in old
        and "## 5. 用例样例（可直接分配给测试执行）" in old
        and "P2 执行留痕" in new
    ):
        n = replace_tc_p2_03_before_section5(text, new)
        if n is not None:
            return n, True

    if "| TC-H-05 |" in old and "**API-抽样（TC-API）**" in old:
        n = replace_tc_h05_before_tc_api(text, new)
        if n is not None:
            return n, True

    # Try stripping trailing "  " before newlines in old (markdown line breaks)
    old_norm = re.sub(r"  +\n", "\n", old)
    if old_norm != old and old_norm in text:
        return text.replace(old_norm, new, 1), True

    # Transcript sometimes has \n\n\n before ---; file may have \n\n
    old_nn = re.sub(r"\n{3,}", "\n\n", old)
    if old_nn != old and old_nn in text:
        return text.replace(old_nn, new, 1), True

    return text, False


def main() -> None:
    transcript = Path(sys.argv[1]) if len(sys.argv) > 1 else TRANSCRIPT_DEFAULT
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT_DEFAULT
    if not transcript.is_file():
        sys.exit(f"Transcript not found: {transcript}")

    text = get_initial_write(transcript)
    ops = list(iter_str_replaces(transcript))
    for i, (lineno, old, new) in enumerate(ops):
        text, ok = apply_one(text, lineno, old, new)
        if not ok:
            print(f"FAILED op {i + 1}/{len(ops)} jsonl_line={lineno}", file=sys.stderr)
            print(f"old (head): {old[:260]!r}", file=sys.stderr)
            sys.exit(1)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"OK {len(ops)} StrReplace ops replayed -> {out} ({text.count(chr(10)) + 1} lines)")


if __name__ == "__main__":
    main()
