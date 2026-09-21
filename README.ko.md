# html-slide

[English README](README.md) · **한국어**

HTML 프레젠테이션을 만들되, **레이아웃·강조·모션·카피·출력을 자동 검증하는 슬라이드 제작 스킬**입니다.

이 리포지토리는 특정 디자인 템플릿 하나를 강제하지 않습니다. 코어는 어떤 덱에도 공통으로 적용되는 **제작 규칙과 검증 계층**이고, 시각 스타일은 필요할 때 `templates/`에서 선택하거나 새로 설계합니다.

## 핵심 구성

- `SKILL.md` — 제작 규칙과 마크업 계약
- `tools/slide_lint.py` — 정적 검사 + 실제 브라우저 기하 검사
- `tests/motion_check.py` — 모션·단계·강조 바인딩 회귀 테스트
- `tools/copy_lint.py` — 한국어 덱의 불필요한 영어와 템플릿 문구 검사
- `tools/export_deck.py` — 검증된 최종 프레임을 PNG·PDF·PPTX로 출력
- `templates/` — 선택 가능한 디자인 출발점
- `motion/` — 관계를 설명하는 모션 패턴 라이브러리

핵심 목표는 하나입니다.

> **스크린샷 한 장에서는 그럴듯하지만 실제 발표·리사이즈·내보내기에서 깨지는 슬라이드를 만들지 않는다.**

---

## 빠른 시작

브라우저 계측에는 Playwright와 Chromium이 필요합니다.

```bash
pip install playwright
playwright install chromium
```

PPTX 출력까지 사용할 경우:

```bash
pip install python-pptx
```

기준 덱 검사:

```bash
python tools/slide_lint.py examples/reference-3slides.html
```

스크린샷까지 저장:

```bash
python tools/slide_lint.py examples/reference-3slides.html --shots out/shots
```

저장소 전체 검증:

```bash
bash tools/verify.sh
```

출력 마지막이 다음과 같아야 합니다.

```text
ALL GREEN
```

특정 Python 환경을 사용하려면:

```bash
PYTHON=/path/to/venv/bin/python bash tools/verify.sh
```

---

## 코어 원칙

### 1. 강조는 실제 대상에 묶는다

강조 효과는 대상 요소의 DOM에 연결되어야 합니다.

허용되는 방식:

- 대상의 자식 요소
- `data-target`으로 묶인 요소
- 대상의 실제 위치에서 계산한 복제

슬라이드 좌표에 `left/top` 값을 직접 써서 그린 강조 박스는 사용하지 않습니다.

린터는 여러 뷰포트에서 실제 대상과 강조 요소의 박스를 측정해 드리프트를 검사합니다.

### 2. 한 슬라이드에는 핵심 하나만 둔다

제목·본문·예시가 모두 하나의 판단을 향해야 합니다.

기본 방향은 **설명보다 보여 주기**입니다.

- 시각 예시 / 실제 화면 / 도식: 약 70%
- 텍스트: 약 30%

내용에 따라 비율은 바꿀 수 있지만, 빈 공간을 채우기 위해 설명문을 늘리지는 않습니다.

### 3. 모션은 관계를 설명할 때만 쓴다

기본 애니메이션 속성은 `transform`과 `opacity`입니다.

다음처럼 실제 의미가 있을 때 사용합니다.

- 이 요소가 핵심이다
- 이전 상태가 이후 상태로 바뀌었다
- 값이 이만큼 변했다
- 이 순서로 진행된다
- 두 요소가 연결되어 있다

모든 요소를 순서대로 등장시키거나 반복적으로 반짝이게 하지 않습니다.

### 4. 모션이 없어도 완성된 화면이어야 한다

정적 상태가 최종 상태입니다.

JavaScript가 없거나, 모션 감소 설정이 켜져 있거나, PDF/PPTX로 출력해도 정보가 빠지면 안 됩니다.

라이브 발표 모션은 `.deck-live` 상태에서만 활성화합니다.

### 5. 1920×1080 좌표계를 통째로 축소한다

슬라이드 내부를 화면 크기에 따라 재배치하지 않고, 고정 1920×1080 스테이지를 `transform: scale()`로 맞춥니다.

이 방식은 다음을 안정적으로 유지합니다.

