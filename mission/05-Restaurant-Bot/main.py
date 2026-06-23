"""
다음 에이전트를 갖춘 Restaurant Bot을 구축하세요:
Triage Agent - 고객이 무엇을 원하는지 파악
Menu Agent - 메뉴, 재료, 알레르기 관련 질문에 답변
Order Agent - 주문을 받고 확인
Reservation Agent - 테이블 예약 처리

요구사항
OpenAI Agents SDK의 handoff 기능을 사용하세요.
Triage 에이전트가 요청에 맞는 전문 에이전트로 라우팅해야 합니다.
각 에이전트는 역할에 맞는 명확한 지시사항을 가져야 합니다.
UI에 handoff가 일어나는 것을 표시하세요 ("메뉴 전문가에게 연결합니다...").

예시 상호작용
User: 예약을 하고 싶어
Triage: 예약 담당에게 연결해 드릴게요...
[Reservation Agent로 handoff]
Reservation: 예약을 도와드리겠습니다! 인원수와 희망 날짜를 알려주세요.

User: 아, 그전에 채식 메뉴 있는지 알려줘
[Menu Agent로 handoff]
Menu: 네! 여러 가지 채식 메뉴가 있습니다...

"""

import dotenv

dotenv.load_dotenv()
from openai import OpenAI
import asyncio
import streamlit as st
from agents import Runner, SQLiteSession, InputGuardrailTripwireTriggered

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
            st.write("I can't help you with that.")                        

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