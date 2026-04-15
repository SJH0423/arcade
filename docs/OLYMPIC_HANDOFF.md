# OLYMPIC 핸드오프 문서

> 다음 세션에서 올림픽 종목 추가 작업을 이어서 할 때 참고. **컨텍스트 0** 에서 시작해도 5분 안에 읽고 작업 재개 가능하도록 작성됨.

마지막 작업 시점: 2026-04-14
프로젝트: `aijjang-arcade` (AI Space)

## 1. 현재 상태

| 종목 | 파일 | 상태 |
|---|---|---|
| 100m 단거리 | `olympic_100m.html` | ✅ 완료 (3 라운드 시스템 적용) |
| 멀리뛰기 | `olympic_longjump.html` | ⏸ 미구현 (COMING SOON) |
| 창던지기 | `olympic_javelin.html` | ⏸ 미구현 |
| 110m 허들 | `olympic_hurdles.html` | ⏸ 미구현 |
| 높이뛰기 | `olympic_highjump.html` | ⏸ 미구현 |
| 해머던지기 | `olympic_hammer.html` | ⏸ 미구현 |

- **STADIUM** (`olympic.html`) — 메뉴 + 점수 누적 + 랭킹 + 이름 등록 완료
- **스프라이트 미리보기** (`olympic_preview.html`) — RUN/VICTORY/DEFEAT 3 모드 검수용
- **메인 ARCADE 인덱스** (`index.html`) — OLYMPIC 카드 추가 안 됨 (필요 시 추가)

## 2. 파일 구조 + 평탄화 유의

```
ai-space-public/arcade/
├── OLYMPIC_HANDOFF.md      ← 이 파일 (deploy 세션에 담지 말 것)
├── olympic.html            ← STADIUM (서브 메뉴)
├── olympic_preview.html    ← 스프라이트 검수
├── olympic_100m.html       ← 100m 게임 (참조 구현)
└── olympic_*.html          ← 추가 종목 (예정)
```

**중요**: AI Space 는 업로드 시 디렉토리 프리픽스를 stripping함. `arcade/olympic.html` → 컨테이너 `/app/olympic.html` 로 떨어짐. HTML 내부 링크는 **상대 경로** 사용 (`href="olympic_100m.html"`).

## 3. 공통 자산

### 스프라이트 (16×24 픽셀)

- **6프레임 RUN 사이클** — 달리기. 프레임 0,2 = contact, 1,3 = passing, 4,5 = airborne extreme
- **VICTORY_FRAME** — 양팔 V자 만세, 폴짝폴짝 (sin 함수 12px 진폭)
- **DEFEAT_FRAME** — OTL 좌절 (좌측 머리, 우측 다리 접힘)
- **drawTears(ox, oy, scale)** — 눈물 3개 위상차 낙하 애니메이션 (DEFEAT 와 함께 사용)

### 컬러 팔레트

```js
const COLORS = {  // 플레이어 (빨강)
  '.': null,
  'S': '#fdba74',  // skin
  'H': '#7c2d12',  // dark hair
  'B': '#dc2626',  // red shirt
  'W': '#fef3c7',  // white shirt detail (가슴 흰점은 victory/defeat 에서 제거됨)
  'P': '#1e3a8a',  // blue shorts
  'F': '#0f0f0f',  // black shoes
  'O': '#f97316',  // shoe stripe
};
const COLORS_AI = {  // AI (파랑)
  '.': null, 'S': '#fdba74', 'H': '#1e293b',
  'B': '#3b82f6', 'W': '#dbeafe', 'P': '#7c2d12',
  'F': '#0f0f0f', 'O': '#22d3ee',
};
```

### renderSprite 시그니처

```js
renderSprite(ctx, frameOrIdx, ox, oy, scale, palette)
// frameOrIdx: number → FRAMES[idx], 또는 raw frame array (VICTORY_FRAME 등)
// palette: COLORS 또는 COLORS_AI (생략 시 COLORS)
```

## 4. localStorage 세션 스키마

```js
const SESSION_KEY = 'olympicSession';
{
  startedAt: 1697000000000,
  events: {
    "100m":     {raw: 6.42, pts: 950},  // raw = 종목별 단위 (시간/거리)
    "longjump": null,                    // null = 미플레이
    ...
  }
}
```

