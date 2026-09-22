# html-slide: 모듈 조합형 슬라이드 엔진

완성된 템플릿부터 고르지 않고, **슬라이드의 전달 목적부터 정한 뒤 필요한 부품을 조합**합니다.
AI는 주제와 자료를 해석해 JSON 설계서를 작성하고, 엔진은 메타데이터 검색, 슬롯 호환성 검사,
HTML 생성과 화면 검증을 수행합니다. 엔진 자체에 LLM이나 임베딩 검색 서버는 없습니다.

## 기본 흐름

```sh
python -m pip install -r requirements-modular.txt
python -m playwright install chromium
npm install
python tools/compose_deck.py catalog
python tools/compose_deck.py search --intent ranking --theme sports-broadcast
python tools/compose_deck.py search --type typography --theme education --domain education --audience elementary --tone clear
python tools/compose_deck.py init --preset sports-match-report --out deck.json
python tools/compose_deck.py plan deck.json --out plan.json
python tools/compose_deck.py build deck.json --out deck.html
python tools/verify_modular.py deck.html --out dist/qa
python tools/export_modular.py deck.html --out dist/export
```

Python 3.10 이상이 필요합니다. HTML 생성에는 jsonschema, 브라우저 검사에는 Playwright와 Chromium,
PPTX 출력에는 Node.js와 PptxGenJS가 추가로 필요합니다. 기존 Chromium은 `CHROME_PATH`로 지정할 수 있습니다.

테마는 모서리와 경계 같은 **디자인 문법**을, 레이아웃은 화면 골격과 슬롯을, 정보 모듈은 데이터 표현을 맡습니다.
폰트 체계, 메인 색상, 차트 색상은 각각 `styles/typography`, `styles/palettes`, `styles/dataviz`의
독립 스타일 팩입니다. 이미지와 모션도 별도 모듈입니다. 프리셋은 검증 가능한 조합 예시일 뿐,
페이지 구성을 강제하지 않습니다.

현재 레이아웃 10종, 정보 모듈 11종, 이미지 모듈 2종, 모션 5종, 테마 7종에 더해
타이포그래피 7종, 메인 팔레트 8종, 데이터 시각화 팔레트 5종, 프리셋 3종이 등록돼 있습니다.
`modules/`, `themes/`, `styles/` 아래의 manifest를 자동으로 찾아 사용하므로 중앙 목록을 수정할 필요가 없습니다.
슬롯 용량이나 데이터 형식이 맞지 않으면 내용을 버리거나 축소하지 않고 오류로 중단합니다.

스타일은 덱 단위로 한 번 선택합니다. `style.typography`, `style.palette`, `style.dataviz`를
`auto`로 두고 domain, audience, tone, density 신호를 주면 theme 추천도와 함께 점수화합니다.
선택 결과와 이유, 상위 대안은 plan에 남습니다. 마음에 들지 않으면 특정 스타일 ID만 고정하고
레이아웃과 내용은 그대로 다시 빌드할 수 있습니다.

## 실제 결과 확인

`examples/modular-showcase.json`을 CLI로 빌드하면 모듈을 조합한 12장 HTML 예제가 생성됩니다.
스포츠 순위와 점수, 지표와 추이, 학습 과정 등은 **구성 시연용 가상 데이터**입니다.
원본 설계서는 같은 이름의 JSON 파일입니다.

하단 인디케이터, 방향키, 화면 좌우 클릭, 정적/동적 전환(S), 전체 목록(O), 전체 화면(F)을 지원합니다.
출처는 전체 목록에서 확인합니다. 모션을 끄거나 자바스크립트를 비활성화해도 최종 정보가 남습니다.
PDF와 PPTX는 동일한 1920x1080 최종 화면으로 만듭니다. PPTX는 편집형 도형이 아닌 정적 이미지 방식입니다.

타이포그래피 팩은 제목, 본문, 숫자 역할별 폰트 스택과 굵기/행간을 선택하지만 별도 폰트 바이너리를
추가로 묶지 않습니다. `--font path/to/font.woff2`를 명시하면 사용 권한이 확인된 로컬 폰트를
HTML에 내장해 선택된 역할 체계에 적용합니다. 기본 생성은 시스템 폰트를 쓰고 환경별 글자 폭 차이를
경고하므로 배포용 덱은 최종 폰트 상태에서 다시 검사하십시오.

## 유지한 것과 달라진 것

기존 저장소의 `motion/`, `templates/`, 예전 예제와 검사 도구는 호환 경로로 보존합니다.
기존 HTML은 `tools/export_deck.py`, 새 모듈형 HTML은 `tools/export_modular.py`로 출력합니다.
한 HTML에 두 런타임을 동시에 넣지 않습니다. 새 작업의 기본 진입점은 `SKILL.md`입니다.

설계 이유와 역할 분리는 `references/modular-architecture.md`, 자동 아트디렉션과 스타일 팩 규칙은
`references/art-direction.md`, 모듈 추가 방법은 `references/module-authoring.md`,
기존 덱의 전환 방법은 `references/migrating-v1.md`에 정리했습니다.

## 검증 범위

```sh
python -m unittest discover -s tests -p 'test_modular.py'
python tests/modular_runtime_check.py
python tools/compose_deck.py build examples/modular-showcase.json --out examples/modular-showcase.html
python tools/verify_modular.py examples/modular-showcase.html --out dist/qa
```

화면 경계, 텍스트 넘침, 블록 겹침, 이미지 로딩, 강조 대상 결합, 네 가지 화면 크기,
정적 전환, 단계 진행과 역행, 전체 목록, 축소 모션, 인쇄 복원, 자바스크립트 없는 최종 정보를 검사합니다.
현재 검사기는 관리형 Chromium을 위해 `set_content`를 사용하므로 최초 URL의 쿼리와 딥링크 로딩은
검사 범위에 포함하지 않습니다. 새 덱마다 화면 검사를 실행하고 스크린샷도 확인해야 합니다.
