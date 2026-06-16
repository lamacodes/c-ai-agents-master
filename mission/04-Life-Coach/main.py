"""
Streamlit UI와 웹 검색 기능을 갖춘 Life Coach Agent의 기초를 구축하세요!

Life Coach가 갖춰야 할 기능:
- Streamlit으로 구축된 채팅 인터페이스
- OpenAI Agents SDK 사용 (Agent + Runner)
- 동기부여 콘텐츠, 자기 개발 팁, 습관 형성 조언을 검색하는 웹 검색 도구

요구사항
- Streamlit으로 UI를 구현하세요 (st.chat_input, st.chat_message).
- 코치가 대화를 기억하도록 세션 메모리를 구현하세요.
- 에이전트가 관련 조언을 검색할 수 있는 웹 검색 도구를 추가하세요.
- 에이전트는 유저를 격려하는 라이프 코치처럼 행동해야 합니다.

예시 상호작용
User: 아침에 일찍 일어나고 싶은데 자꾸 알람을 끄게 돼
Coach: [웹 검색: "아침에 일찍 일어나는 팁"]
Coach: 좋은 목표네요! 효과가 검증된 방법들을 알려드릴게요: 1. 알람을 침대에서 먼 곳에 두세요...

User: 좋은 습관을 만들려면 어떻게 해야 해?
Coach: [웹 검색: "습관 만들기 기술"]
Coach: 가장 효과적인 방법은 "습관 쌓기(habit stacking)" 기법입니다...

"""

import dotenv
dotenv.load_dotenv()

import asyncio
import streamlit as st
from agents import Agent, Runner, SQLiteSession, WebSearchTool

if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="Life_Coach",
        instructions="""
        너는 따뜻하고 열정적인 Life Coach AI야. 사용자를 격려하고 응원해줘.

        사용자가 조언, 고민, 습관, 목표, 자기계발에 대해 이야기하면 반드시 WebSearchTool로 검색한 후 답변해.
        단순 인사(예: "안녕", "고마워")에만 검색 없이 답변해.
        """,
        tools=[WebSearchTool()],
    )
agent = st.session_state["agent"]

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history",
        "life-coach-memory.db",
    )
session = st.session_state["session"]


async def paint_history():
    messages = await session.get_items()

    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"])
        if "type" in message and message["type"] == "web_search_call":
            query = message.get("action", {}).get("query", "")
            with st.chat_message("ai"):
                st.write(f'[웹 검색: "{query}"]')


def update_status(status_container, event):

    status_messages = {
        "response.web_search_call.completed": ("✅ Web search completed.", "complete"),
        "response.web_search_call.in_progress": (
            "🔍 Starting web search...",
            "running",
        ),
        "response.web_search_call.searching": (
            "🔍 Web search in progress...",
            "running",
        ),
        "response.completed": (" ", "complete"),
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)


asyncio.run(paint_history())



async def run_agent(message):
    with st.chat_message("ai"):
        status_container = st.status("⏳", expanded=False)
        search_placeholder = st.empty()
        text_placeholder = st.empty()
        response = ""

        stream = Runner.run_streamed(
            agent,
            message,
            session=session,
        )

        async for event in stream.stream_events():
            if event.type == "raw_response_event":

                update_status(status_container, event.data.type)

                if event.data.type == "response.output_item.done":
                    item = event.data.item
                    if getattr(item, "type", None) == "web_search_call":
                        query = item.action.query
                        search_placeholder.write(f'[웹 검색: "{query}"]')

                elif event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response)


prompt = st.chat_input("Write a message for your assistant")

if prompt:
    with st.chat_message("human"):
        st.write(prompt)
    asyncio.run(run_agent(prompt))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))