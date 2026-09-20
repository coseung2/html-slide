# html-slide

**규율을 좋은 의도가 아니라 린터로 강제하는** HTML 발표자료 제작 스킬.

해결하려는 문제는 이렇습니다. "두 번째 열을 강조해줘"라는 요청을 받은 에이전트는
`left: 412px; top: 268px`를 씁니다. 스크린샷에서는 맞아 보이고, 레이아웃이나 창
크기가 바뀌는 순간 깨집니다. 슬라이드는 장식으로 흘러가기도 합니다 — 모든 요소가
움직이고, 아무것도 설명하지 않는 모션, 시각자료 아래 설명 캡션, 구석에 박힌 제목.
전부 습관이고, 습관에는 **돌아가는 검사**가 필요합니다.

그래서 이 리포지토리는 두 가지를 동시에 담고 있습니다. **규범 문서**(`SKILL.md`)와,
그 규칙을 어긴 덱을 **실패시키는 강제 계층**(`tools/slide_lint.py`,
`tests/motion_check.py`)입니다. 브라우저에서 실제로 렌더링해 박스를 재야만 확인
가능한 규칙까지 포함합니다.

## 구성

```
SKILL.md                    규칙 — §1 타이포, §3 간격, §8 모션, §9 바인딩, §10 상태기계, §17 함정
tools/slide_lint.py         린터: 정적 검사 + 브라우저 계측 기하 검사
tools/verify.sh             3개 게이트 순차 실행; exit 0 = 납품 가능
tools/lint_all.sh           배포된 모든 덱을 한 번에 pass/fail
tests/motion_check.py       거동 테스트: reduced-motion 완전성, 페이즈 워크, 리사이즈 바인딩
tests/linter_selftest.py    각 규칙이 지금도 발화하는지 증명 (픽스처 vs 깨끗한 기준 덱)
tests/fixtures/broken-deck.html    검사 가능한 규칙을 전부 일부러 위반한 덱
examples/reference-3slides.html    통과하는 3장 덱, 기준선으로 사용
motion/                     모션 레시피 15종 — 무엇을 설명하는가로 분류
motion/README.md            계약, 패턴 인덱스, 출처 트레일
references/SOURCES.md       모든 타이밍 값과 방법의 출처
references/runtime-contract.md     `.deck-live` / `data-start` 계약 전문
references/geometry-qa.md   앵커링 증명, 정적 검사, 측정 함정
references/motion-timing.md       타이밍 값별 출처
references/ecosystem-survey.md    인접 스킬 리포 조사 (요약이 아니라 직접 읽은 기록)
assets/fonts/               Pretendard Variable (OFL) — 자체 호스팅, CDN 호출 없음
```

## 이름 붙일 가치가 있는 두 실패

**대상을 벗어나는 강조.** 규칙은 강조가 대상의 자식이거나, `data-target`으로
묶인 형제거나, 대상에서 파생된 복제여야 한다는 것입니다 — 슬라이드 좌표에 그린
박스는 안 됩니다. 린터가 바인딩을 증명합니다. 1920×1080, 1280×720, 1024×768에서
렌더링하고, 강조와 대상의 겹침을 재고, 커버리지가 떨어지거나 정렬이 스테이지 단위
1개를 넘게 어긋나면 실패시킵니다. 기준 덱과 ring/pulse 패턴은 모든 크기에서
100% 커버리지, 0.00 드리프트를 기록합니다.

**의미를 나르는 모션.** `transform`, `opacity`, `filter`, `clip-path`만
애니메이션합니다. `top`, `width`, `height`, `margin`은 레이아웃과 페인트를
유발하고, 그것이 대상이 자기 강조 밑에서 빠져나가는 방식입니다. 여기 타이핑
효과가 `width`를 애니메이션하지 않는 이유도 같습니다 — 박스를 미리 확보하고
글자만 페이드인하므로, 한글 음절이 내부 획에서 잘리는 일이 없습니다. 길이·이징은
여기서 발명하지 않았습니다. 공개된 출처(`references/SOURCES.md`)에서 가져왔고
레시피는 그 값을 그대로 구현합니다.

