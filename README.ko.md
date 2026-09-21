# html-slide

[English README](README.md) · **한국어**

HTML로 프레젠테이션을 만들되, **감각에만 의존하지 않고 실제 브라우저 계측과 자동 검증으로 품질을 지키는 슬라이드 제작 스킬**입니다.

이 리포지토리는 단순한 HTML 템플릿 모음이 아닙니다.

- `SKILL.md`: 어떤 슬라이드를 만들어야 하는지 정의하는 제작 규칙
- `tools/slide_lint.py`: 배치·강조·타이포·간격을 검사하는 린터
- `tests/motion_check.py`: 모션이 실제 발표 상황에서 정상 동작하는지 확인하는 브라우저 테스트
- `tools/copy_lint.py`: 한국어 덱의 불필요한 영어와 템플릿 문구를 검사하는 카피 린터
- `tools/sports_qa.py`: 스포츠 리포트의 사진·정보·컨트롤 충돌을 점검하는 보조 QA
- `tools/export_deck.py`: 검증된 HTML을 PNG·PDF·PPTX로 한 번에 내보내는 최종 출력 파이프라인

핵심 목표는 하나입니다.

> **스크린샷 한 장에서는 그럴듯하지만, 실제 발표·리사이즈·내보내기에서 깨지는 슬라이드를 만들지 않는다.**

---

## 왜 필요한가

HTML 슬라이드에서 반복해서 발생하는 문제는 비슷합니다.

- 강조 박스를 `left: 412px; top: 268px`처럼 슬라이드 좌표에 직접 그려 놓는다.
- 창 크기가 바뀌면 강조가 실제 대상에서 벗어난다.
- 제목·본문·예시가 서로 멀어져 읽는 순서가 흐려진다.
- 모든 요소를 움직여 모션이 의미보다 장식이 된다.
- 애니메이션이 끝나야만 핵심 정보가 보인다.
- 사진 위에 본문을 얹어 가독성이 무너진다.
- 한국어 덱인데 `TITLE RACE`, `NEXT UP`, `POINTS` 같은 영어 템플릿 라벨이 그대로 남는다.
- PDF와 PPTX를 따로 만들면서 HTML과 결과물이 서로 달라진다.

`html-slide`는 이런 문제를 **규칙 + 자동 검사 + 실제 브라우저 검증**으로 막습니다.

---

## 핵심 원칙

### 1. 강조는 반드시 실제 대상에 묶는다

강조 효과는 대상의 자식 요소이거나, `data-target`으로 실제 대상에 연결된 요소이거나, 대상에서 계산해 만든 복제여야 합니다.

슬라이드 좌표에 임의로 그린 강조 박스는 허용하지 않습니다.

린터는 여러 해상도에서 대상과 강조의 위치를 실제로 측정해, 강조가 대상에서 벗어나면 실패시킵니다.

### 2. 모션은 의미를 설명할 때만 쓴다

기본 애니메이션 속성은 `transform`과 `opacity`입니다.

`top`, `left`, `width`, `height`, `margin`, `padding`처럼 레이아웃 자체를 흔드는 속성을 애니메이션하지 않습니다.

모션은 다음과 같은 관계를 설명할 때 사용합니다.

- 무엇이 핵심인가
- 무엇이 얼마나 변했는가
- 전과 후가 어떻게 달라졌는가
- 어떤 순서로 진행되는가
- 두 요소가 어떤 관계인가

장식만을 위한 반복 모션은 넣지 않습니다.

### 3. 모션이 없어도 완성된 슬라이드여야 한다

정적 상태가 곧 최종 상태입니다.

JavaScript가 꺼져 있거나, `prefers-reduced-motion`이 켜져 있거나, PDF/PPTX로 출력하더라도 **정보가 빠진 슬라이드가 나오면 안 됩니다.**

라이브 발표에서만 `.deck-live`가 모션 상태를 활성화합니다.

### 4. 고정 1920×1080 스테이지를 통째로 축소한다

슬라이드 내부를 뷰포트에 맞춰 재배치하지 않습니다.

1920×1080 좌표계를 유지하고 `transform: scale()`로 화면에 맞춥니다. 따라서 발표 창 크기가 달라져도 내부 좌표와 강조 바인딩이 흔들리지 않습니다.

의미 있는 콘텐츠는 기본적으로 스테이지 가장자리에서 **5% 안쪽의 안전 영역**에 둡니다.

### 5. 한국어 덱은 처음부터 한국어로 쓴다

영문 템플릿을 만든 뒤 단어만 번역하지 않습니다.

