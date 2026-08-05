# ShinSeon_Bitget 기획서 #21: 바이낸스 1분 청산 실시간 상태 동적 연동 구현

## 1. 개요 및 현상
- **현상**: 대시보드의 `[雷達] 실시간 오더플로우 레이더` 상단 타이틀 영역이 `⚪ 바이낸스 1분 청산`으로 무조건 고정 표기되어 있으며, 실시간 바이낸스 선물 청산(forceOrder) 폭발적 수신 시 **`🟢 바이낸스 1분 찐청산`** (녹색 아이콘) 상태나 연결 장애 시 **`🚨 바이낸스 끊김 (재접속 중)`** (적색 점멸 경보) 상태가 실시간으로 표기되지 않는 현상.
- **원인**: 
  1. AWS 서버(`shinseon_server.py`)의 `ui_callback` 및 `run_telemetry_loop`에서 바이낸스 선물 청산 WSS 수신 플래그(`has_real_force`) 및 WSS 연결 상태(`liq_wss_connected`) 데이터를 웹소켓 `ui_update` 패킷에 담아 발송하지 않고 있었음.
  2. 클라이언트(`shinseon_client.pyw`) 수신부에서 수신된 WSS 연결 상태 및 찐청산 플래그를 반영하여 `lbl_radar_title`의 아이콘(`status_icon`), 색상(`status_color`), 메시지(`status_msg`)를 실시간 동적으로 변경해 주는 연동 로직이 누락되어 있었음.

---

## 2. 세부 개발 및 수정 계획

### [서버 측 수정: `shinseon_server.py`]
1. **바이낸스 선물 청산 WSS 감시 상태 데이터 패키징**
   - `run_telemetry_loop`에서 바이낸스 1분 찐청산 여부(`has_real_force = (now_t - self.last_real_forceorder_time) <= 60.0`) 및 WSS 연결 상태(`self.liq_wss_connected`)를 실시간 연산.
   - `ui_callback` 호출 시 `has_real_force` 및 `liq_wss_connected` 키값을 `ui_update` 패킷에 포함하여 브로드캐스트.

### [클라이언트 측 수정: `shinseon_client.pyw`]
1. **웹소켓 `ui_update` 수신부 상태 연동 구현**
   - 수신된 `liq_wss_connected` 및 `has_real_force` 플래그 판정:
     - **WSS 끊김 시 (`not liq_wss_connected`)**: `🚨 바이낸스 끊김 (재접속 중)` (적색 아이콘 및 점멸 효과)
     - **1분 찐청산 포착 시 (`has_real_force`)**: `🟢 바이낸스 1분 찐청산` (민트/녹색 아이콘 `#00FFCC`)
     - **일반 감시 시**: `⚪ 바이낸스 1분 청산` (은백색 아이콘 `#D0D0D0`)
   - `lbl_radar_title`을 `■ [雷達] 실시간 오더플로우 레이더<br><span style='color:{status_color}'>{status_icon} {status_msg}</span> ({current_session})` 형태로 실시간 렌더링 동기화.

---

## 3. 개발 진행 상태
- [x] 개발 완료
