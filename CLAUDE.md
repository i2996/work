# WORK SPACE — Claude 작업 규칙

## 작업 마무리: PR 만들고 main 에 머지까지
사용자가 요청한 작업이 끝나면 따로 묻지 말고 아래 순서로 끝까지 진행한다.

1. 지정된 작업 브랜치에 커밋하고 push 한다.
2. main 으로 가는 PR 을 만든다. (PR 설명은 한국어로 짧게, 바뀐 점 위주)
3. 그 PR 을 바로 머지한다. (squash merge)
4. 사용자에게 PR 링크와 머지 결과를 알려준다.

주의
- main 에 머지되면 GitHub Actions 가 exe 를 빌드해 릴리스로 올리고, 사용자의 프로그램이 자동 업데이트로 받는다.
  그러니 머지 전에 아래 "확인" 을 반드시 통과시킨다. 확인이 실패하면 머지하지 말고 사용자에게 알린다.
- 작업 브랜치의 이전 PR 이 이미 머지됐다면 같은 이름으로 최신 main 에서 브랜치를 다시 만들어 작업한다.

## 확인 (머지 전)
- `python3 -m py_compile work_space.py`
- 화면 코드(HTML/CSS/JS 문자열)를 바꿨다면 Playwright 로 페이지를 띄워 콘솔 오류가 없는지, 바꾼 기능이 동작하는지 확인한다.
  pywebview 없이 `page('main')` 결과 HTML 을 파일로 저장해 열면 되고, 데이터는 localStorage 의 `ws_state` 에 저장된다.
- `__pycache__` 같은 임시 파일은 커밋하지 않는다.

## 프로젝트 개요
- `work_space.py` 한 파일짜리 업무 관리 프로그램 (pywebview + 내장 HTML/CSS/JS).
- 데이터: exe 옆 `workspace_data.json`.
- `APP_VERSION = "dev"` 줄은 빌드 때 빌드 번호로 바뀌므로 건드리지 않는다.
- 사용자와는 한국어로 대화한다.
