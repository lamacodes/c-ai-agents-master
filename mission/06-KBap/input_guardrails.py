from agents import (
    Agent,
    input_guardrail,
    Runner,
    RunContextWrapper,
    GuardrailFunctionOutput,
)
# pyrefly: ignore [missing-import]
from models import InputGuardRailOutput, UserAccountContext
# pyrefly: ignore [missing-import]
from concept import MODEL


input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    model=MODEL,
    instructions="""
    당신은 레스토랑 챗봇의 입력 필터입니다. 오직 분류만 하세요. 절대 질문에 답하지 마세요.

    오직 다음 두 경우에만 is_off_topic = true를 반환하세요:
    1. 레스토랑(음식, 서비스, 예약, 주문)과 완전히 무관한 주제 (철학, 인생, 날씨, 정치, 코딩, 스포츠 등)
    2. 레스토랑 경험과 전혀 관계없는 순수 욕설이나 혐오 표현

    그 외 모든 경우는 is_off_topic = false를 반환하세요.
    특히 음식·서비스·직원에 대한 불만은 아무리 부정적인 표현이어도 반드시 false입니다.

    예시:
    "인생이란 뭘까?" → true
    "날씨 어때?" → true
    "코딩 도와줘" → true
    "씨발" → true
    "음식이 맛없었어요" → false
    "직원이 불친절했어요" → false
    "음식이 너무 별로였고 직원도 불친절했어" → false
    "주문하고 싶어요" → false
    "예약 취소해주세요" → false

    reason 필드에 거부 이유를 한국어로 작성하세요.
    """,
    output_type=InputGuardRailOutput,
)



@input_guardrail(run_in_parallel=False)
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
