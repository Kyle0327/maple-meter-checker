# Maple meter checker

메이플스토리 클래식 월드의 **경험치·메소와 사냥 시간**을 게임 위에서 확인하는 Windows 앱입니다.

## [⬇ Windows용 다운로드](https://github.com/Kyle0327/maple-meter-checker/releases/latest/download/MapleMeterChecker-Windows-x64.zip)

**무료 다운로드 · GitHub 로그인 불필요 · Python 설치 불필요**

현재 배포: **2.1.1 / Windows x64** · [업데이트 내용과 검사 결과](https://github.com/Kyle0327/maple-meter-checker/releases/latest)

### Mac 테스트 버전

**macOS 14 이상** · CrossOver에서 게임이 정상 실행되는 환경을 대상으로 합니다.

- [Apple Silicon (M 시리즈) 다운로드](https://github.com/Kyle0327/maple-meter-checker/releases/download/mac-v2.2.0-preview.1/MapleMeterChecker-macOS-arm64-preview.zip)
- [Intel Mac 다운로드](https://github.com/Kyle0327/maple-meter-checker/releases/download/mac-v2.2.0-preview.1/MapleMeterChecker-macOS-x86_64-preview.zip)
- [Mac 사용 안내](macos/README-mac.txt) · [테스트 버전 변경 사항](https://github.com/Kyle0327/maple-meter-checker/releases/tag/mac-v2.2.0-preview.1)

앱을 응용 프로그램 폴더로 옮긴 뒤 화면 기록 권한을 허용하고, 창 목록에서 게임 창을 선택하세요. Mac 기본 시작/일시정지 단축키는 **Control + Option + S**입니다.

**실제 CrossOver 게임 인식은 사용자 테스트 전입니다.** Apple Silicon·Intel에서 빌드 및 앱 시작 테스트를 거칩니다. Apple Developer ID 서명·공증은 아직 없어 Gatekeeper가 차단할 수 있는 테스트 빌드입니다. 일반 사용자용 서명·공증과 실기기 검증은 남아 있습니다.

아래 안내와 단축키 표는 Windows 기준이며, Mac은 위의 별도 사용 안내를 확인해 주세요.


### 시작하기

1. 위 **Windows용 다운로드**를 누릅니다.
2. 받은 ZIP 파일을 우클릭하고 **모두 압축 풀기**를 선택합니다.
3. 압축을 푼 폴더에서 **MapleMeterChecker.exe**를 실행합니다.
4. 게임을 켜고 표시 항목을 선택한 뒤 **측정 시작**을 누릅니다.

**`_internal` 폴더는 필수입니다. EXE와 함께 두세요.** 기존 버전은 종료하고 새 버전을 실행해 주세요. `Code → Download ZIP`은 앱 다운로드가 아닙니다.

### 표시할 수 있는 항목

| 구분 | 표시 항목 |
|---|---|
| 경험치 | 누적 / 분당 / 30분 / 1시간, 수치 또는 % |
| 메소 | 누적 / 분당 / 30분 / 1시간 |
| 시간 | 측정 시간 |

분당·30분·1시간 값은 측정 중 평균 속도로 계산한 예상치입니다. 글자와 배경의 투명도를 따로 조절하며, 패널을 게임 밖과 다른 모니터로 옮길 수 있습니다.

### 기본 단축키

| 단축키 | 동작 |
|---|---|
| Ctrl + Alt + F8 | 시작 / 일시정지 / 계속 측정 |
| Ctrl + Alt + F9 | 설정 열기 |
| Ctrl + Alt + F10 | 위치 잠금 / 클릭 통과 |
| Ctrl + Alt + R | 초기화 |
| Ctrl + Alt + E | 경험치 수치 ↔ % |

단축키는 설정에서 변경할 수 있습니다. 배경이 투명해도 패널의 **이동** 손잡이를 잡으면 옮길 수 있습니다.

### 보안 검사와 경고 안내

2.1.1은 실행 시 임시 폴더에 실행 환경을 풀던 단일 EXE 방식을 EXE와 필수 파일을 함께 제공하는 방식으로 변경했습니다. UPX 압축은 사용하지 않습니다.

2026-11-05, 제작 PC의 **Microsoft Defender**로 2.1.1 배포 폴더와 최종 ZIP을 각각 검사했으며 **위협이 발견되지 않았다는 결과**를 받았습니다. 기능 테스트 31개와 앱 시작·화면 표시도 확인했습니다. 검사 정보 및 파일 해시는 [릴리스](https://github.com/Kyle0327/maple-meter-checker/releases/latest)에 첨부되어 있습니다.

앱은 **전자서명되지 않았습니다.** 이번 검사만으로 모든 PC·백신에서 안전하거나 차단되지 않는다고 보장하지 않습니다. 기존 2.1이 다른 PC에서 삭제되었다는 제보는 있으나 정확한 탐지명은 아직 확인되지 않았습니다. **오탐 문제가 완전히 해소되었다고 확정하지 않습니다.**

보안 프로그램이 차단하면 실행을 중단하고 Windows 보안 → 바이러스 및 위협 방지 → 보호 기록에서 **탐지명과 앱 버전**을 확인해 [이슈](https://github.com/Kyle0327/maple-meter-checker/issues)에 알려 주세요. 개인정보가 들어간 전체 기록은 올리지 마세요. 백신 끄기나 검사 제외 등록을 권장하지 않습니다.

### 동작과 지원 범위

- 화면에 보이는 숫자와 획득 메시지를 읽습니다. 게임 메모리 접근이나 게임 프로세스에 코드 주입을 하지 않습니다.
- 앱 자체에 서버 전송, 계정 로그인, 자동 스크린샷 저장 기능이 없습니다.
- 설정과 오류 기록은 PC의 `checker-data` 폴더에 저장합니다. 배포 ZIP에는 개인 설정·게임 캡처·기록이 포함되지 않습니다.
- Windows 11 x64에서 확인했습니다. 실제 1920×1200 및 2560×1440 화면에서 인식을 확인했으며, 모든 해상도·UI 조합을 검증한 것은 아닙니다.
- 게임 창 가림·최소화·빠르게 사라진 메시지로 메소가 누락될 수 있습니다.
- Nexon의 공식 프로그램이 아닌 독립 제작 도구입니다.

이 저장소는 앱 다운로드와 사용 안내를 제공합니다. 포함된 실행 환경과 글꼴의 라이선스는 배포 폴더의 `licenses`에서 확인할 수 있습니다.
