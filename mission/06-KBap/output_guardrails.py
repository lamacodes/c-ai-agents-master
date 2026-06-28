from agents import (
    Agent,
    output_guardrail,
    Runner,
    RunContextWrapper,
    GuardrailFunctionOutput,
)
# pyrefly: ignore [missing-import]
from models import OutputGuardRailOutput, UserAccountContext
# pyrefly: ignore [missing-import]
from concept import MODEL

output_guardrail_agent = Agent(
    name="Output Guardrail Agent",
    model=MODEL,
    instructions="""
    당신은 레스토랑 챗봇 응답의 안전성 검사기입니다.
    오직 '진짜 유출/부적절'만 차단하고, 정상적인 고객 응대는 절대 막지 마세요.
    확신이 없으면 모든 필드를 false 로 두세요. (오탐 방지)

    [중요] 현재 응대 중인 고객 '본인'의 정보는 정상입니다 — 절대 true 로 표시하지 마세요:
    - 본인의 예약 확인/안내 (날짜, 시간, 인원, 예약자 이름) → 정상
    - 본인의 주문 확인/안내 (메뉴, 수량, 합계 금액) → 정상
    - 공개 메뉴의 이름, 설명, 판매 가격, 알레르기 정보 → 정상

    아래 '진짜 문제'에 해당할 때만 해당 필드를 true 로 설정하세요:

    - contains_off_topic: 비전문적·무례한 표현, 욕설, 부적절한 언어
    - contains_reservation_data: '다른 고객'의 예약 정보, 또는 내부 시스템 전용
      데이터(전체 예약 명단, 내부 ID 등)를 노출
    - contains_menu_data: 메뉴 '원가', 마진, 공급업체 등 내부 전용 정보를 노출
      (고객에게 안내하는 판매 가격은 정상이므로 false)
    - contains_order_data: '다른 고객'의 주문 내역, 또는 내부 매출/시스템 데이터를 노출

    reason 에는 판단 근거를 한 줄로 적으세요.
    """,
    output_type=OutputGuardRailOutput,
)


@output_guardrail
async def output_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent,
    output: str,
):
    result = await Runner.run(
        output_guardrail_agent,
        output,
        context=wrapper.context,
    )

    validation = result.final_output

    triggered = (
        validation.contains_off_topic
        or validation.contains_reservation_data
        or validation.contains_menu_data
        or validation.contains_order_data
    )

    return GuardrailFunctionOutput(
        output_info=validation,
        tripwire_triggered=triggered,
    )