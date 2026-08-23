@echo off
chcp 65001 > nul
title 신선 전략 백테스터 V1.0 (ShinSeon Strategy Backtester)
echo ====================================================
echo  🚀 [SHINSEON] 신선 오더플로우 전문 독립 전략 백테스터 가동 중...
echo ====================================================
start "" pythonw shinseon_backtester.pyw
exit
