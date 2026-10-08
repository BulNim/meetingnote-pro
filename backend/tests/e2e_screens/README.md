# 화면 시험 (실제 서버 + 실제 Chrome)

pytest 가 자동으로 돌리지 않는다. 화면 6종의 상태를 사람이 보는 순서대로 눈으로 확인하는 대신 Playwright 로 재현한다.
임시 폴더에 DB 와 스크린샷(`shots/`)을 만들고 끝나면 경로를 알려 준다.

```
.venv\Scripts\pip install playwright        # 시스템 Chrome 을 쓴다 (별도 다운로드 없음)
.venv\Scripts\python backend\tests\e2e_screens\screens_main.py     # 실제 Gemini 를 부른다 (회의_녹음.wav 업로드)
.venv\Scripts\python backend\tests\e2e_screens\screens_extra.py    # 세션 만료 · member 권한 · 정원 초과 등
```
