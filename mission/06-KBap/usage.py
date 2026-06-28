"""
앱 전역 일일 사용량 카운터 (비용 보호).

st.session_state 기반 제한은 새로고침/새 탭/초기화로 우회되지만,
이 카운터는 '프로세스 전역'(모든 브라우저 세션이 공유)에 저장되므로 우회되지 않는다.
- 모든 세션은 같은 프로세스를 공유하므로 모듈 전역 변수가 공유된다.
- 여러 세션이 동시에 접근하므로 Lock 으로 보호한다.
- 날짜가 바뀌면 자동으로 0 으로 리셋된다.
- 앱이 재시작(재배포/슬립 복귀)되면 0 으로 리셋된다(휘발성). 이는 허용 범위.

이것은 '근사적' 소프트 상한이며, 최종 안전장치는 OpenAI 대시보드의 예산 한도다.
"""

import threading
from datetime import date

_lock = threading.Lock()
_state = {"day": None, "count": 0}


def _reset_if_new_day(today: str):
    if _state["day"] != today:
        _state["day"] = today
        _state["count"] = 0


def try_consume(daily_limit: int) -> bool:
    """한도 내이면 카운트를 1 증가시키고 True, 한도 초과면 증가 없이 False."""
    with _lock:
        today = date.today().isoformat()
        _reset_if_new_day(today)
        if _state["count"] >= daily_limit:
            return False
        _state["count"] += 1
        return True


def current_usage() -> int:
    """오늘 누적 사용량(증가 없이 조회)."""
    with _lock:
        _reset_if_new_day(date.today().isoformat())
        return _state["count"]
