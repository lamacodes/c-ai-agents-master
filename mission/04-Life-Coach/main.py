"""
* 이미지 생성 기능을 추가하여 비전 보드와 동기부여 포스터를 만들 수 있는 **Life Coach Agent**를 완성하세요!
* 최종 Life Coach가 갖춰야 할 기능:
  > 1. **웹 검색** - 조언, 팁, 동기부여 콘텐츠 검색
  > 2. **파일 검색** - 개인 목표 및 일기 참조
  > 3. **이미지 생성** - 비전 보드 및 동기부여 이미지 생성
  >

### 요구사항

* 에이전트에 이미지 생성 도구를 추가하세요.
* 코치가 다음을 생성할 수 있어야 합니다:

  > * 목표 기반 비전 보드
  > * 맞춤 메시지가 담긴 동기부여 포스터
  > * 진행 상황의 시각적 표현
  >
* 세 가지 도구가 자연스럽게 함께 작동해야 합니다.

### 예시 상호작용

```
User: 올해 책 10권 읽기 목표를 달성했어!
Coach: 정말 대단해요! 🎉 축하 이미지를 만들어 드릴게요...
Coach: [이미지 생성: "책 10권 읽기 달성 축하!"]  

User: 2025년 목표로 비전 보드를 만들어 줄 수 있어?
Coach: [목표 문서에서 2025년 계획 검색]
Coach: 목표를 확인했어요: 운동, 한국어 학습, 여행...
Coach: [운동, 언어, 여행 테마가 담긴 비전 보드 이미지 생성]
```

"""

import dotenv
dotenv.load_dotenv()

import os
from dotenv import set_key
from openai import OpenAI
import asyncio
import base64
from pathlib import Path
import streamlit as st
from agents import (
    Agent,
    Runner,
    SQLiteSession,
    WebSearchTool,
    FileSearchTool,
    ImageGenerationTool,
)

client = OpenAI()


_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


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

        너는 다음과 같은 도구(tools)들을 가지고 사용할 수 있어 :
            - File Search Tool: 사용자가 자신과 관련된 사실이나 일기, 개인 목표를 참조하거나 특정 파일에 대해 질문할 때 사용해.
            - Web Search Tool: 사용자가 조언, 고민, 습관, 목표, 자기계발에 대해 이야기하면 WebSearchTool로 검색한 후 답변해.
            - Image Generation Tool: 사용자가 비전 보드, 동기부여 포스터, 진행 상황의 시각적 표현을 원하면 ImageGenerationTool을 사용해.
        """,
        tools=[
            WebSearchTool(),
            FileSearchTool(
                vector_store_ids=[VECTOR_STORE_ID],
                max_num_results=3,
            ),
            ImageGenerationTool(
                tool_config={
                    "type": "image_generation",
                    "quality": "medium",
                    "output_format": "jpeg",
                    "partial_images": 1,
                }
            )
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
            message_type = message["type"]

            # 웹 검색을 하는 경우
            if message_type == "web_search_call":
                query = message.get("action", {}).get("query", "")
                with st.chat_message("ai"):
                    st.write(f'[웹 검색: "{query}"]')

            # 파일을 검색하는 경우
            elif message_type == "file_search_call":
                with st.chat_message("ai"):
                    st.write("🗂️ Searched your files...")
            
            # 이미지를 생성하는 경우
            elif message_type == "image_generation_call":
                image = base64.b64decode(message["result"])
                with st.chat_message("ai"):
                    st.image(image)

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
        "response.image_generation_call.generating": (
            "🎨 Drawing image...",
            "running",
        ),
        "response.image_generation_call.in_progress": (
            "🎨 Drawing image...",
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
        image_placeholder = st.empty()
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

                elif event.data.type == "response.image_generation_call.partial_image":
                    image = base64.b64decode(event.data.partial_image_b64)
                    image_placeholder.image(image)                    

                # elif event.data.type == "response.completed":
                #     image_placeholder.empty()


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