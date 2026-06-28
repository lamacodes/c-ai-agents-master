import streamlit as st
from agents import (
    Agent,
    RunContextWrapper,
    handoff,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters


# pyrefly: ignore [missing-import]
from models import UserAccountContext, HandoffData
# pyrefly: ignore [missing-import]
from my_agents.menu_agent import menu_agent
# pyrefly: ignore [missing-import]
from my_agents.order_agent import order_agent
# pyrefly: ignore [missing-import]
from my_agents.reservation_agent import reservation_agent
# pyrefly: ignore [missing-import]
from my_agents.complaints_agent import complaints_agent
# pyrefly: ignore [missing-import]
from input_guardrails import off_topic_guardrail
# pyrefly: ignore [missing-import]
from output_guardrails import output_guardrail
# pyrefly: ignore [missing-import]
from concept import STORE_CONCEPT, LANGUAGE_RULE, MODEL


def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}

    {STORE_CONCEPT}

    당신은 K-Bap 의 친절한 안내 직원입니다. 고객을 따뜻하게 맞이하고 적합한 전문가에게 연결합니다.
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

    🍽️ 불만 처리 전문가 - 다음 경우 연결:
    - 음식 품질 불만 (맛, 온도, 양, 신선도 등)
    - 서비스 불만 (불친절, 느린 응대, 실수 등)
    - 환경 불만 (청결, 온도, 소음 등)
    - 예약/주문 문제 (누락, 오류, 지연 등)
    - 기타 불만 사항

    연결 프로세스:
    1. 첫 메시지에서 고객 이름으로 인사합니다
    2. 고객의 요청을 파악합니다
    3. 메뉴, 주문, 예약, 불만 처리 중 하나로 분류합니다
    4. 연결 전 간단히 안내합니다 (예: "메뉴 전문가에게 연결해 드릴게요!")
    5. 적합한 전문 에이전트로 연결합니다

    일반 문의 처리 (메뉴/주문/예약/불만 4가지에 속하지 않는 경우):
    - 주차, 영업시간, 위치, 오시는 길, 와이파이, 매장 정책 등 일반 안내는
      전문가에게 연결하지 말고 당신이 직접 간단히 답변하세요.
    - 확실한 정보가 없으면 솔직히 모른다고 안내하고 매장에 확인을 권합니다.
    - 4가지 분야 중 어디에도 명확히 속하지 않으면 함부로 연결하지 말고 직접 응대하세요.

    여러 주제에 걸친 요청은 가장 시급한 것부터 처리하세요.
    요청이 불명확하면 연결 전 짧은 확인 질문을 한 번만 합니다.

    {LANGUAGE_RULE}
    """


def handle_handoff(
    wrapper: RunContextWrapper[UserAccountContext],
    input_data: HandoffData,
):
    # 이 콜백은 사이드바 블록보다 먼저 실행되므로, 여기서 직접 그리면 위치가
    # 사이드바 맨 위로 고정된다. 데이터만 저장하고, 렌더링은 main.py 사이드바에서
    # '현재 담당' 아래에 예쁘게 처리한다.
    st.session_state["last_handoff"] = {
        "to_name": input_data.to_agent_name,
        "issue_type": input_data.issue_type,
        "description": input_data.issue_description,
        "reason": input_data.reason,
    }


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


triage_agent = Agent(
    name="Triage_Agent",
    model=MODEL,
    instructions=dynamic_triage_agent_instructions,
    input_guardrails=[
        off_topic_guardrail,
    ],
    handoffs=[
        make_handoff(menu_agent),
        make_handoff(order_agent),
        make_handoff(reservation_agent),
        make_handoff(complaints_agent),
    ],
    output_guardrails=[
        output_guardrail,
    ],
)


# 전문 에이전트는 잎(leaf) 노드 — 어디로도 handoff 하지 않는다.
# handoff 그래프를 Triage -> 전문가 단방향(DAG)으로 유지하면 순환이 없어
# 무한 handoff 루프(MaxTurnsExceeded)가 구조적으로 불가능하다.
# 주제 전환은 main.py 가 매 턴 시작을 triage 로 리셋하므로, 다음 턴에
# triage 가 대화 기록을 보고 다시 분류한다(세션 메모리로 맥락 유지).
menu_agent.handoffs = []
order_agent.handoffs = []
reservation_agent.handoffs = []
complaints_agent.handoffs = []