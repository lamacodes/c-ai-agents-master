from agents import (
    Agent,
    output_guardrail,
    Runner,
    RunContextWrapper,
    GuardrailFunctionOutput,
)
# pyrefly: ignore [missing-import]
from models import OutputGuardRailOutput, UserAccountContext

output_guardrail_agent = Agent(
    name="Output Guardrail Agent",
    instructions="""
    레스토랑 챗봇의 응답이 부적절하게 다음 내용을 포함하는지 분석하세요:

    - 비전문적이거나 무례한 표현, 욕설, 부적절한 언어 (contains_off_topic)
    - 다른 고객의 예약 정보 등 내부 예약 데이터 (contains_reservation_data)
    - 메뉴 원가, 공급업체 정보 등 내부 메뉴 데이터 (contains_menu_data)
    - 다른 고객의 주문 내역 등 내부 주문 데이터 (contains_order_data)

    해당 내용이 포함된 필드는 true를 반환하세요.
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