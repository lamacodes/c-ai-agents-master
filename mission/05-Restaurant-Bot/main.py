"""
Restaurant Bot에 Guardrails와 Complaints Agent를 추가하세요!

다음 기능을 추가하세요:

Input Guardrails - 부적절하거나 주제에 벗어난 메시지 필터링
Output Guardrails - 봇이 부적절한 응답을 하지 않도록 보장
Complaints Agent - 불만족한 고객을 세심하게 처리하고 해결책 제시

요구사항

다음을 거부하는 Input Guardrails를 추가하세요:
주제에 벗어난 질문 (레스토랑과 관련 없는 내용)
부적절한 언어
다음을 보장하는 Output Guardrails를 추가하세요:
전문적이고 정중한 응답
내부 정보를 노출하지 않음
다음과 같은 Complaints Agent를 만드세요:
고객의 불만을 공감하며 인정
해결책 제시 (환불, 할인, 매니저 콜백)
심각한 문제를 적절히 에스컬레이션

예시 상호작용
User: 음식이 너무 별로였고 직원도 불친절했어..
Triage: 정말 죄송합니다. 도움을 드릴 수 있는 담당자에게 연결해 드릴게요...
[Complaints Agent로 handoff]
Complaints: 불쾌한 경험을 드려 진심으로 사과드립니다.
이 상황을 바로잡고 싶은데요 - 다음 방문 시 50% 할인을 제공해 드리거나,
원하시면 매니저가 직접 연락드리도록 하겠습니다. 어떤 방법이 좋으시겠어요?

User: 인생의 의미가 뭘까?
Bot: [input guardrail 작동]
Bot: 저는 레스토랑 관련 질문에 대해서만 도와드리고 있어요. 메뉴를 확인하거나, 예약하거나, 음식을 주문할 수 있어요.

"""

import dotenv

dotenv.load_dotenv()
from openai import OpenAI
import asyncio
import streamlit as st
from agents import Runner, SQLiteSession, InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered

# pyrefly: ignore [missing-import]
from models import UserAccountContext
# pyrefly: ignore [missing-import]
from my_agents.triage_agent import triage_agent


client = OpenAI()

user_account_ctx = UserAccountContext(
    customer_id=1,
    name="jun",
    tier="basic",
)

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history",
        "customer-support-memory.db",
    )
session = st.session_state["session"]

if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent


async def paint_history():
    messages = await session.get_items()
    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"].replace("$", "\$"))


asyncio.run(paint_history())


async def run_agent(message):
    with st.chat_message("ai"):
        text_placeholder = st.empty()
        response = ""

        st.session_state["text_placeholder"] = text_placeholder

        try:

            stream = Runner.run_streamed(
                st.session_state["agent"],
                message,
                session=session,
                context=user_account_ctx,
            )

            async for event in stream.stream_events():
                if event.type == "raw_response_event":

                    if event.data.type == "response.output_text.delta":
                        response += event.data.delta
                        text_placeholder.write(response.replace("$", "\$"))

                elif event.type == "agent_updated_stream_event":

                    if st.session_state["agent"].name != event.new_agent.name:
                        
                        st.write(f"🤖 Transfered from {st.session_state["agent"].name} to {event.new_agent.name}")

                        st.session_state["agent"] = event.new_agent

                        text_placeholder = st.empty()

                        st.session_state["text_placeholder"] = text_placeholder
                        response = ""

        except InputGuardrailTripwireTriggered:
            st.session_state["text_placeholder"].empty()
            st.write("죄송하지만 저는 레스토랑 관련 질문에 대해서만 도와드릴 수 있어요. 메뉴를 확인하거나, 예약하거나, 음식을 주문할 수 있어요.")

        except OutputGuardrailTripwireTriggered:
            st.session_state["text_placeholder"].empty()
            st.write("죄송합니다. 해당 응답을 제공할 수 없습니다.")


# message input
message = st.chat_input(
    "Write a message for your assistant"
)


if message:

    with st.chat_message("human"):
        st.write(message)

    asyncio.run(run_agent(message))

# sidebar
with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))