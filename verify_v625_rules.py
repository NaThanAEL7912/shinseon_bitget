# -*- coding: utf-8 -*-
import sys

# Test the exact V6.25 signal logic
def evaluate_v625_signal(rolling_1m_liq, target_liq, oi_delta_1m, target_oi, price_slope_1m, long_liq, short_liq):
    direction = None
    if rolling_1m_liq >= target_liq and oi_delta_1m > 0 and oi_delta_1m >= target_oi:
        if price_slope_1m > 0 and short_liq >= long_liq:
            direction = "LONG"
        elif price_slope_1m < 0 and long_liq >= short_liq:
            direction = "SHORT"
        else:
            direction = None
    else:
        direction = None
    return direction

# Unit Tests
test_cases = [
    # 1. Valid +OI Long (Case C)
    {"name": "Valid +OI LONG (Case C)", "liq": 600000, "t_liq": 500000, "oi": 0.20, "t_oi": 0.15, "slope": 0.5, "long_liq": 100000, "short_liq": 500000, "expected": "LONG"},
    # 2. Valid +OI Short (Case D)
    {"name": "Valid +OI SHORT (Case D)", "liq": 600000, "t_liq": 500000, "oi": 0.20, "t_oi": 0.15, "slope": -0.5, "long_liq": 500000, "short_liq": 100000, "expected": "SHORT"},
    # 3. Old -OI Case A (Must be Rejected)
    {"name": "Old -OI Case A (Must be REJECTED)", "liq": 600000, "t_liq": 500000, "oi": -0.20, "t_oi": 0.15, "slope": -0.5, "long_liq": 500000, "short_liq": 100000, "expected": None},
    # 4. Old -OI Case B (Must be Rejected)
    {"name": "Old -OI Case B (Must be REJECTED)", "liq": 600000, "t_liq": 500000, "oi": -0.20, "t_oi": 0.15, "slope": 0.5, "long_liq": 100000, "short_liq": 500000, "expected": None},
    # 5. Below OI Threshold (Must be Rejected)
    {"name": "Below OI Threshold (Must be REJECTED)", "liq": 600000, "t_liq": 500000, "oi": 0.10, "t_oi": 0.15, "slope": 0.5, "long_liq": 100000, "short_liq": 500000, "expected": None},
    # 6. Below Liq Threshold (Must be Rejected)
    {"name": "Below Liq Threshold (Must be REJECTED)", "liq": 300000, "t_liq": 500000, "oi": 0.20, "t_oi": 0.15, "slope": 0.5, "long_liq": 100000, "short_liq": 200000, "expected": None},
]

all_passed = True
print("=== [V6.25 오더플로우 순수 +OI 단일 헌법 단위 검증 테스트] ===")
for tc in test_cases:
    res = evaluate_v625_signal(tc["liq"], tc["t_liq"], tc["oi"], tc["t_oi"], tc["slope"], tc["long_liq"], tc["short_liq"])
    passed = (res == tc["expected"])
    if not passed: all_passed = False
    print(f"[{'PASS' if passed else 'FAIL'}] {tc['name']}: Result={res} (Expected={tc['expected']})")

if all_passed:
    print("\n🎉 모든 단위 테스트 100% 전수 통과! (ALL 6 TESTS PASSED)")
else:
    print("\n❌ 일부 테스트 실패!")
    sys.exit(1)
