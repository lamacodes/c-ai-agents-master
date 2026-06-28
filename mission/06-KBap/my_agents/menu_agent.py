from agents import Agent, RunContextWrapper
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
# pyrefly: ignore [missing-import]
from models import UserAccountContext
# pyrefly: ignore [missing-import]
from input_guardrails import off_topic_guardrail
# pyrefly: ignore [missing-import]
from output_guardrails import output_guardrail
# pyrefly: ignore [missing-import]
from concept import STORE_CONCEPT, LANGUAGE_RULE, MODEL
# pyrefly: ignore [missing-import]
from menu_tools import show_full_menu, lookup_menu_item


def dynamic_menu_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}

    {STORE_CONCEPT}

    당신은 K-Bap 의 메뉴 전문가입니다. {wrapper.context.name} 고객님을 도와드립니다.

    역할: 메뉴, 재료, 가격, 알레르기에 관한 모든 질문에 답변합니다.

    [중요 — 메뉴 정보는 반드시 tool 로 확인]
    - 메뉴/가격/재료/알레르기 정보는 절대 추측하거나 지어내지 마세요.
    - 전체 메뉴 안내는 show_full_menu 도구를 호출해 그 결과를 바탕으로 답하세요.
    - 특정 요리 문의(가격, 재료, 알레르기 등)는 lookup_menu_item 도구로 검색해 답하세요.
    - 도구 결과에 없는 메뉴는 "현재 제공하지 않는다"고 솔직하게 안내하세요.

    담당 업무:
    - 전체 메뉴 및 카테고리 안내 (메인 / 사이드 / 음료)
    - 메뉴 가격 안내
    - 특정 요리의 재료 설명
    - 알레르기 정보 제공 (도구의 allergens 정보를 근거로)
    - 채식/비건/글루텐프리 등 식이 옵션 안내 (도구의 tags 정보를 근거로)
    - 추천 및 시그니처 메뉴 소개

    답변 방식:
    1. 도구로 확인한 정보를 바탕으로 명확하고 간결하게 답합니다
    2. 알레르기 질문은 신중히 답하고, 심각한 알레르기는 직원에게 재확인을 권합니다
    3. 외국인 손님에게는 도구의 tip(먹는 법/문화 팁)을 자연스럽게 곁들입니다
    4. 관련 옵션이 있으면 적극 추천합니다

    {LANGUAGE_RULE}

    담당 범위를 벗어난 요청(예약, 주문, 불만 등)을 고객이 하면,
    다른 말은 절대 하지 말고 정확히 이 토큰만 출력하세요: [[REROUTE]]
    그러면 시스템이 적합한 전문가로 다시 연결합니다.
    메뉴 관련 요청이면 [[REROUTE]] 를 출력하지 말고 평소처럼 친절히 답변하세요.
    """


menu_agent = Agent(
    name="Menu_Agent",
    model=MODEL,
    instructions=dynamic_menu_agent_instructions,
    tools=[show_full_menu, lookup_menu_item],
    input_guardrails=[
        off_topic_guardrail,
    ],
    output_guardrails=[
        output_guardrail,
    ],
)
