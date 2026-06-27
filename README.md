# 🧠 Ollama Dashboard

로컬 환경에서 구동되는 Ollama LLM을 Streamlit 기반으로 시각화하고 관리할 수 있는 경량 웹 대시보드 프로젝트입니다.

-----

## 📌 주요 기능 (Features)

* **Ollama LLM 실시간 연동 UI**: 로컬에 기구동 중인 Ollama 인프라 및 모델 리스트와 실시간으로 연동되는 채팅 인터페이스를 제공합니다.
* **Streamlit 기반 웹 대시보드**: 초경량 고효율 프론트엔드 아키텍처를 채택하여 간결하고 반응성이 뛰어난 웹 UI를 구성합니다.
* **확장 가능 구조**: 시스템 자원(CPU/RAM) 및 하드웨어 가속기(NVIDIA GPU) 모니터링 레이어를 손쉽게 결합할 수 있습니다.
* **독립 포트 운영**: 기본 `9999` 포트를 할당받아 기존 포트와의 충돌 없이 안정적인 웹 서비스 환경을 제공합니다.
* **systemd 백그라운드 서비스 지원**: 프로덕션 및 운영 인프라 환경을 위한 백레벨 서비스 자동화 등록 프로세스를 지원합니다(선택 사항).

-----

## 🧱 시스템 요구사항 (Prerequisites)

* **OS**: Ubuntu 20.04 LTS 이상 환경 권장
* **Runtime**: Python 3.10 이상 인프라 환경
* **Dependencies**: Ollama 컴포넌트 설치 및 백엔드 서비스 기구동 상태
* **Hardware**: (권장) 하드웨어 가속을 위한 NVIDIA GPU 및 최신 드라이버

-----

## 📁 프로젝트 구조 (Project Structure)

```text
ollama-dashboard/
├── app.py                     # Streamlit 기반 메인 웹 애플리케이션 소스
├── install.sh                 # 가상환경 및 의존성 패키지 자동화 설치 스크립트
├── start.sh                   # 대시보드 런타임 수동 실행 스크립트
├── ollama-dashboard.service   # 프로세스 데몬화를 위한 systemd 유닛 파일
└── .venv/                     # 격리된 Python 가상환경 폴더 (설치 후 자동 생성)
```

-----

## ⚙️ 설치 가이드 (Installation)

### 1. 필수 시스템 패키지 구성
터미널 가상 셸 환경에 접속하여 Python 필수 구성 요소 및 네트워크 모니터링 도구를 설치합니다.

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv net-tools
```

### 2. 자동 빌드 및 배포 스크립트 실행
제공된 `install.sh` 스크립트에 런타임 실행 권한을 바인딩하고 가상 환경 설치 파이프라인을 기동합니다.

```bash
git clone https://github.com/jasonkim-77/ollma-dashboard-ubuntu
cd ollama-dashboard-ubuntu

chmod +x install.sh
./install.sh
```

> **💡 설치 스크립트가 수행하는 작업:**
> * 격리형 파이프라인 가상 환경(`.venv`) 생성 및 독립 패키지 샌드박싱 환경 구성
> * 코어 라이브러리 의존성 트리 자동 빌드 (`Streamlit`, `Pandas`, `Plotly`, `Requests`, `Ollama`, `Watchdog`)
> * 커널 방화벽(UFW) 정책 내 엔드포인트 `9999` 포트의 인바운드 트래픽 규칙 자동화 추가

-----

## 🚀 실행 및 접속 프로토콜 (Usage)

### 애플리케이션 수동 기동
```bash
chmod +x start.sh
./start.sh
```

### 네트워크 엔드포인트 웹 주소
* **로컬 내부 호스트 접속:** `http://localhost:9999`
* **원격 외부 네트워크 접속:** `http://<YOUR-SERVER-IP>:9999`

-----

## 🔧 systemd 인프라 서비스 데몬화 (Production)

운영 서버 인프라 환경에서 세션을 유지하고 코어 백그라운드 데몬으로 프로세스를 무중단 관리 및 운영하기 위한 절차입니다.

### 1. 서비스 설정 유닛 파일 배치
```bash
sudo cp ollama-dashboard.service /etc/systemd/system/
```

### 2. 시스템 관리 데몬 갱신
```bash
sudo systemctl daemon-reload
```

### 3. 서비스 상시 기동 및 자동 활성화 (부팅 시 자동 링크)
```bash
sudo systemctl enable --now ollama-dashboard
```
*(기동 중인 서비스를 단순 재시작할 경우: `sudo systemctl restart ollama-dashboard`)*

### 4. 프로세스 가용성 및 런타임 상태 모니터링
```bash
sudo systemctl status ollama-dashboard
```

### 5. 표준 출력 및 실시간 서비스 로그 수집
```bash
journalctl -u ollama-dashboard -f
```

-----

## 🔥 네트워크 방화벽 설정 (UFW)

외부 인바운드 트래픽 환경에서 서비스 프록시 영역으로의 안전한 접근을 위해 방화벽 규칙 체인을 갱신합니다.
```bash
sudo ufw allow 9999
sudo ufw enable
sudo ufw status
```

-----

## 🚀 향후 로드맵 및 확장 아키텍처 (Roadmap)

본 프로젝트의 유연한 모듈러 설계를 바탕으로 다음과 같이 고도화가 가능합니다:
1. **GPU 텔레메트리 시각화**: Plotly 차트 엔진 기반 실시간 VRAM 점유율, 전력 소모량, 온도를 모니터링하는 대시보드 결합
2. **모델 제어 라이프사이클 UI**: 웹 콘솔 내에서 실시간으로 Ollama 모델 다운로드(Pull), 삭제 및 컨텍스트 파라미터 동적 변경 제어 UI 구축
3. **영속성 데이터 아카이빙**: 내장형 데이터베이스(SQLite 등) 연동을 통한 유저 및 세션별 채팅 히스토리 기록 아카이브 아키텍처
4. **엔터프라이즈 게이트웨이**: 비동기 트래픽 제어 및 중규모 로드밸런싱 처리를 위한 `FastAPI` 기반 API Gateway 레이어 통합
