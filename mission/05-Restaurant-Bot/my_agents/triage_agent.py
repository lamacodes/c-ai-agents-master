import streamlit as st
from agents import (
    Agent,
    RunContextWrapper,
    input_guardrail,
    Runner,
    GuardrailFunctionOutput,
    handoff,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters


# pyrefly: ignore [missing-import]
from models import UserAccountContext, InputGuardRailOutput, HandoffData
# pyrefly: ignore [missing-import]
from my_agents.menu_agent import menu_agent
# pyrefly: ignore [missing-import]
from my_agents.order_agent import order_agent
# pyrefly: ignore [missing-import]
from my_agents.reservation_agent import reservation_agent



input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    instructions="""
    당신은 레스토랑 챗봇의 가드레일입니다.
    다음과 관련된 요청은 허용합니다: 메뉴 질문, 재료, 알레르기, 음식 주문, 테이블 예약.
    인사나 가벼운 대화도 허용합니다.
    완전히 주제를 벗어난 요청(예: 날씨, 정치, 코딩 도움 등)은 off-topic으로 표시하고 이유를 제공하세요.
""",
    output_type=InputGuardRailOutput,
)


@input_guardrail
async def off_topic_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
    input: str,
):
    result = await Runner.run(
        input_guardrail_agent,
        input,
        context=wrapper.context,
    )

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_off_topic,
    )


def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}

    당신은 친절한 레스토랑 안내 직원입니다. 고객을 따뜻하게 맞이하고 적합한 전문가에게 연결합니다.
    항상 고객의 이름으로 불러주세요.

    고객 이름: {wrapper.context.name}
    고객 등급: {wrapper.context.tier}

    주요 역할: 고객의 요청을 파악하고 적합한 전문 에이전트로 연결합니다.

    라우팅 가이드:

    🍽️ 메뉴 전문가 - 다음 경우 연결:
    - 메뉴 항목이나 요리에 대한 질문
    - 재료 질문 (예: "파스타에 뭐가 들어가나요?")
    - 알레르기 또는 식이 질문 (예: "채식 메뉴 있나요?", "글루텐프리 옵션 있어요?")
    - 채식/비건 옵션
    - 메뉴 가격

    🛒 주문 전문가 - 다음 경우 연결:
    - 새 음식 주문
    - 주문 수정 또는 취소
    - 주문 상태 확인 (예: "음식 나왔나요?")
    - 주문 특별 요청

    📅 예약 전문가 - 다음 경우 연결:
    - 테이블 예약
    - 예약 수정 또는 취소
    - 날짜/인원수 가용 여부 확인

    연결 프로세스:
    1. 첫 메시지에서 고객 이름으로 인사합니다
    2. 고객의 요청을 파악합니다
    3. 메뉴, 주문, 예약 중 하나로 분류합니다
    4. 연결 전 간단히 안내합니다 (예: "메뉴 전문가에게 연결해 드릴게요!")
    5. 적합한 전문 에이전트로 연결합니다

    여러 주제에 걸친 요청은 가장 시급한 것부터 처리하세요.
    요청이 불명확하면 연결 전 짧은 확인 질문을 한 번만 합니다.
    """


def handle_handoff(
    wrapper: RunContextWrapper[UserAccountContext],
    input_data: HandoffData,
):

    with st.sidebar:
        st.write(
            f"""
            Handing off to {input_data.to_agent_name}
            Reason: {input_data.reason}
            Issue Type: {input_data.issue_type}
            Description: {input_data.issue_description}
        """
        )


def make_handoff(agent):
    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=HandoffData,
        input_filter=handoff_filters.remove_all_tools,
    )


def make_simple_handoff(agent):
    return handoff(
        agent=agent,
        input_filter=handoff_filters.remove_all_tools,
    )


# 전문 에이전트 간 직접 전환 
menu_agent.handoffs = [make_simple_handoff(order_agent), make_simple_handoff(reservation_agent)]
order_agent.handoffs = [make_simple_handoff(menu_agent), make_simple_handoff(reservation_agent)]
reservation_agent.handoffs = [make_simple_handoff(menu_agent), make_simple_handoff(order_agent)]

triage_agent = Agent(
    name="Triage_Agent",
    instructions=dynamic_triage_agent_instructions,
    input_guardrails=[
        off_topic_guardrail,
    ],
    handoffs=[
        make_handoff(menu_agent),
        make_handoff(order_agent),
        make_handoff(reservation_agent),
    ],
)