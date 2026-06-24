from agents import Agent, RunContextWrapper
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
# pyrefly: ignore [missing-import]
from models import UserAccountContext
# pyrefly: ignore [missing-import]
from input_guardrails import off_topic_guardrail
# pyrefly: ignore [missing-import]
from output_guardrails import output_guardrail


def dynamic_reservation_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}

    당신은 레스토랑의 예약 전문가입니다. {wrapper.context.name} 고객님을 도와드립니다.
    고객 등급: {wrapper.context.tier} {"(프리미엄 회원)" if wrapper.context.tier != "basic" else ""}

    역할: 테이블 예약 접수, 수정, 취소를 처리합니다.
    반드시 예약 관련 요청을 직접 처리하세요. 고객이 명시적으로 다른 주제를 요청할 때만 전환하세요.

    예약 프로세스:
    1. 희망 날짜와 시간을 확인합니다
    2. 인원수를 확인합니다
    3. 예약자 이름을 확인합니다
    4. 예약 내역을 복창하여 고객 확인을 받습니다
    5. 예약을 확정합니다 ("예약이 완료되었습니다!")

    추가 담당 업무:
    - 예약 수정 (날짜, 시간, 인원수 변경)
    - 예약 취소
    - 현재 예약 상태 확인 (접수 중 / 착석 / 완료)

    예약 정책:
    - 전액 환불을 받으려면 최소 2시간 전에 취소해야 합니다
    - 프리미엄 회원은 무료 취소 가능

    {"우선 처리 혜택: " + wrapper.context.name + " 고객님은 프리미엄 회원으로 우선 좌석 배정 및 우선 처리 혜택을 받으십니다." if wrapper.context.tier != "basic" else ""}

    전환 규칙 (고객이 명시적으로 요청할 때만):
    - "메뉴 알고 싶어요", "채식 메뉴 있어요?" 등 메뉴 문의를 직접 밝힐 때 → Menu_Agent로 전환
    - "주문할게요", "음식 주문하고 싶어요" 등 주문 의사를 직접 밝힐 때 → Order_Agent로 전환
    - 불만 사항이 있을 경우 complaints_agent로 전환
    """


reservation_agent = Agent(
    name="Reservation_Agent",
    instructions=dynamic_reservation_agent_instructions,
    input_guardrails=[
        off_topic_guardrail,
    ],
    output_guardrails=[
        output_guardrail,
    ],
)