- 종목별로 **최종 점수만** 저장 (라운드 상세 X)
- `raw` 와 `pts` 둘 다 저장 — STADIUM 카드에 둘 다 표시

## 5. 결정사항 (모든 종목 공통)

### 라운드 시스템

- **각 종목 = 3 라운드**
- **점수 합산**: 3 라운드 중 **최고 기록만** (실제 올림픽 방식)
- **AI 2-0 조기 종료**: aiWins ≥ 2 시 즉시 final
- **AI 시간 점진 강화**: R1 (느림) → R2 (중간) → R3 (빠름)
- **라운드 사이**: Space 수동 진행 + 10초 무입력 자동
- **라운드 사이 화면 (drawRoundEnd)**: 결과 + 누적 + 다음 AI 시간 + 10초 게이지
- **최종 화면 (drawFinal)**: 라운드 표 + 최종 점수 + ENTER 안내 (자동 이동 X)
- **forfeit (실격)**: AI 골인 후 8초 내 못 끝내면 자동 DQ → 그 라운드 AI 안 그림 (플레이어 혼자 OTL)
- **재시도 정책**: 세션 내 잠금. NEW GAME 으로만 재시도

### STADIUM 잠금

- 완료된 카드는 클릭 불가 (`.done` 클래스 + 우상단 🔒 LOCKED)
- 미구현 종목은 회색 + "COMING SOON" + "예정" 라벨 (`.coming` 클래스, `playable:false`)
- 등록 후 (`submitted=true`) 전체 카드 잠금 + REGISTERED 배너 + PLAY AGAIN 버튼

### 점수 환산식

- 종목별로 다른 선형 환산. 100m 기준: `pts = (14 - time) / 8 * 1000`, 0~1000 캡
- **0pt 컷**: 일반인 누구나 도달 불가능한 수준
- **1000pt**: 진심 진력했을 때 도달 가능
- 6종목 만점 합산 = **6000pt** (현재는 100m 만 → MAX_TOTAL = 1000)
- **메달**: Gold ≥83% / Silver ≥58% / Bronze ≥33% (자동 계산)

### 이름 등록

- 클래식 3슬롯 A-Z 사이클 (starwing 패턴)
- ↑↓: 글자 변경 / ←→: 슬롯 이동 / Enter: 확정 / Esc: 취소
- 배포 환경에서만 동작 (`/api/ranking/olympic`). 로컬 file:// 에서는 fetch 실패

## 6. 100m 튜닝 상수

```js
const MAX_SPEED = 11;
const PRESS_GAIN = 0.38;       // 한 번 누름당 속도 증가량 (40% 미만 = 너무 어려움)
const DECAY = 0.065;           // 프레임당 속도 감속
const GOAL = 100;              // meters
const METERS_PER_SPEED = 0.045;
const AI_TIMES = [7.80, 7.50, 7.20];  // R1, R2, R3
const FORFEIT_DEADLINE_MS = 8000;
```

**현재 밸런스**: 진심 연타 ~6초 / 캐주얼 ~9초 / AI R1 7.80s 무난, R3 7.20s 박빙

## 7. 워크플로우 (스프라이트 변경 시)

1. **olympic_preview.html 에서 디자인** (RUN/VICTORY/DEFEAT 모드 토글)
2. 검수 후 마음에 들면 → 게임 파일에 **수동 동기화** (현재 공유 JS 파일 없음 — TODO)
3. **공유 JS 파일 추출은 미완** — 5종목 추가 시 한 번에 정리하면 좋음 (`olympic_sprites.js`)

## 8. 남은 5종목 — 메커닉 제안

| 종목 | 핵심 메커닉 | 키 입력 | 점수 환산 |
|---|---|---|---|
| **멀리뛰기** | 연타로 속도 → 도약 라인에서 Space 로 점프 + 각도 타이밍 (각도 게이지가 흐를 때 적절한 순간) | A/D 연타 + Space (점프) | 거리(m) → pts |
| **창던지기** | 짧은 도움닫기 + 각도 게이지 + 파워 게이지 | A/D 연타 + Space (던지기) | 거리(m) → pts |
| **110m 허들** | 100m 와 동일하지만 허들 8개. 각 허들 앞에서 Space 로 점프 (실패 시 감속) | A/D 연타 + Space (허들마다 점프) | 시간(s) → pts |
| **높이뛰기** | 짧은 도움닫기 + 도약 + 막대 통과 (높이 증가 시 1cm 단위) | A/D 연타 + Space | 높이(m) → pts |
| **해머던지기** | 회전 게이지 (A/D 빠르게) + 릴리스 타이밍 | A/D 연타 + Space | 거리(m) → pts |