제목·소제목·지표명·설명은 처음부터 한국어 독자를 기준으로 작성합니다.

다만 다음은 영어를 유지할 수 있습니다.

- `EPL`, `VAR`, `xG`, `AI`, `HTML` 같은 익숙한 약어
- `MCI`, `ARS`, `LIV` 같은 팀 코드
- 공식 브랜드명·제품명
- 원문 인용
- 출처·메타데이터

자세한 기준은 [한국어 카피 가이드](references/korean-copy.md)를 참고하십시오.

---

## 빠른 시작

### 1. 필요한 환경

브라우저 계측에는 Playwright와 Chromium이 필요합니다.

```bash
pip install playwright
playwright install chromium
```

PPTX 출력까지 사용할 경우 `python-pptx`도 필요합니다.

```bash
pip install python-pptx
```

시스템에 Chrome 또는 Chromium이 설치되어 있으면 내보내기 도구가 자동으로 감지합니다.

### 2. 기준 덱 검사

```bash
python tools/slide_lint.py examples/reference-3slides.html
```

스크린샷도 함께 남기려면:

```bash
python tools/slide_lint.py examples/reference-3slides.html --shots out/shots
```

### 3. 저장소 전체 검증

```bash
bash tools/verify.sh
```

특정 가상환경의 Python을 사용하려면:

```bash
PYTHON=/path/to/venv/bin/python bash tools/verify.sh
```

출력 마지막이 다음과 같아야 합니다.

```text
ALL GREEN
```

---

## 품질 게이트 5단계

`tools/verify.sh`는 다음 검사를 순서대로 실행합니다.

### 1/5 · 모든 배포 덱 린트

`tools/lint_all.sh`

저장소에 포함된 덱이 기본 린터 규칙을 통과하는지 확인합니다.

검사 대상에는 다음이 포함됩니다.

- 스테이지 밖으로 나간 요소
- 잘린 텍스트
- 강조 대상 바인딩
- 최소 글자 크기
- 과도한 타이포 단계
- 잘못된 한글 줄바꿈
- 하단 설명 캡션
- 과도한 내부 간격
- 레이아웃을 흔드는 애니메이션 속성

### 2/5 · 린터 자체 테스트

`tests/linter_selftest.py`

린터가 조용히 고장 나는 상황을 막습니다.

고의로 잘못 만든 `tests/fixtures/broken-deck.html`에서는 규칙 위반을 실제로 잡아내야 하고, 기준 덱은 깨끗하게 통과해야 합니다.

### 3/5 · 모션 동작 검사

`tests/motion_check.py`

실제 Chromium에서 다음을 확인합니다.

- 정적 상태에서 모든 정보가 보이는가
- 발표 모드에서 단계가 순서대로 진행되는가
- 이전 단계로 정상 복귀하는가
- 마지막 단계가 완성 프레임과 일치하는가
- 강조가 여러 뷰포트에서 실제 대상에 붙어 있는가
- 강조가 재생되는 동안 대상 자체가 움직이지 않는가
- 전환 모션이 시작과 끝에서 정상 정렬되는가
- 한글 타이핑 효과가 음절 단위로 깨지지 않는가

현재 모션 회귀 검사는 **134개**입니다.

### 4/5 · 스포츠·발표자 컨트롤 검사

`tests/sports_check.py`

스포츠용 레이아웃과 공통 발표자 셸을 함께 검사합니다.

- 발표자 컨트롤 중복 생성
- 키보드 탐색
- 정적 모드
- 개요 화면
- 모달이 열렸을 때 전역 단축키 차단
- 초기 해시 딥링크
- 리사이즈 시 레이아웃 안정성
- 5개 뷰포트의 기하 검사
- 외부 네트워크 의존성
- 런타임 오류

현재 회귀 검사는 **35개**입니다.

### 5/5 · 한국어 카피 린터 자체 테스트

`tests/copy_lint_selftest.py`

한국어 덱에서 템플릿성 영어가 다시 섞이지 않도록 카피 린터가 정상 동작하는지 확인합니다.

현재 자체 테스트는 **8개**입니다.

---

## 한국어 카피 품질

한국어 슬라이드에서는 아래와 같은 표현을 기본값으로 쓰지 않습니다.

```text
TOP SIX MARKET REPORT
TITLE RACE
THE PACK
NEXT UP
TOP 3 POINTS
GOAL DIFF.
```

같은 정보를 한국어 독자가 더 빠르게 읽을 수 있다면 한국어가 우선입니다.

예:

| 피할 표현 | 권장 표현 |
|---|---|
| TITLE RACE | 맨시티, 3점 차 단독 선두 |
| THE PACK | 승점 9 동률권 |
| NEXT UP | 다음 경기 |
| POINTS | 승점 |
| GOALS | 득점 |
| GOAL DIFF. | 득실차 |
| FORM | 최근 흐름 |
| SIGNAL | 핵심 정리 |

한국어 덱 카피 검사:

```bash
python tools/copy_lint.py deck.html --strict
```

의도적으로 유지한 영문 표기는 해당 요소에 `data-copy-en-ok`를 붙일 수 있습니다.

```html
<span data-copy-en-ok>EPL</span>
```

이 속성은 **검토된 예외 한 곳만 면제**하는 용도입니다. 슬라이드 전체를 영어 검사에서 빼는 용도로 사용하지 않습니다.

> 카피 린터는 불필요한 영어와 명백한 템플릿 문구를 잡습니다.
> 번역체의 미묘한 어색함까지 기계적으로 판정하지는 않습니다. 마지막 편집은 [한국어 카피 가이드](references/korean-copy.md)의 전/후 예시를 기준으로 직접 검토합니다.

---

## 스포츠 리포트

순위표, 경기 결과, 득점 순위, 다음 라운드 예고처럼 스포츠 방송형 자료를 만들 때는 [스포츠 덱 가이드](references/sports-decks.md)를 함께 적용합니다.

### 스포츠용 추가 원칙

- 사진과 정보 영역을 분리합니다.
- 사진 위에 긴 본문을 얹지 않습니다.
- 엠블럼은 알파 영역 안의 불필요한 조각까지 확인합니다.
- 경기 사진과 구단 로고/벽지 그래픽을 혼동하지 않습니다.
- 서로 비교하는 막대는 같은 기준축을 사용합니다.
- 기록 강조는 대상 요소에 직접 묶습니다.
- 모든 카드가 움직이게 하지 않습니다.
- 강조가 필요한 장면에만 한 번의 의미 있는 모션을 사용합니다.
- 하단 발표자 컨트롤이 슬라이드 내용을 가리지 않아야 합니다.

스포츠 전용 QA:

```bash
python tools/sports_qa.py selfcontained-deck.html --out out/sports-qa
python tests/sports_check.py
```

`sports_qa.py`는 다음 5개 화면 크기를 검사합니다.

- 1920×1080
- 1280×720
- 1024×768
- 390×844
- 844×390

검사 항목:

- 이미지와 텍스트 충돌
- 잘린 콘텐츠
- 깨진 이미지
- 발표자 컨트롤에 가려진 콘텐츠
- 화면 크기에 따른 배치 드리프트

단, 다음은 자동으로 판정하지 않습니다.

- 경기 결과의 사실 여부
- 사진이 실제 해당 경기인지
- 이미지 저작권
- 사진 속 선수 신원
- 피사체 크롭의 미적 완성도

이 항목은 출처 확인과 렌더링 스크린샷 검토가 별도로 필요합니다.

---

## 발표자 런타임

공통 발표자 셸은 HTML 덱의 상태를 관리합니다.

기본 구조는 다음과 같습니다.

- 이전 / 다음
- 현재 슬라이드 번호
- 현재 모션 단계
- 정적 모드
- 전체 개요
- 전체 화면
- 진행률 표시

키보드 탐색과 모달 격리도 회귀 테스트에 포함됩니다.

모션 상태는 `.deck-live`일 때만 활성화되고, 정적 출력에서는 최종 완성 프레임을 사용합니다.

자세한 계약은 [runtime-contract.md](references/runtime-contract.md)를 참고하십시오.

---

## 모션 라이브러리

`motion/patterns/index.html`에서 전체 패턴을 확인할 수 있습니다.

패턴은 **어떻게 보이는가**가 아니라 **무엇을 설명하는가**를 기준으로 분류합니다.

| 그룹 | 설명하는 관계 | 패턴 |
|---|---|---|
| EMPHASIS | 이 객체가 핵심이다 | `pat-ring`, `pat-pulse`, `pat-recede` |
| REVEAL | 자료가 어떻게 등장하는가 | `pat-group`, `pat-line-step` |
| TRANSFORM | 이전 상태가 이후 상태로 바뀌었다 | `pat-state`, FLIP |
| QUANTITY | 값이 이만큼 변했다 | `pat-roll`, `pat-bar` |
| SEQUENCE | 이 순서로 진행된다 | `pat-steps` |
| CONNECTIVE | 두 요소가 연결되어 있다 | `pat-path` |
| SWAP | 이것이 저것으로 교체됐다 | `pat-swap` |
| TYPE | 문장이 쓰이고 있다 | `pat-type` |
| TRANSITION | 한 장면이 다른 장면으로 넘어간다 | `pat-wipe`, `pat-focus-pull` |

