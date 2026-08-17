# SHINSEON 오더플로우 판단 백서

## 📌 1. 개요 및 목적 (바이낸스 100% 시세 전권 대전제)
본 문서는 SHINSEON 비트겟 선물 자동저격 트레이딩 시스템에서 가장 어마어마한 수익을 싹쓸이했던 **V2.55 황금 전성기 오더플로우 저격 알고리즘, V6.06 지수가중 추세 기울기(EMA Slope 15s Half-life) 0.5초 반응 엔진, 및 V6.07 롱/숏 청산 주도 비율(Dominant Liq Ratio) 2차 안전 방화벽의 100% 전수 헌법 백서**입니다.

> **🏛️ [헌법 대전제]: 모든 저격 판단/결정(타점 포착, 4대 매트릭스, 1분 지수가중 추세 기울기 `price_slope_1m`, OI 속도 `oi_delta_1m`, 1분 청산액 및 롱/숏 청산 주도 비율)은 오직 100% 바이낸스(Binance) 실시간 시세 및 거래 데이터로만 정해집니다.** 비트겟 가격은 얼마이든 판단에 단 0.001%도 영향을 미치지 않으며, 오직 최종 주문을 체결하는 발주 창구 역할만 수행합니다.

---

## 🛡️ 2. 0단계: 필수 듀얼 임계치 대전제 (AND 조건)
신규 저격 진입 및 포지션 보유 중 반대 청산 감시는 아래 2가지 조건이 **100% 동시에 넘어섰을 때(AND 조건)에만 기어가 동작**합니다. 하나라도 미달 시 진입/청산을 일절 기각(NONE)하고 휴식합니다.

1. **`1분 청산액 >= target_liq`** (세션별 기본: $500,000 이상)
2. **`abs(1분 OI속도) >= target_oi`** (세션별 기본: 0.18% 이상)

---

## 🎯 3. 1단계: 1분 지수가중 기울기(EMA Slope) ✕ OI속도(oi_delta) ✕ 롱/숏 청산 주도 비율 4대 저격 매트릭스 (V6.07)

| 경우의 수 | 1분 지수가중 기울기 (`price_slope_1m`) | 1분 OI속도 (`oi_delta_1m`) | 롱/숏 청산 주도 비율 2차 검증 | 저격 깃발 방향 | 시장 세력 메커니즘 팩트 |
|---|---|---|---|---|---|
| **Case A** | 📉 **`price_slope < 0`** (지속 하락) | 📉 **`oi_delta < 0`** (OI 감소) | **`long_liq >= short_liq`** (롱 청산 주도) | 🟢 **`LONG`** | **개미 롱 손절 털기 팩트 검증 ➡️ 바닥 LONG 저격!** |
| **Case B** | 📈 **`price_slope > 0`** (지속 상승) | 📉 **`oi_delta < 0`** (OI 감소) | **`short_liq >= long_liq`** (숏 청산 주도) | 🔴 **`SHORT`** | **개미 숏스퀴즈 털기 팩트 검증 ➡️ 꼭대기 SHORT 저격!** |
| **Case C** | 📈 **`price_slope > 0`** (지속 상승) | 📈 **`oi_delta > 0`** (OI 증가) | **`short_liq >= long_liq`** (숏 청산 돌파) | 🟢 **`LONG`** | **세력이 숏 청산 먹으며 상승 ➡️ 상승 추세 LONG 탑승!** |
| **Case D** | 📉 **`price_slope < 0`** (지속 하락) | 📈 **`oi_delta > 0`** (OI 증가) | **`long_liq >= short_liq`** (롱 청산 돌파) | 🔴 **`SHORT`** | **세력이 롱 청산 먹으며 하락 ➡️ 하강 추세 SHORT 탑승!** |
| **불일치** | 위 조건 미달 또는 청산 주도 세력 불일치 시 | | | ⚪️ **`NONE`** | **위험 휩쏘/혼조세 100% 기각 ➡️ 안전하게 휴식 (`NONE`)** |

---

## 🚨 4. 2단계: 실전 집행 및 포지션 보유 중 반대 청산 & 쿨타임 스위칭 감시

### ① 포지션 미보유 시 (신규 진입)
- 쿨타임 대기 중(`cooldown_until_time`)이 아닐 때, 4대 매트릭스에서 결정된 깃발(`direction`)대로 **비트겟 선물 시장가 주문을 쏘고, 1초 CSV 장부 파일에도 100% 동일한 방향을 인쇄 기록**합니다.

