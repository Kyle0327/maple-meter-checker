Maple meter checker 2.1.0 source

Windows 11 / Python 3.14.3에서 빌드. 31개 테스트 통과.

python -m pip install -r requirements.txt
python app.py
powershell -File build.ps1

UI: ui.py / preview.py / theme.py
게임 패널과 자유 이동: overlay.py / placement.py
앱 전용 볼드 글꼴과 아이콘: typography.py
중복 실행 방지: instance.py
측정 및 화면 인식: app.py / session.py / reader.py
검증: test_meter.py / test_checker.py / test_ux.py

Pretendard Bold / ExtraBold는 원본 OTF를 변경하지 않고 앱 실행 중에만 로드합니다.
배포 시 Pretendard-LICENSE.txt와 실행 환경 라이선스 고지를 함께 포함하세요.

배포 ZIP에는 checker-data, fixtures, 테스트 기록이나 게임 캡처를 넣지 않습니다.
현재 사용자 설정은 배포 ZIP 생성 후 로컬 실행 폴더로만 복사했습니다.