새 모션을 추가하기 전에는 [motion/README.md](motion/README.md)를 먼저 읽으십시오.

---

## 최종 출력: HTML → PNG + PDF + PPTX

완성된 덱은 별도로 PDF나 PPTX를 다시 디자인하지 않습니다.

`tools/export_deck.py`가 먼저 린터를 실행하고, 검증된 **1920×1080 최종 정적 프레임**을 캡처한 뒤 같은 PNG 프레임으로 PDF와 PPTX를 만듭니다.

```bash
python tools/export_deck.py deck.html
```

출력 위치를 지정하려면:

```bash
python tools/export_deck.py deck.html --out dist/deck
```

결과:

```text
dist/deck/
├── frames/
│   ├── slide-001.png
│   ├── slide-002.png
│   └── ...
├── deck.pdf
├── deck.pptx
├── lint.json
└── manifest.json
```

이 방식의 장점:

- HTML, PDF, PPTX가 같은 최종 프레임을 사용
- 출력 포맷별 레이아웃 차이 최소화
- 린터 오류가 있으면 기본적으로 내보내기 중단
- HTML은 라이브 발표용
- PDF/PPTX는 정적 전달용

`--skip-lint`는 검증을 생략해야 하는 예외 상황에서만 사용합니다.

---

## 리포지토리 구조

```text
SKILL.md
├─ 제작 규칙과 마크업 계약

tools/
├─ slide_lint.py        기본 린터
├─ copy_lint.py         한국어 카피 검사
├─ sports_qa.py         스포츠 레이아웃 QA
├─ export_deck.py       PNG/PDF/PPTX 출력
├─ lint_all.sh          전체 덱 린트
└─ verify.sh            전체 5단계 품질 게이트

tests/
├─ linter_selftest.py
├─ motion_check.py
├─ sports_check.py
├─ copy_lint_selftest.py
└─ fixtures/

motion/
├─ deck-motion.js
├─ deck-shell.js
├─ sports.css
├─ motion.css
├─ README.md
└─ patterns/

references/
├─ korean-copy.md
├─ sports-decks.md
├─ runtime-contract.md
├─ geometry-qa.md
├─ motion-timing.md
└─ SOURCES.md

examples/
├─ reference-3slides.html
└─ ...

assets/fonts/
└─ Pretendard Variable
```

---

## 새 덱을 만들 때 권장 순서

1. `SKILL.md`의 제작 규칙을 적용합니다.
2. 1920×1080 고정 스테이지를 만듭니다.
3. 한 슬라이드에 핵심 메시지 하나만 배치합니다.
4. 한국어 덱이면 먼저 자연스러운 한국어 카피를 확정합니다.
5. 사진과 정보의 역할을 분리합니다.
6. 강조가 필요하면 실제 대상에 바인딩합니다.
7. 모션은 관계를 설명할 때만 추가합니다.
8. 정적 상태만으로도 완성된 화면인지 확인합니다.
9. `slide_lint.py`로 기하 검사를 실행합니다.
10. 한국어 덱은 `copy_lint.py --strict`를 실행합니다.
11. 스포츠 덱은 `sports_qa.py`까지 실행합니다.
12. `tools/verify.sh`가 `ALL GREEN`인지 확인합니다.
13. `export_deck.py`로 최종 결과물을 출력합니다.

---

## 주요 참고 문서

- [SKILL.md](SKILL.md) — 제작 규칙 전문
- [한국어 카피 가이드](references/korean-copy.md) — 자연스러운 한국어 슬라이드 카피
- [스포츠 덱 가이드](references/sports-decks.md) — 사진·엠블럼·순위표·경기 그래픽
- [런타임 계약](references/runtime-contract.md) — `.deck-live`, 단계, 정적 상태 규칙
- [기하 QA](references/geometry-qa.md) — 배치·강조 바인딩 검사 방식
- [모션 타이밍](references/motion-timing.md) — 모션 길이와 이징 근거
- [모션 라이브러리](motion/README.md) — 15개 모션 패턴
- [출처](references/SOURCES.md) — 타이밍·방법론 출처

---

## 라이선스와 출처

규칙 문서, 린터, 테스트, 예제, 모션 라이브러리는 이 리포지토리의 작업물입니다.

모션 타이밍과 방법론의 출처는 `references/SOURCES.md`에 정리되어 있습니다.

Pretendard Variable은 SIL Open Font License를 따르며 `assets/fonts/`에 포함되어 있습니다.