## 9. 새 종목 추가 체크리스트

```
[ ] olympic_<event>.html 파일 생성 (olympic_100m.html 복사 후 수정)
[ ] FRAMES, VICTORY_FRAME, DEFEAT_FRAME, drawTears 복사 (또는 공유 JS)
[ ] EVENT_ID 변경 ('100m' → '<event>')
[ ] 게임 메커닉 구현 (핵심 차별화 포인트)
[ ] calcPoints() 환산식 작성
[ ] 라운드 시스템 + AI 데드라인 그대로 적용 (또는 종목 특성에 맞게 변형)
[ ] saveResult() 호출로 localStorage 갱신
[ ] olympic.html 의 EVENTS 배열에서 해당 종목 playable: false → true 변경
[ ] olympic_preview.html 에 새 포즈/애니메이션 있으면 검수용 추가
[ ] 패턴 A 로 배포 (전체 파일 세션 + finalize deploy=false + force_rebuild)
[ ] 라이브 검증 — fetch + render + ranking 동작 확인
```

## 10. 배포 패턴 (필수)

`ai-space-public/CLAUDE.md` 의 **패턴 A** 참조. 요약:

```
1. ls 로 배포 대상 폴더 전체 파일 전수 확인
2. create_session(files=[전체 파일], update=true)  ← 누락하면 BUG-008 (repo 삭제)
3. curl 로 각 파일 업로드
4. finalize(deploy=false)                           ← deploy 분리
5. update_project(mode=force_rebuild, wait=true)    ← workspace 캐시 폐기
6. curl 로 내용 검증 (wc -c, grep 식별 문자열)
```

**OLYMPIC_HANDOFF.md 는 deploy 세션에 담지 말 것** (라이브에 doc 노출 X)

배포 대상 파일 (현재 기준 9개):
- `app.py`, `requirements.txt`
- `index.html`
- `bloxfall.html`, `dungeon.html`, `hyperlane.html`, `minecraft.html`, `starwing.html`
- `olympic.html`, `olympic_100m.html`, `olympic_preview.html`

종목 추가하면 그 파일도 세션에 추가.

## 11. 알려진 함정

1. **BUG-008** — `project_upload` 세션 = 스냅샷. 누락 파일 전부 삭제됨. 항상 전체 파일 포함
2. **BUG-009** — `finalize(deploy=true)` workspace stale 캐시. 항상 `force_rebuild` 추가 호출
3. **mode=quick 폐기** — `auto` 도 금지. `force_rebuild` 만 사용
4. **로컬 file:// 에서 API fetch 실패** — 등록 테스트는 배포 환경에서만 가능
5. **스프라이트 동기화 미완** — preview 와 게임 파일에 같은 스프라이트가 중복. 수정 시 둘 다 갱신 필요

## 12. 마지막 작업 상태

- 100m 게임 로컬에서 동작 확인됨
- **배포는 안 한 상태** — 다음 세션에서 사용자가 "배포해" 지시 시 패턴 A 로 진행
- olympic.html 의 `MAX_TOTAL` 은 1000 (100m 만 playable)
- 5종목 추가 시 자동으로 `MAX_TOTAL` 합산 + 메달 임계값 비례 조정됨

## 13. 참고 — 사용자 선호

- **"주인님"** 으로 호칭 (대화에서)
- 결정 빠름. 옵션 A/B/C 제안 시 한 글자로 답변. "다 추천대로" 도 자주 함
- 한글 키워드로 작업 지시 ("진행", "배포", "오케이")
- 색상 자주 트집 — preview 에서 먼저 검수 후 적용 권장
- 스프라이트 디자인은 한 번에 안 끝남 — 2~3회 수정 각오
- TodoWrite/Task 도구는 한글 깨짐 위험. 영어로 작성

---

**다음 세션 시작 시 첫 행동**:
1. 이 문서 읽기 (5분)
2. 100m 게임 로컬에서 동작 확인 (`file:///C:/startcoding/ai-space-public/arcade/olympic.html`)
3. 사용자에게 "어느 종목부터 진행할까요?" 묻기
4. 종목 결정 후 위 9번 체크리스트 따라 진행
