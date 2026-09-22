# Semantic motion grammar

Use this reference when a slide needs data motion, a focus beat, or more than one animation phase.

## Start with the sentence, not the effect

Before writing keyframes, state the slide's visual takeaway in one sentence and identify **one primary motion target**. If that target is unclear, the motion hierarchy is unclear.

An optional secondary target is allowed when it directly completes the same claim. Do not give every visible object equal animation weight.

## Map relationship to motion

| Relationship | Preferred motion grammar | Typical target |
|---|---|---|
| value changed | value swap / roll | old → new number |
| gap / spread | bracket, ruler, distance trace | two endpoints |
| trajectory | marker travel / path follow | start → end |
| quantity | bar growth / accumulation | magnitude |
| distribution / concentration | sequential accumulation | cluster |
| comparison | controlled swap / contrast | A → B |
| discrete sequence | step resolve | state 1 → 2 → 3 |
| time order | timeline sweep | chronological nodes |
| mechanism | transform / reveal cause and result | actual UI/data object |

Do not diversify motion cosmetically. Repeating the same fade, recede, pulse, ring, or underline on unrelated slides is still one motion idea wearing different colours.

## Phase discipline

- A phase begins only after presenter input.
- One input advances exactly one declared `data-step`.
- A phase may contain a short stagger or directed micro-sequence after that input.
- Time must never advance to the next phase.
- Entering a slide must not start a meaningful beat merely because the slide became `.is-active`.
- Back returns to the previous stable phase; forward from there must reproduce the same end state.

## Static contract

Motion explains; state remains. With JavaScript absent, static mode on, or reduced motion requested, render the accepted completed frame immediately. Old/superseded values may be hidden only when the final replacement is visible.

## Review questions

1. What single thing should the audience notice first?
2. What relationship is being explained?
3. Does the motion depict that relationship, or merely decorate it?
4. Would the slide still make sense in its final static frame?
5. Does one click produce exactly one stable new state?
