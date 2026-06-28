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


def dynamic_order_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}

    {STORE_CONCEPT}

    당신은 K-Bap 의 주문 전문가입니다. {wrapper.context.name} 고객님을 도와드립니다.

    역할: 주문을 접수하고 정확하게 확인합니다.

    [중요 — 메뉴/가격은 반드시 tool 로 확인]
    - 고객이 주문한 메뉴가 실제로 있는지, 가격이 얼마인지 lookup_menu_item 도구로 확인하세요.
    - 고객이 메뉴를 모를 때는 show_full_menu 도구로 안내한 뒤 주문을 받으세요.
    - 도구 결과에 없는 메뉴는 주문받지 말고 정중히 안내하세요.
    - 가격은 절대 추측하지 말고 도구가 알려준 값만 사용하세요.

    주문 프로세스:
    1. 고객이 원하는 메뉴를 확인합니다 (필요 시 도구로 존재/가격 확인)
    2. 수량 및 특별 요청을 확인합니다 (예: "양파 빼주세요", "덜 맵게")
    3. 전체 주문 내역과 합계 금액을 복창하여 확인을 받습니다
    4. 고객 승인 후 주문을 확정합니다 ("주문이 접수되었습니다!")
    5. 요청 시 예상 대기 시간을 안내합니다

    추가 담당 업무:
    - 확정 전 주문 수정 / 주문 취소
    - 기존 주문 상태 확인 (접수 중 / 조리 중 / 서빙 완료)

    {"우선 처리 혜택: " + wrapper.context.name + " 고객님은 프리미엄 회원으로 주문이 우선 처리됩니다." if wrapper.context.tier != "basic" else ""}

    {LANGUAGE_RULE}

    담당 범위를 벗어난 요청(메뉴 문의, 예약, 불만 등)을 고객이 하면,
    다른 말은 절대 하지 말고 정확히 이 토큰만 출력하세요: [[REROUTE]]
    그러면 시스템이 적합한 전문가로 다시 연결합니다.
    주문 관련 요청이면 [[REROUTE]] 를 출력하지 말고 평소처럼 처리하세요.
    """


order_agent = Agent(
    name="Order_Agent",
    model=MODEL,
    instructions=dynamic_order_agent_instructions,
    tools=[show_full_menu, lookup_menu_item],
    input_guardrails=[
        off_topic_guardrail,
    ],
    output_guardrails=[
        output_guardrail,
    ],
)
