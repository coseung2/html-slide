#!/usr/bin/env python3
"""Lightweight visible-copy lint for Korean HTML slide decks.

This intentionally catches only deterministic problems: template English,
English-heavy visible strings, banned punctuation, and release-status caveats
that leak into Korean body copy. Naturalness/translationese remains editorial.
"""
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path

SKIP_TAGS = {"script", "style", "template", "noscript", "svg"}
KOREAN_FALLBACK_HANGUL = 12
TEMPLATE_ENGLISH = (
    "KEY TAKEAWAYS",
    "NEXT STEPS",
    "PROJECT OVERVIEW",
    "STATUS OVERVIEW",
    "EXECUTIVE SUMMARY",
    "ACTION ITEMS",
    "KEY INSIGHTS",
)
PROHIBITED_KOREAN_PUNCTUATION = {
    "·": "middle dot",
    "–": "en dash",
    "—": "em dash",
}


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.stack: list[tuple[str, bool, bool, bool, bool]] = []
        self.skip_depth = 0
        self.allow_depth = 0
        self.body_depth = 0
        self.caveat_allow_depth = 0
        self.parts: list[dict] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang", "")
        skip = tag in SKIP_TAGS
        allow = "data-copy-en-ok" in attrs
        body = "body" in set(attrs.get("class", "").split())
        caveat_allow = "data-copy-caveat-ok" in attrs
        self.stack.append((tag, skip, allow, body, caveat_allow))
        self.skip_depth += int(skip)
        self.allow_depth += int(allow)
        self.body_depth += int(body)
        self.caveat_allow_depth += int(caveat_allow)

    def handle_startendtag(self, tag, attrs):
        if tag == "html":
            self.lang = dict(attrs).get("lang", self.lang)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            open_tag, skip, allow, body, caveat_allow = self.stack[i]
            if open_tag == tag:
                removed = self.stack[i:]
                del self.stack[i:]
                self.skip_depth -= sum(int(item[1]) for item in removed)
                self.allow_depth -= sum(int(item[2]) for item in removed)
                self.body_depth -= sum(int(item[3]) for item in removed)
                self.caveat_allow_depth -= sum(int(item[4]) for item in removed)
                break

    def handle_data(self, data):
        if self.skip_depth:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self.parts.append({
                "line": self.getpos()[0],
                "text": text,
                "allowed": self.allow_depth > 0,
                "body": self.body_depth > 0,
                "caveatAllowed": self.caveat_allow_depth > 0,
            })


def _is_urlish(text: str) -> bool:
    lower = text.lower()
    return lower.startswith(("http://", "https://", "www.")) or ".com/" in lower


def lint_text(source: str) -> dict:
    parser = VisibleText()
    parser.feed(source)
    visible = " ".join(p["text"] for p in parser.parts)
    hangul_total = len(re.findall(r"[가-힣]", visible))
    korean_mode = parser.lang.lower().startswith("ko") or hangul_total >= KOREAN_FALLBACK_HANGUL
    findings: list[dict] = []

    if not parser.lang.lower().startswith("ko") and hangul_total >= KOREAN_FALLBACK_HANGUL:
        findings.append({
            "severity": "warning",
            "code": "copy-lang",
            "line": 1,
            "text": 'Korean copy detected but <html lang="ko"> is missing.',
        })

    if korean_mode:
        for char, name in PROHIBITED_KOREAN_PUNCTUATION.items():
            for match in re.finditer(re.escape(char), source):
                findings.append({
                    "severity": "error",
                    "code": "copy-prohibited-punctuation",
                    "line": source.count("\n", 0, match.start()) + 1,
                    "text": char,
                    "detail": f"{name} is prohibited in Korean slide source; rewrite with Korean punctuation or ~ for numeric ranges",
                })

        for part in parser.parts:
            text = part["text"]
            if part["body"] and not part["caveatAllowed"] and re.search(r"잠정치|예비치|추후\s*수정|향후\s*수정|수정될\s*수", text):
                findings.append({
                    "severity": "error",
                    "code": "copy-body-release-caveat",
                    "line": part["line"],
                    "text": text,
                    "detail": "release-status caveat belongs in a compact footnote/source, not main body copy; use data-copy-caveat-ok only when revisions are the slide's subject",
                })
            if part["allowed"] or _is_urlish(text):
                continue
            upper = re.sub(r"\s+", " ", text.upper())
            template = next((token for token in TEMPLATE_ENGLISH if re.search(r"(?<![A-Z])" + re.escape(token) + r"(?![A-Z])", upper)), None)
            if template:
                findings.append({
                    "severity": "error",
                    "code": "copy-template-english",
                    "line": part["line"],
                    "text": text,
                    "detail": f"template English remains: {template}",
                })
                continue

            latin = len(re.findall(r"[A-Za-z]", text))
            hangul = len(re.findall(r"[가-힣]", text))
            english_words = re.findall(r"\b[A-Za-z][A-Za-z'-]{2,}\b", text)
            alphabetic = latin + hangul
            if latin >= 12 and len(english_words) >= 2 and alphabetic and latin / alphabetic >= 0.60:
                findings.append({
                    "severity": "error",
                    "code": "copy-english-heavy",
                    "line": part["line"],
                    "text": text,
                    "detail": "visible Korean-deck copy is English-heavy; rewrite or mark a reviewed exception",
                })

    return {
        "lang": parser.lang,
        "koreanMode": korean_mode,
        "visibleParts": len(parser.parts),
        "errors": sum(f["severity"] == "error" for f in findings),
        "warnings": sum(f["severity"] == "warning" for f in findings),
        "findings": findings,
    }


def lint_file(path: Path) -> dict:
    return lint_text(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html", type=Path)
    ap.add_argument("--strict", action="store_true", help="fail on warnings as well as errors")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    report = lint_file(args.html)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for finding in report["findings"]:
            detail = finding.get("detail", finding["text"])
            print(f"{finding['severity'].upper()} {finding['code']} line {finding['line']}: {detail}")
        state = "PASS" if report["errors"] == 0 and (not args.strict or report["warnings"] == 0) else "FAIL"
        print(f"{state}: errors={report['errors']} warnings={report['warnings']} koreanMode={report['koreanMode']}")
    return 1 if report["errors"] or (args.strict and report["warnings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
