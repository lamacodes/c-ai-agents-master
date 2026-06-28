"""
K-Bap 서비스 공통 콘셉트/규칙. 모든 agent instructions 에서 재사용한다.
"""

# 비용 절감: 모든 에이전트/가드레일이 사용할 모델.
# gpt-4o 대비 호출당 비용이 크게 낮고, 이 봇의 작업에는 품질 차이가 거의 없다.
MODEL = "gpt-4o-mini"

# 비용 보호: 한 세션(브라우저)에서 보낼 수 있는 최대 메시지 수. (부드러운 안내용 — 새로고침으로 우회 가능)
MAX_MESSAGES_PER_SESSION = 30

# 비용 보호: 앱 전체가 하루에 처리할 수 있는 총 메시지 수.
# 프로세스 전역 카운터라 새로고침/새 탭/초기화로 우회되지 않는다(usage.py).
GLOBAL_DAILY_MESSAGE_LIMIT = 500

# 가게 정체성 — 모든 에이전트가 공유하는 페르소나 배경
STORE_CONCEPT = """
[가게 소개]
당신은 'K-Bap'에서 일합니다. K-Bap 은 한국을 찾은 외국인 여행객에게
대표적인 한식을 소개하는 모던 한식 다이닝 레스토랑입니다.
한식이 처음인 손님에게도 친절하게, 먹는 법이나 작은 문화 팁을 곁들여
따뜻하게 안내하세요.
"""

# 가게 표시 정보 (UI 헤더/사이드바)
STORE_EMOJI = "🍚"  # 사이드바 가게 표시 전용
BRAND_ICON = "🥢"   # 페이지 아이콘 + 챗 아바타
STORE_NAME = "K-Bap"
STORE_TAGLINE = "A bowl of Korea · 한 그릇에 담은 한국"

# 에이전트별 표시 정보 (이모지 아바타 + '한글(영어)' 라벨) — UI 에서 사용
AGENT_PROFILES = {
    "Triage_Agent": {"emoji": "🛎️", "label": "안내 (Concierge)"},
    "Menu_Agent": {"emoji": "🍽️", "label": "메뉴 (Menu)"},
    "Order_Agent": {"emoji": "🧾", "label": "주문 (Order)"},
    "Reservation_Agent": {"emoji": "🗓️", "label": "예약 (Reserve)"},
    "Complaints_Agent": {"emoji": "🤝", "label": "케어 (Care)"},
}


def agent_profile(name):
    """에이전트 이름 → 표시 정보. 미등록 이름은 브랜드 기본값으로."""
    return AGENT_PROFILES.get(name, {"emoji": BRAND_ICON, "label": name})


# 첫 화면 환영 문구 (대화 기록이 비어 있을 때 표시)
WELCOME_TITLE = "안녕하세요! 밥 아저씨예요 🥢"
WELCOME_BODY = (
    "K-Bap 의 메뉴 추천, 주문, 예약, 그 외 문의까지 도와드려요.\n\n"
    "Welcome to K-Bap! Ask me anything about our menu, orders, or reservations."
)

# 고객이 무엇을 말해야 할지 막막하지 않도록 보여주는 예시 (클릭하면 바로 전송)
EXAMPLE_PROMPTS = [
    "메뉴 추천해줘",
    "비건 메뉴 있어?",
    "오늘 저녁 7시 2명 예약하고 싶어",
]


# 응답 언어 규칙 — instructions 는 한국어지만 답변은 고객 언어에 맞춘다
LANGUAGE_RULE = """
[응답 언어 규칙]
- 고객이 사용한 언어로 답변하세요. (영어로 물으면 영어로, 한국어로 물으면 한국어로)
- 메뉴 이름, 재료, 알레르기 등 모든 고유 명칭은 '한글(영어)' 순서로 함께 표기하세요.
  예: 비빔밥 (Bibimbap), 막걸리 (Makgeolli), 계란 (egg), 대두 (soy)
- 가격은 원화로 표기하세요. 예: ₩14,000
"""
