# 👑 [기획서_390] 황실 콕핏(shinseon_cockpit.pyw) 듀얼 저격 알림(청산액&OI속도 100% 충족) 시 sound/position.mp3 사운드 직결 재생 엔진 탑재 및 콕핏 V1.10 배포 기획서

---

## 1. 개요 및 배경

- **발생 원인 분석:**
  - 국왕 폐하의 콕핏 화면에 `[21:33:07] 🎯 [황실 듀얼 저격 알림] 청산액($1,958,569 >= $600,000) & OI속도(+0.1324% >= +0.1200%) 100% 동시 충족!` 신호가 점등되었음에도 소리가 나지 않았던 원인:
    1. 폐하께서 현재 띄워두신 콕핏 창이 `V1.07` 버전으로, 구형 `winsound.Beep(1200, 200)`(메인보드 비프음)만 장착되어 있어 스피커/헤드폰으로 사운드가 출력되지 않았음.
    2. `sound/position.mp3` 고품질 사운드 엔진이 `check_dual_threshold_sound()`에 직접 연결되어 있지 않았음.
- **개편 목적:**
  - `🎯 [황실 듀얼 저격 알림]` 발생 시 `winsound.Beep` 대신 `sound/position.mp3` 파일을 즉각 백그라운드 스피커로 시원하고 웅장하게 재생하도록 직결 개편.
  - 콕핏 버전을 **`👑 황실 수동 콕핏 V1.10`**으로 상향 배포.

---

## 2. 세부 개발 명세

### 1) `check_dual_threshold_sound()` 내 `play_position_sound()` 직결
- `check_dual_threshold_sound` 함수 내부:
  ```python
  if now - self._last_beep_time >= 60.0:
      self._last_beep_time = now
      self.add_log(f"🎯 [황실 듀얼 저격 알림] 청산액(${int(self.rolling_1m_liq):,} >= ${int(self.target_liq):,}) & OI속도({self.oi_delta_1m:+.4f}% >= {self.target_oi:+.4f}%) 100% 동시 충족!")
      play_position_sound()  # sound/position.mp3 즉시 재생!
  ```

### 2) `play_position_sound()` 재생 안정성 극대화
- `sound/position.mp3` 경로를 최우선 탐색하여 Windows MCI(`mciSendStringW`)로 백그라운드 논블로킹 즉시 재생 및 볼륨 최적화.

### 3) 콕핏 버전 체계 V1.10 갱신
- `VERSION = "V1.10"`, `self.COCKPIT_VERSION = "V1.10"`
- 윈도우 타이틀 및 상단 헤더 라벨: **`👑 황실 수동 콕핏 V1.10`**

---

## 3. 검증 계획
1. `python -m py_compile shinseon_cockpit.pyw` 구문 무결성 검증.
2. `check_dual_threshold_sound()` 격발 시 `position.mp3` 사운드가 정상 호출되는지 단위 테스트 검증.
3. 3초 서브프로세스 기동 테스트 0 Error, 0 Crash 검증.

---

## 4. 작업 상태
- [x] 개발 완료 (2026-08-30 21:43 완공)
- 무결성 검증 통과 (구문 컴파일 100%, 3초 무충돌 기동 통과, 사운드 직결 검증 완료)
