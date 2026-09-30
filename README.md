# WORK SPACE

서버 없이 혼자 쓰는 업무 관리 프로그램 (Python + tkinter).
데이터는 exe와 같은 폴더의 `workspace_data.json` 에 자동 저장됩니다.

## exe 만드는 법
### 방법 1) GitHub Actions (PC에 파이썬 없어도 됨)
1. 이 폴더 전체를 GitHub 저장소에 업로드 (`.github` 폴더 포함, 비공개 저장소 OK)
2. 저장소 > Actions > Build EXE > Run workflow
3. 완료 후 Artifacts 의 `WorkSpace-exe` 다운로드 → `WorkSpace.exe`

### 방법 2) 내 PC (윈도우, 파이썬 설치됨)
`build_exe.bat` 더블클릭 → `dist\WorkSpace.exe`

## 바로 실행 (exe 없이)
```
pip install -r requirements.txt
python work_space.py
```

## 백업/이전
`workspace_data.json` 파일만 복사하면 됩니다.
