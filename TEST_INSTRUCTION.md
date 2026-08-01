# 신선 비트겟 (ShinSeon_Bitget) 테스트 지시서 (Phase 1)

**수신**: 세종 (QA 최고 책임자)
**발신**: 안티그래비티 (PM)

## 테스트 개요
쫄다구 코더 에이전트가 1차 기초 뼈대 공사(Playwright 제거 및 Bitget ccxt 초기화 객체 생성)를 마쳤다.
이 단계에서는 실제 API 주문이 들어가지 않으며, **오직 애플리케이션의 정상 부팅 여부 및 문법적 오류(Syntax Error) 탐지**가 주 목적이다.

## 테스트 수행 지침
1. **명령어 실행**: 터미널(Powershell)에서 아래 명령을 실행하여 문법 오류가 없는지 확인하라.
   `python -m py_compile C:\Working\AntiGravity\ShinSeon_Bitget\shinseon_master_app.pyw`
2. **코드 로드 테스트**: 파이썬 인터프리터를 열고 다음 코드를 실행하여 예외가 터지지 않는지 확인하라.
   ```python
   import sys
   sys.path.append(r"C:\Working\AntiGravity\ShinSeon_Bitget")
   try:
       import shinseon_master_app
       print("SUCCESS_LOAD")
   except Exception as e:
       print("ERROR:", e)
   ```
   *(주의: 윈도우 UI(PySide6)가 뜨지 않게 단지 import만 성공하는지 체크할 것)*
3. **Playwright 의존성 확인**: `shinseon_master_app.pyw` 내부의 Playwright 임포트 구문이 정상적으로 무력화(NotImplementedError) 되었는지 확인하라.

## 보고 지침
위 3가지 항목을 테스트한 뒤, 텔레그램을 통해 폐하께 **사극 톤**으로 "1차 기초 뼈대 공사 컴파일 및 부팅 테스트를 완료하였사옵니다. 결과는 ..." 라고 보고하라. 에러가 있다면 상세히 아뢰어야 한다.