### ② 포지션 보유 중일 때 (Holding Position)
1. **동일 방향 깃발 수신 시:** 기존 포지션 온전히 홀딩 유지 (추세 탑승). (추가 매수 조건 충족 시 비중 확대)
2. **반대 방향 깃발 수신 시 (`direction != entry_direction`):**
   - **[100% 즉시 청산]:** **OI 부호(+/-)에 관계없이 반대 깃발 수신 즉시 기존 포지션 전량 시장가 청산(`CLEAR`)**을 집행합니다. (v2.55 황금 전성기 헌법)
   - **[쿨타임 대기 🚨]:** 청산 직후 사용자 설정창 지정 **익절/스위칭 쿨타임(기본 15.0초)** 또는 **손절 쿨타임(기본 30.0초)** 동안 `cooldown_until_time`을 엄격히 가동하여 신규 진입을 무조건 철통 차단합니다. (대시보드 UI 설정창에서 자유롭게 동적 조율 가능)
   - **[스위칭 승차]:** 쿨타임이 완벽히 지난 후(`time.time() >= cooldown_until_time`), 유효한 반대 방향 저격 깃발 수신 시 비로소 안전하게 반대 방향 포지션으로 신규 스위칭 탑승합니다.

---

## 📊 5. CSV 레코더 12대 영문 표준 장부 명세 (V6.04)

`Timestamp(KST),BTC_Price($),1m_Rolling_Liq($),1m_Long_Liq($),1m_Short_Liq($),Liq_Threshold($),1m_OI_Speed(%),OI_Speed_Threshold(%),1m_Price_Delta($),1m_Price_Slope,Signal,Bot_State`

1. **`Timestamp(KST)`**: `="YYYY-MM-DD HH:MM:SS"` (엑셀 오픈 즉시 초단위 노출)
2. **`BTC_Price($)`**: 바이낸스 선물 실시간 미드 시세
3. **`1m_Rolling_Liq($)`**: 최근 60초간 바이낸스 청산 누적 합산액 (USD)
4. **`1m_Long_Liq($)`**: 최근 60초간 바이낸스 롱 청산액 (USD)
5. **`1m_Short_Liq($)`**: 최근 60초간 바이낸스 숏 청산액 (USD)
6. **`Liq_Threshold($)`**: 세션별 청산 임계치 ($500,000~)
7. **`1m_OI_Speed(%)`**: 최근 60초간 미결제약정(OI) 변화율 (%)
8. **`OI_Speed_Threshold(%)`**: 세션별 OI 속도 임계치 (0.18%~)
9. **`1m_Price_Delta($)`**: 최근 60.0초(1분 전) 대비 시세 변동폭 ($)
10. **`1m_Price_Slope`**: 최근 60초간 수집된 샘플의 지수가중 선형회귀 추세 기울기 (EMA Slope, 15s Half-life)
11. **`Signal`**: `LONG`, `SHORT`, `NONE`
12. **`Bot_State`**: `RUNNING`, `PAUSED`

---

## 🏛️ 6. 100% 파이썬 실전 구현 원본 소스코드 (V6.07)

```python
# [0단계]: 최근 1분 동안 터진 청산 금액과 OI속도가 우리가 목표한 최소 기준치(임계치)를 넘어섰는지 검사해요!
if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
    
    # --------------------------------------------------------------------------
    # 1단계: 지수가중 기울기(price_slope_1m) ✕ OI속도(oi_delta_1m) ✕ 롱/숏 청산 주도 비율 3중 안전 방화벽!
    # --------------------------------------------------------------------------
    
    # [Case A]: EMA추세 하락(<0), OI 감소(<0), 롱 청산 주도(long_liq >= short_liq) ➡️ 🟢 "LONG" 저점 저격!
    if price_slope_1m < 0 and oi_delta_1m < 0 and long_liq >= short_liq:
        direction = "LONG"
        
    # [Case B]: EMA추세 상승(>0), OI 감소(<0), 숏 청산 주도(short_liq >= long_liq) ➡️ 🔴 "SHORT" 꼭대기 저격!
    elif price_slope_1m > 0 and oi_delta_1m < 0 and short_liq >= long_liq:
        direction = "SHORT"
        
    # [Case C]: EMA추세 상승(>0), OI 증가(>0), 숏 청산 돌파(short_liq >= long_liq) ➡️ 🟢 "LONG" 추세 탑승!
    elif price_slope_1m > 0 and oi_delta_1m > 0 and short_liq >= long_liq:
        direction = "LONG"
        
    # [Case D]: EMA추세 하락(<0), OI 증가(>0), 롱 청산 돌파(long_liq >= short_liq) ➡️ 🔴 "SHORT" 추세 탑승!
    elif price_slope_1m < 0 and oi_delta_1m > 0 and long_liq >= short_liq:
        direction = "SHORT"
        
    else:
        direction = None    # 휩쏘/혼조세/주도비율 불일치 시 100% NONE 안전 기각!
```
