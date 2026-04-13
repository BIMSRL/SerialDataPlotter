# Python 독립 실행 파일 만들기 (Windows)

Python 스크립트를 `.exe` 파일로 패키징하는 방법. 핵심 도구는 **PyInstaller**다.

---

## 기본 흐름

```
.py 소스코드  →  PyInstaller  →  .exe 실행파일 (Python 없이도 실행 가능)
```

---

## 1. PyInstaller 설치

```bash
pip install pyinstaller
```

> 설치 후 `pyinstaller --version`으로 정상 설치 여부를 확인한다.

---

## 2. 기본 빌드 명령

```bash
# 단일 폴더로 출력 (빌드 속도 빠름)
pyinstaller my_script.py

# 단일 .exe 파일로 출력 (배포에 유리)
pyinstaller --onefile my_script.py

# 콘솔 창 숨김 (GUI 앱 전용)
pyinstaller --onefile --windowed my_script.py

# 아이콘 지정
pyinstaller --onefile --windowed --icon=app.ico my_script.py
```

---

## 3. 출력 디렉토리 구조

```
my_project/
├── build/               ← 임시 빌드 파일 (무시해도 됨)
├── dist/
│   └── my_script.exe    ← 배포할 파일
├── my_script.spec       ← 빌드 설정 파일
└── my_script.py
```

---

## 4. `.spec` 파일로 세밀한 제어

반복 빌드나 복잡한 프로젝트에서는 `.spec` 파일을 직접 편집하는 것이 효율적이다.

```python
# my_script.spec
a = Analysis(
    ['my_script.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/', 'assets/')],    # 리소스 파일 포함
    hiddenimports=['numpy', 'pandas'], # 누락 모듈 명시
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='MyApp',
    debug=False,
    console=False,   # GUI면 False
    icon='app.ico',
)
```

`.spec` 파일로 빌드:

```bash
pyinstaller my_script.spec
```

---

## 5. 주요 옵션 정리

| 옵션 | 설명 | 비고 |
|------|------|------|
| `--onefile` | 단일 `.exe`로 묶음 | 배포 시 권장 |
| `--windowed` / `--noconsole` | 콘솔 창 숨김 | GUI 앱 전용 |
| `--icon=app.ico` | 아이콘 설정 | `.ico` 형식 필요 |
| `--add-data "src;dest"` | 리소스 파일 포함 | 구분자 `;` (Windows) |
| `--hidden-import=모듈명` | 누락 모듈 수동 추가 | 동적 import 시 필요 |
| `--name=AppName` | 출력 파일 이름 지정 | |
| `--upx-dir` | UPX 압축으로 용량 축소 | UPX 별도 설치 필요 |

> **Windows 주의:** `--add-data`의 경로 구분자는 `;`이다. Linux/Mac은 `:`를 사용하므로 혼동 주의.

---

## 6. 자주 발생하는 문제

### ① 모듈을 찾지 못하는 경우

동적 import 시 PyInstaller가 의존성을 자동 감지하지 못하는 경우:

```bash
pyinstaller --onefile --hidden-import=모듈명 my_script.py
```

### ② 리소스 파일 경로 오류

`--onefile` 빌드 시 런타임 경로가 달라지므로 코드에서 아래와 같이 처리한다:

```python
import sys, os

def resource_path(relative_path):
    """PyInstaller 임시 폴더 또는 실제 경로를 반환"""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)

# 사용 예
img_path = resource_path("assets/logo.png")
```

### ③ 백신 프로그램 오탐 (False Positive)

PyInstaller `.exe`는 백신 소프트웨어에서 악성코드로 오탐될 수 있다.  
코드 서명(Code Signing) 인증서를 적용하거나, 배포 시 사용자에게 예외 추가를 안내한다.

---

## 7. 대안 도구 비교

| 도구 | 특징 | 적합한 경우 |
|------|------|------------|
| **PyInstaller** ★ | 가장 범용적, 커뮤니티 크다 | 대부분의 경우 |
| **cx_Freeze** | 크로스플랫폼, 설정 복잡 | 다중 플랫폼 동시 지원 |
| **Nuitka** | Python → C++ 컴파일, 성능 우수 | 실행 속도가 중요한 경우 |
| **auto-py-to-exe** | PyInstaller GUI 래퍼 | 명령줄이 불편한 경우 |

---

## 핵심 명령 요약

| 상황 | 명령 |
|------|------|
| 일반 스크립트 | `pyinstaller --onefile my_script.py` |
| GUI 앱 (tkinter 등) | `pyinstaller --onefile --windowed my_script.py` |
| 리소스 파일 포함 | `.spec` 파일 편집 + `resource_path()` 함수 사용 |
| 누락 모듈 대응 | `--hidden-import=모듈명` 옵션 추가 |