- 강조 바인딩
- 오브젝트 간 거리
- 줄바꿈
- 프레젠테이션 캡처
- PDF/PPTX 최종 프레임

의미 있는 콘텐츠는 기본적으로 가장자리 5% 안쪽의 안전 영역에 둡니다.

### 6. 템플릿은 규칙이 아니라 시작점이다

`templates/`의 파일은 선택 가능한 **시각 문법**입니다.

사용자가 특정 분위기나 장르를 원할 때 참고할 뿐, 모든 덱이 한 템플릿을 따라가면 안 됩니다.

내용이 템플릿과 맞지 않으면 레이아웃을 버리고 새 장면을 설계합니다.

---

## 템플릿

현재 두 개의 기준 시안을 제공합니다.

### 스포츠 방송형 리포트

`templates/sports-broadcast.html`

어두운 방송 그래픽 톤, 높은 수치 대비, 표·비교·미디어가 많은 데이터 리포트에 적합합니다.

상세한 도메인 규칙은 메인 README가 아니라 [템플릿 전용 가이드](templates/sports-broadcast.md)에만 둡니다.

### 강의·개념 설명형

`templates/lecture-editorial.html`

밝은 중성 배경, 단일 강조색, 큰 예시 화면, 원인/결과·단계·전후 비교가 필요한 강의나 발표에 적합합니다.

상세 구조는 [템플릿 전용 가이드](templates/lecture-editorial.md)를 참고합니다.

전체 템플릿 사용 원칙은 [templates/README.ko.md](templates/README.ko.md)에 정리되어 있습니다.

---

## 한국어 카피

한국어 덱은 영문 템플릿을 만든 뒤 단어만 치환하지 않습니다.

제목·라벨·설명은 처음부터 한국어 독자를 기준으로 작성합니다.

영어를 남겨도 되는 대표적인 경우:

- `AI`, `API`, `UI`, `HTML`처럼 널리 쓰이는 약어
- 공식 브랜드·제품명
- 기술 표준
- 원문 인용
- 출처·메타데이터

일반 라벨이 한국어로 더 빠르게 읽히면 한국어가 우선입니다.

예:

| 피할 표현 | 권장 표현 |
|---|---|
| KEY TAKEAWAYS | 핵심 정리 |
| NEXT STEPS | 다음 단계 |
| PROJECT OVERVIEW | 프로젝트 개요 |
| STATUS | 상태 |
| SUMMARY | 요약 |

검사:

```bash
python tools/copy_lint.py deck.html --strict
```

의도적으로 유지한 영문 표기는 해당 요소에 `data-copy-en-ok`를 붙일 수 있습니다.

```html
<span data-copy-en-ok>OpenAI API</span>
```

자세한 편집 규칙은 [references/korean-copy.md](references/korean-copy.md)를 참고합니다.

---

## 품질 게이트

`tools/verify.sh`는 5단계 검증을 실행합니다.

### 1/5 · 전체 덱 린트

`tools/lint_all.sh`

다음을 포함한 기본 규칙을 검사합니다.

- 스테이지 밖으로 나간 콘텐츠
- 잘린 텍스트
- 강조 대상 바인딩
- 안전 영역
- 타이포 단계
- 한글 `keep-all`
- 과도한 내부 간격
- 하단 설명 캡션
- 레이아웃을 흔드는 모션 속성

`examples/`, `motion/patterns/`, `templates/`의 HTML이 모두 검사 대상입니다.

### 2/5 · 린터 자체 테스트

`tests/linter_selftest.py`

고의로 깨뜨린 덱에서 규칙이 실제로 발화하는지 확인합니다.

린터가 조용히 고장 난 상태에서 깨끗한 보고서만 내는 상황을 막습니다.

### 3/5 · 모션 동작 검사

`tests/motion_check.py`

실제 Chromium에서 다음을 확인합니다.

- 정적 상태 완전성
- 단계 진행
- 이전 단계 복귀
- 마지막 단계 정착
- 강조 바인딩
- 대상 위치 안정성
- 전환 모션 종료 상태
- 한글 음절 타이핑

현재 회귀 검사는 **134개**입니다.

### 4/5 · 발표자·템플릿 회귀 검사

공통 발표자 런타임, 키보드 탐색, 모달 격리, 리사이즈, 미디어가 많은 템플릿의 기하 안정성을 확인합니다.

현재 회귀 검사는 **35개**입니다.

