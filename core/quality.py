"""Deck-level composition quality diagnostics for visual-first authoring."""
from __future__ import annotations

from collections import Counter
from typing import Any

from .registry import ContractError

DEFAULT_THRESHOLDS = {
    'min_concrete_visual_ratio': 0.40,
    'max_layout_share': 0.50,
    'max_consecutive_layout': 2,
    'max_generic_only_run': 2,
    'max_motion_share': 0.75,
    'min_anchor_coverage': 0.50,
}

# Transitional defaults for the current reviewed module catalog. New modules may
# declare ``visualRole`` in their manifest and override these fallbacks.
ROLE_FALLBACK = {
    'image': 'evidence',
    'bar-chart': 'evidence',
    'line-chart': 'evidence',
    'metric': 'evidence',
    'ranking': 'evidence',
    'score': 'evidence',
    'logo': 'support',
    'process': 'structure',
    'timeline': 'structure',
    'comparison-text': 'structure',
    'statement': 'copy',
    'quote': 'copy',
    'bullet-list': 'copy',
}

EVIDENCE_REQUIRED_INTENTS = {
    'comparison', 'before-after', 'ranking', 'distribution', 'kpi', 'scene', 'evidence'
}


def _longest_true_run(values: list[bool]) -> int:
    best = current = 0
    for value in values:
        current = current + 1 if value else 0
        best = max(best, current)
    return best


def _longest_same_run(values: list[str]) -> int:
    if not values:
        return 0
    best = current = 1
    previous = values[0]
    for value in values[1:]:
        if value == previous:
            current += 1
        else:
            previous = value
            current = 1
        best = max(best, current)
    return best


def _module_role(block: dict[str, Any], registry) -> str:
    module = registry.block(block['module'])
    declared = module.get('visualRole')
    if declared in {'evidence', 'structure', 'support', 'copy'}:
        return declared
    return ROLE_FALLBACK.get(block['module'], 'structure' if module.get('type') == 'visuals' else 'copy')


def _issue(code: str, message: str, *, slides: list[str] | None = None) -> dict[str, Any]:
    result = {'code': code, 'severity': 'error', 'message': message}
    if slides:
        result['slides'] = slides
    return result