## 실행

```bash
# 덱 하나, 기하 + 규칙 (~10초)
~/.venvs/pw/bin/python tools/slide_lint.py examples/reference-3slides.html

# 스크린샷까지 저장
~/.venvs/pw/bin/python tools/slide_lint.py deck.html --shots /tmp/shots

# 전체 게이트: 모든 덱 + 린터 셀프테스트 + 모션 거동
bash tools/verify.sh
```

현재 상태: `reference-3slides.html`과 **패턴 15종 전부**가 오류 0·경고 0으로
린터를 통과합니다. `linter_selftest.py`는 픽스처가 17개 규칙 코드(오류 9건)를
여전히 발화하고 기준 덱은 깨끗함을 확인합니다. `motion_check.py`는 거동 검사
**134개, 실패 0**.

Playwright가 필요합니다 (`pip install playwright && playwright install chromium`).

## 모션 라이브러리

`motion/patterns/index.html`이 갤러리입니다. 레시피 15종을 **어떻게 보이는가가
아니라 무엇을 설명하는가**로 묶었습니다.

| 그룹 | 설명하는 것 | 레시피 |
|---|---|---|
| EMPHASIS | 이 객체가 주어다 | `pat-ring`, `pat-pulse`, `pat-recede` |
| REVEAL | 자료가 어떻게 도착하는가 | `pat-group`, `pat-line-step` |
| TRANSFORM | 전이 후가 되었다 | `pat-state`, FLIP 이동 |
| QUANTITY | 이만큼 변했다 | `pat-roll`, `pat-bar` |
| SEQUENCE | 이 순서로 진행된다 | `pat-steps` (가역) |
| CONNECTIVE | 이 둘은 관계가 있다 | `pat-path` |
| SWAP | 이것이 저것을 대체했다 | `pat-swap` |
| TYPE | 이 텍스트가 쓰이고 있다 | `pat-type` (음절 단위) |
| TRANSITION | 이 장면이 저 장면에 자리를 내줬다 | `pat-wipe`, `pat-focus-pull` |

각 패턴은 실행 가능한 페이지이고, 자기 레시피에 *언제 쓸 것인가 / 쓰지 말 것인가*
주석이 붙어 있으며, 다른 슬라이드와 똑같이 린트됩니다.
`motion/patterns/index.html`에서 시작하고, 새로 추가하기 전에 `motion/README.md`를
읽으십시오.

## 레이아웃

스테이지는 `transform: scale()`로 맞춘 고정 16:9 박스입니다. 따라서 슬라이드
좌표가 안정적이고, 리사이즈 시 레이아웃이 애니메이션되지 않습니다. 스텝 페이즈는
`.deck-live`에 스코프되고, 런타임이 모션을 원할 때만 이 클래스를 붙입니다 —
그래서 캡처한 프레임, PDF 내보내기, `prefers-reduced-motion`이 모두 같은 완성
슬라이드를 보여줍니다.

## 한국어 문서

- 이 파일이 한국어 README입니다. 영문 원본은 `README.md`.
- 모션 라이브러리 상세는 `motion/README.md`, 규칙 전문은 `SKILL.md`.

## 라이선스와 출처

규범 문서, 린터, 테스트, 예제, 모션 라이브러리는 이 리포지토리의 자체 작업물입니다.
모션 타이밍 값은 MIT 라이선스 참조 자료와 공개 문서에서 가져왔으며,
`references/SOURCES.md`에 출처 경로가, `references/`에 귀속 표기가 함께 있는
발췌문이 있습니다. Pretendard Variable은 SIL Open Font License
(`assets/fonts/`)를 따릅니다.