### 5/5 · 한국어 카피 린터 자체 테스트

`tests/copy_lint_selftest.py`

한국어 카피 검사가 일반 발표 문구를 기준으로 정상 동작하는지 확인합니다.

현재 자체 테스트는 **8개**입니다.

---

## 모션 라이브러리

`motion/patterns/index.html`에서 전체 패턴을 확인할 수 있습니다.

모션은 **어떻게 보이는가**가 아니라 **무엇을 설명하는가**로 분류합니다.

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

새 모션을 추가하기 전에 [motion/README.md](motion/README.md)를 확인합니다.

---

## 최종 출력

완성된 덱은 PDF와 PPTX를 별도로 다시 디자인하지 않습니다.

`tools/export_deck.py`가 린터를 실행하고, 검증된 **1920×1080 최종 정적 프레임**을 캡처한 뒤 같은 PNG로 PDF와 PPTX를 만듭니다.

```bash
python tools/export_deck.py deck.html
```

출력 위치 지정:

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

HTML은 라이브 발표용, PDF/PPTX는 정적 전달용입니다.

`--skip-lint`는 검증을 생략해야 하는 예외 상황에서만 사용합니다.

---

## 리포지토리 구조

```text
SKILL.md                  코어 제작 규칙

tools/
├─ slide_lint.py          기본 린터
├─ copy_lint.py           한국어 카피 검사
├─ media_qa.py            미디어가 많은 덱의 보조 기하 QA
├─ export_deck.py         PNG/PDF/PPTX 출력
├─ lint_all.sh            전체 덱 린트
└─ verify.sh              전체 품질 게이트

tests/
├─ linter_selftest.py
├─ motion_check.py
├─ template_runtime_check.py
├─ copy_lint_selftest.py
└─ ...

templates/
├─ README.ko.md
├─ sports-broadcast.html
├─ sports-broadcast.md
├─ lecture-editorial.html
└─ lecture-editorial.md

motion/
├─ deck-motion.js
├─ deck-shell.js
├─ motion.css
├─ README.md
└─ patterns/

references/
├─ korean-copy.md
├─ runtime-contract.md
├─ geometry-qa.md
├─ motion-timing.md
└─ SOURCES.md

examples/
└─ ...

assets/fonts/
└─ Pretendard Variable
```

---

## 새 덱을 만들 때 권장 순서

1. `SKILL.md`의 코어 규칙을 적용합니다.
2. 필요하면 `templates/`에서 목적에 맞는 시안을 선택합니다.
3. 한 슬라이드에 핵심 메시지 하나만 잡습니다.
4. 한국어 덱이면 실제 한국어 카피부터 확정합니다.
5. 시각 예시와 설명의 관계를 정합니다.
6. 강조가 필요하면 실제 대상에 바인딩합니다.
7. 모션은 관계를 설명할 때만 추가합니다.
8. 정적 상태만으로도 완성됐는지 확인합니다.
9. `slide_lint.py`를 실행합니다.
10. 한국어 덱은 `copy_lint.py --strict`도 실행합니다.
11. `tools/verify.sh`가 `ALL GREEN`인지 확인합니다.
12. `export_deck.py`로 최종 결과물을 출력합니다.

---

## 주요 참고 문서

- [SKILL.md](SKILL.md) — 코어 제작 규칙
- [템플릿 인덱스](templates/README.ko.md) — 선택 가능한 시각 양식
- [한국어 카피 가이드](references/korean-copy.md) — 자연스러운 한국어 카피
- [런타임 계약](references/runtime-contract.md) — `.deck-live`, 단계, 정적 상태
- [기하 QA](references/geometry-qa.md) — 배치·강조 바인딩 검사
- [모션 타이밍](references/motion-timing.md) — 모션 길이와 이징 근거
- [모션 라이브러리](motion/README.md) — 모션 패턴
- [출처](references/SOURCES.md) — 방법론과 타이밍 출처

---

## 라이선스와 출처

규칙 문서, 린터, 테스트, 예제, 템플릿, 모션 라이브러리는 이 리포지토리의 작업물입니다.

모션 타이밍과 방법론 출처는 `references/SOURCES.md`에 정리되어 있습니다.

Pretendard Variable은 SIL Open Font License를 따르며 `assets/fonts/`에 포함되어 있습니다.