def evaluate_deck_quality(spec: dict, slides: list[dict], registry) -> dict:
    """Return deterministic deck-level quality diagnostics.

    Legacy specs default to advisory mode. New authoring should opt into strict mode;
    the composer then turns these diagnostics into a hard contract gate.
    """
    options = spec.get('quality', {})
    profile = options.get('profile', 'advisory')
    thresholds = {key: options.get(key, value) for key, value in DEFAULT_THRESHOLDS.items()}
    source_by_id = {slide['id']: slide for slide in spec.get('slides', [])}
    n = len(slides)

    layouts = [slide['layout'] for slide in slides]
    layout_counts = Counter(layouts)
    top_layout, top_layout_count = layout_counts.most_common(1)[0] if layouts else ('', 0)
    max_layout_share = top_layout_count / n if n else 0.0
    max_consecutive_layout = _longest_same_run(layouts)

    concrete_flags: list[bool] = []
    generic_only_ids: list[str] = []
    missing_evidence_ids: list[str] = []
    explicit_without_reason: list[str] = []
    anchor_hits = 0
    narrative = spec.get('narrative', {})
    anchor = narrative.get('anchor')
    continuity = narrative.get('continuity', 'independent')

    for slide in slides:
        roles = [_module_role(block, registry) for block in slide.get('blocks', [])]
        concrete = 'evidence' in roles
        concrete_flags.append(concrete)
        if not concrete:
            generic_only_ids.append(slide['id'])
            if slide.get('intent') in EVIDENCE_REQUIRED_INTENTS:
                missing_evidence_ids.append(slide['id'])
        source = source_by_id.get(slide['id'], {})
        if source.get('layout', 'auto') != 'auto' and not source.get('layout_reason', '').strip():
            explicit_without_reason.append(slide['id'])
        if anchor and source.get('anchor_ref') == anchor:
            anchor_hits += 1

    concrete_ratio = sum(concrete_flags) / n if n else 0.0
    max_generic_only_run = _longest_true_run([not flag for flag in concrete_flags])

    motions = [effect['module'] for slide in slides for effect in slide.get('motion', [])]
    motion_counts = Counter(motions)
    top_motion, top_motion_count = motion_counts.most_common(1)[0] if motions else ('', 0)
    max_motion_share = top_motion_count / len(motions) if motions else 0.0

    anchor_coverage = anchor_hits / n if n else 0.0
    issues: list[dict[str, Any]] = []

    if explicit_without_reason:
        issues.append(_issue(
            'explicit-layout-without-reason',
            'Explicit layouts need layout_reason so the planner cannot be bypassed without an accountable composition decision.',
            slides=explicit_without_reason,
        ))
    if missing_evidence_ids:
        issues.append(_issue(
            'evidence-required-intent-without-concrete-visual',
            'Slides whose intent depends on evidence/comparison/data need a concrete visual or data-bearing module, not only prose/structure modules.',
            slides=missing_evidence_ids,
        ))
    if n >= 5 and concrete_ratio < thresholds['min_concrete_visual_ratio']:
        issues.append(_issue(
            'low-concrete-visual-coverage',
            f'Concrete visual coverage is {concrete_ratio:.0%}; target is at least {thresholds["min_concrete_visual_ratio"]:.0%}.',
            slides=generic_only_ids,
        ))
    if n >= 4 and max_generic_only_run > thresholds['max_generic_only_run']:
        issues.append(_issue(
            'generic-structure-run',
            f'{max_generic_only_run} consecutive slides rely only on copy/structural modules; maximum is {thresholds["max_generic_only_run"]}.',
        ))
    if n >= 6 and max_layout_share > thresholds['max_layout_share']:
        issues.append(_issue(
            'layout-share-too-high',
            f'Layout {top_layout!r} occupies {max_layout_share:.0%} of the deck; maximum is {thresholds["max_layout_share"]:.0%}.',
        ))
    if max_consecutive_layout > thresholds['max_consecutive_layout']:
        issues.append(_issue(
            'layout-run-too-long',
            f'The same layout repeats {max_consecutive_layout} times consecutively; maximum is {thresholds["max_consecutive_layout"]}.',
        ))
    if len(motions) >= 4 and max_motion_share > thresholds['max_motion_share']:
        issues.append(_issue(
            'motion-grammar-too-repetitive',
            f'Motion grammar {top_motion!r} accounts for {max_motion_share:.0%} of declared motion; maximum is {thresholds["max_motion_share"]:.0%}.',
        ))
    if continuity in {'recurring', 'progressive'}:
        if not anchor:
            issues.append(_issue(
                'narrative-anchor-missing',
                'Recurring/progressive narrative continuity requires narrative.anchor.',
            ))
        elif n >= 2 and anchor_coverage < thresholds['min_anchor_coverage']:
            issues.append(_issue(
                'narrative-anchor-coverage-low',
                f'Anchor {anchor!r} appears on {anchor_coverage:.0%} of slides; target is at least {thresholds["min_anchor_coverage"]:.0%}.',
            ))

    report = {
        'profile': profile,
        'enforced': profile == 'strict',
        'passed': not issues,
        'thresholds': thresholds,
        'metrics': {
            'slideCount': n,
            'concreteVisualRatio': round(concrete_ratio, 4),
            'genericOnlySlides': generic_only_ids,
            'maxGenericOnlyRun': max_generic_only_run,
            'layoutCounts': dict(sorted(layout_counts.items())),
            'maxLayoutShare': round(max_layout_share, 4),
            'maxConsecutiveLayout': max_consecutive_layout,
            'motionCounts': dict(sorted(motion_counts.items())),
            'maxMotionShare': round(max_motion_share, 4),
            'anchor': anchor,
            'anchorCoverage': round(anchor_coverage, 4),
        },
        'issues': issues,
    }
    return report


def enforce_deck_quality(report: dict) -> None:
    if report.get('profile') != 'strict' or report.get('passed', True):
        return
    summary = '; '.join(issue['code'] + ': ' + issue['message'] for issue in report.get('issues', []))
    raise ContractError('quality gate failed: ' + summary)
