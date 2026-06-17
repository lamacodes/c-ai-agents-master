"""
* Life Coach가 목표와 일기 항목을 기억할 수 있도록 **파일 검색** 기능을 추가하세요!
* Life Coach에 추가해야 할 기능:
  > 1. 개인 목표 문서를 업로드하고 검색
  > 2. 조언 시 과거 기록을 참조
  > 3. 시간에 따른 진행 상황 추적

### 요구사항

* 개인 목표가 담긴 문서(PDF 또는 TXT)를 작성하세요.
* 에이전트에 파일 검색 도구를 추가하세요.
* 코치가 업로드된 목표를 참조하여 조언하도록 하세요.
* 웹 검색과 결합하여 개인화된 추천을 제공하세요.

### 예시 상호작용

```
User: 내 운동 목표 달성은 잘 되어가고 있어?
Coach: [목표 문서 검색]
Coach: 목표에 따르면 주 3회 운동을 계획하셨네요. 관련 팁을 검색해 볼게요...
Coach: [웹 검색: "운동 루틴 유지하는 방법"]
Coach: 목표와 최신 연구 결과를 바탕으로 제안드리자면...
```

"""

import dotenv
dotenv.load_dotenv()

import os
from dotenv import set_key
from openai import OpenAI
import asyncio
import base64
import streamlit as st
from agents import Agent, Runner, SQLiteSession, WebSearchTool, FileSearchTool

client = OpenAI()

_ENV_FILE = os.path.join(os.path.dirname(__file__), "../../.env")


def get_or_create_vector_store() -> str:
    vs_id = os.environ.get("VECTOR_STORE_ID", "")
    if vs_id:
        try:
            client.vector_stores.retrieve(vs_id)
            return vs_id
        except Exception:
            pass
    vs = client.vector_stores.create(name="life-coach-files")
    set_key(_ENV_FILE, "VECTOR_STORE_ID", vs.id)
    os.environ["VECTOR_STORE_ID"] = vs.id
    return vs.id


if "vector_store_id" not in st.session_state:
    st.session_state["vector_store_id"] = get_or_create_vector_store()
VECTOR_STORE_ID = st.session_state["vector_store_id"]


if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="Life_Coach",
        instructions="""
        너는 따뜻하고 열정적인 Life Coach AI야. 사용자를 격려하고 응원해줘.

        - File Search Tool: 사용자가 자신과 관련된 사실이나 특정 파일에 대해 질문할 때 사용해.
        - Web Search Tool: 사용자가 조언, 고민, 습관, 목표, 자기계발에 대해 이야기하면 반드시 WebSearchTool로 검색한 후 답변해.
        """,
        tools=[
            WebSearchTool(),
            FileSearchTool(
                vector_store_ids=[VECTOR_STORE_ID],
                max_num_results=3,
            ),
        ],
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
                    content = message["content"]                    
                    if isinstance(content, str):
                        st.write(content)
                    elif isinstance(content, list):
                        for part in content:
                            if "image_url" in part:
                                st.image(part["image_url"])

                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"].replace("$", "\$"))
        if "type" in message:
            # 웹 검색을 하는 경우
            if message["type"] == "web_search_call":
                query = message.get("action", {}).get("query", "")
                with st.chat_message("ai"):
                    st.write(f'[웹 검색: "{query}"]')

            # 파일을 검색하는 경우
            elif message["type"] == "file_search_call":
                with st.chat_message("ai"):
                    st.write("🗂️ Searched your files...")                    

asyncio.run(paint_history())

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
        "response.file_search_call.completed": (
            "✅ File search completed.",
            "complete",
        ),
        "response.file_search_call.in_progress": (
            "🗂️ Starting file search...",
            "running",
        ),
        "response.file_search_call.searching": (
            "🗂️ File search in progress...",
            "running",
        ),
        "response.completed": (" ", "complete"),
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)


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
                    text_placeholder.write(response.replace("$", "\$"))


prompt = st.chat_input(
    "Write a message for your assistant",
    accept_file=True,
    file_type=[
        "txt",
        "jpg",
        "jpeg",
        "png",
    ],
)

if prompt:

    for file in prompt.files:
        if file.type.startswith("text/"):
            with st.chat_message("ai"):
                with st.status("⏳ Uploading file...") as status:
                    uploaded_file = client.files.create(
                        file=(file.name, file.getvalue()),
                        purpose="user_data",
                    )
                    status.update(label="⏳ Attaching file...")
                    client.vector_stores.files.create(
                        vector_store_id=VECTOR_STORE_ID,
                        file_id=uploaded_file.id,
                    )
                    status.update(label="✅ File uploaded", state="complete")
        elif file.type.startswith("image/"):
            with st.status("⏳ Uploading image...") as status:
                file_bytes = file.getvalue()
                base64_data = base64.b64encode(file_bytes).decode("utf-8")
                data_uri = f"data:{file.type};base64,{base64_data}"
                asyncio.run(
                    session.add_items(
                        [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_image",
                                        "detail": "auto",
                                        "image_url": data_uri,
                                    }
                                ],
                            }
                        ]
                    )
                )
                status.update(label="✅ Image uploaded", state="complete")
            with st.chat_message("human"):
                st.image(data_uri)

    if prompt.text:
        with st.chat_message("human"):
            st.write(prompt.text)
        asyncio.run(run_agent(prompt.text))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())

    st.divider()
    st.write("**Vector store files**")
    files = client.vector_stores.files.list(vector_store_id=VECTOR_STORE_ID).data
    for f in files:
        if st.button(f"🗑️  {f.id}", key=f"del-{f.id}"):
            client.vector_stores.files.delete(vector_store_id=VECTOR_STORE_ID, file_id=f.id)
            client.files.delete(file_id=f.id)  # 파일 자체도 삭제
            st.rerun()

    st.write(asyncio.run(session.get_items()))