import dotenv

import os
import uuid
import asyncio
import streamlit as st
from agents import (
    Runner,
    SQLiteSession,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    MaxTurnsExceeded,
)

# pyrefly: ignore [missing-import]
from models import UserAccountContext

# pyrefly: ignore [missing-import]
from my_agents.triage_agent import triage_agent

# pyrefly: ignore [missing-import]
from concept import (
    STORE_EMOJI,
    BRAND_ICON,
    STORE_NAME,
    STORE_TAGLINE,
    agent_profile,
    WELCOME_TITLE,
    WELCOME_BODY,
    EXAMPLE_PROMPTS,
    MAX_MESSAGES_PER_SESSION,
    GLOBAL_DAILY_MESSAGE_LIMIT,
)

# pyrefly: ignore [missing-import]
import usage  # 앱 전역 일일 사용량 카운터 (새로고침으로 우회 불가)

dotenv.load_dotenv()

# 로컬은 .env 로 키를 읽지만, 배포(Streamlit Cloud)에서는 .env 가 없으므로
# st.secrets 의 OPENAI_API_KEY 를 환경변수로 주입한다.
# (secrets.toml 이 전혀 없으면 st.secrets 접근이 예외를 던질 수 있어 방어적으로 처리)
try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass

# set_page_config 는 다른 모든 st 명령보다 먼저 호출되어야 한다.
st.set_page_config(page_title=f"{STORE_NAME} · Korean Dining", page_icon=BRAND_ICON)

# 헤더 — 밥 아저씨 마스코트 배너 (메인 전용 / 사이드바와 차별화)
BANNER_PATH = os.path.join(os.path.dirname(__file__), "assets", "banner.png")
if os.path.exists(BANNER_PATH):
    st.image(BANNER_PATH, use_container_width=True)
st.title(STORE_NAME)
st.caption(STORE_TAGLINE)

# 멀티유저 격리: 브라우저 세션마다 고유 session_id 를 부여한다.
# (st.session_state 는 유저별로 분리되지만, SQLiteSession 은 같은 DB 를 쓰므로
#  session_id 가 같으면 대화 기록이 섞인다. uuid 로 유저별 행을 분리한다.)
if "session_id" not in st.session_state:
    st.session_state["session_id"] = uuid.uuid4().hex

if "customer_name" not in st.session_state:
    st.session_state["customer_name"] = ""

# 비용 보호: 세션당 메시지 수 카운터
if "msg_count" not in st.session_state:
    st.session_state["msg_count"] = 0

# 고객 컨텍스트 — 이름은 사이드바 입력값에서 가져온다(미입력 시 Guest).
user_account_ctx = UserAccountContext(
    customer_id=1,
    name=st.session_state.get("customer_name") or "Guest",
    tier="basic",
)

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        st.session_state["session_id"],
        "customer-support-memory.db",
    )
session = st.session_state["session"]

if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent


async def paint_history():
    messages = await session.get_items()
    for message in messages:
        if "role" in message:
            role = message["role"]
            # 과거 메시지는 어느 에이전트가 답했는지 기록이 없으므로 브랜드 아바타로 통일
            avatar = None if role == "user" else BRAND_ICON
            with st.chat_message(role, avatar=avatar):
                if role == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"].replace("$", "\$"))


asyncio.run(paint_history())


# 첫 화면(대화 기록이 비어 있을 때) 환영 + 예시 안내.
# 고객이 무엇을 말해야 할지 막막하지 않도록 예시 버튼을 제공한다.
history_empty = len(asyncio.run(session.get_items())) == 0
if history_empty and "pending_prompt" not in st.session_state:
    st.markdown(f"#### {WELCOME_TITLE}")
    st.write(WELCOME_BODY)
    st.caption("예시로 시작해보세요 · Try one of these")
    cols = st.columns(len(EXAMPLE_PROMPTS))
    for col, example in zip(cols, EXAMPLE_PROMPTS):
        if col.button(example, use_container_width=True):
            st.session_state["pending_prompt"] = example
            st.rerun()


# 현재 전문가가 "내 담당이 아니다"라고 알리는 신호.
# 전문가는 leaf(handoff 없음)라 스스로 전환할 수 없으므로, 이 신호를 출력하면
# 코드가 같은 턴에 딱 한 번 triage 로 재라우팅한다. handoff 순환이 없어 무한 루프가 불가능하다.
REROUTE_SIGNAL = "[[REROUTE]]"


async def run_agent(message, allow_reroute=True):
    needs_reroute = False

    with st.chat_message("ai", avatar=BRAND_ICON):
        # 어느 에이전트가 응답 중인지 표시하는 캡션 (핸드오프 시 갱신됨)
        agent_caption = st.empty()
        start_p = agent_profile(st.session_state["agent"].name)
        agent_caption.caption(f"{start_p['emoji']} {start_p['label']} · 응대 중")

        text_placeholder = st.empty()
        response = ""

        st.session_state["text_placeholder"] = text_placeholder

        # 재라우팅 시 이번 실행이 세션에 남긴 항목을 되돌리기 위해 시작 길이를 기록
        items_before = len(await session.get_items())

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
                        # 재라우팅 신호는 어느 패스에서도 사용자에게 노출하지 않는다.
                        # 신호의 접두사인 동안에는 표시를 보류한다.
                        if REROUTE_SIGNAL.startswith(response.strip()):
                            continue
                        text_placeholder.write(response.replace("$", "\$"))

                elif event.type == "agent_updated_stream_event":
                    if st.session_state["agent"].name != event.new_agent.name:
                        st.session_state["agent"] = event.new_agent

                        # 응답 담당 캡션을 새 에이전트로 갱신
                        new_p = agent_profile(event.new_agent.name)
                        agent_caption.caption(
                            f"{new_p['emoji']} {new_p['label']} · 응대 중"
                        )

                        text_placeholder = st.empty()

                        st.session_state["text_placeholder"] = text_placeholder
                        response = ""

        except InputGuardrailTripwireTriggered:
            st.session_state["text_placeholder"].empty()
            st.write(
                "I'm here for everything K-Bap 🥢 — menu, orders, reservations, and dining support.\n\n"
                "K-Bap 관련(메뉴·주문·예약·문의)만 도와드릴 수 있어요."
            )
            return

        except OutputGuardrailTripwireTriggered:
            st.session_state["text_placeholder"].empty()
            st.write("죄송합니다. 해당 응답을 제공할 수 없습니다.")
            return

        # 안전망: 혹시라도 핸드오프가 한 턴 내에서 과도하게 반복되면 크래시 대신 안내.
        except MaxTurnsExceeded:
            st.session_state["text_placeholder"].empty()
            st.write(
                "요청을 적합한 담당자에게 연결하는 데 어려움이 있어요. 조금 더 구체적으로 말씀해 주시겠어요?"
            )
            return

        # 현재 전문가가 담당 밖이라고 신호를 보낸 경우
        if response.strip() == REROUTE_SIGNAL:
            text_placeholder.empty()
            agent_caption.empty()
            # 신호 응답과 이번 사용자 메시지를 세션에서 제거해 대화 기록을 깨끗이 유지
            items_added = len(await session.get_items()) - items_before
            for _ in range(max(0, items_added)):
                await session.pop_item()

            if allow_reroute:
                # 같은 턴에 딱 한 번 triage 로 재라우팅한다.
                needs_reroute = True
            else:
                # 재라우팅 후에도 담당이 없으면(4개 분야 어디에도 속하지 않는 문의 등)
                # 더 반복하지 않고 정중히 안내한다. (triage 가 직접 처리하지 못한 예외 상황)
                st.write(
                    "죄송하지만 그 부분은 제가 직접 도와드리기 어려운 문의예요. "
                    "메뉴, 주문, 예약, 불만 사항이 있으시면 도와드릴게요."
                )

    # 재라우팅: triage 로 시작해 적합한 전문가를 다시 고른다(allow_reroute=False 로 1회만).
    if needs_reroute:
        st.session_state["agent"] = triage_agent
        await run_agent(message, allow_reroute=False)


# message input — 직접 입력 또는 예시 버튼(pending_prompt)
# 비용 보호 2단계:
#  - 세션 한도(부드러운 안내, 초기화로 계속 가능하지만 아래 전역 한도 안에서만)
#  - 전역 일일 한도(서버측, 새로고침/새 탭/초기화로도 우회 불가)
session_reached = st.session_state["msg_count"] >= MAX_MESSAGES_PER_SESSION
global_reached = usage.current_usage() >= GLOBAL_DAILY_MESSAGE_LIMIT
blocked = session_reached or global_reached

typed = st.chat_input(
    "메뉴·주문·예약 무엇이든 물어보세요 · Ask anything about K-Bap",
    disabled=blocked,
)
message = st.session_state.pop("pending_prompt", None) or typed

if global_reached:
    st.error(
        "오늘 앱 전체 사용량 한도에 도달했어요. 잠시 후 다시 시도해 주세요.\n\n"
        "This app has reached its daily usage limit. Please try again later."
    )
elif session_reached:
    st.info(
        f"이 세션의 대화 한도({MAX_MESSAGES_PER_SESSION}건)에 도달했어요. "
        "사이드바에서 초기화하면 계속할 수 있어요.\n\n"
        "Session limit reached. Reset from the sidebar to continue."
    )

if message and not blocked:
    # 전역 카운터를 원자적으로 소비. 막 한도에 닿았다면(동시 접속) 차단.
    if not usage.try_consume(GLOBAL_DAILY_MESSAGE_LIMIT):
        st.error(
            "오늘 앱 전체 사용량 한도에 도달했어요. 잠시 후 다시 시도해 주세요.\n\n"
            "This app has reached its daily usage limit. Please try again later."
        )
    else:
        st.session_state["msg_count"] += 1
        with st.chat_message("human"):
            st.write(message)

        asyncio.run(run_agent(message))

# sidebar
with st.sidebar:
    # 사이드바는 텍스트/이모지 중심 — 메인의 마스코트 배너와 역할을 구분한다.
    st.markdown(f"## {STORE_EMOJI} {STORE_NAME}")
    st.divider()

    # 고객 이름 입력 (멀티유저 — 하드코딩 제거). key 바인딩으로 즉시 반영.
    st.text_input(
        "이름 · Your name",
        key="customer_name",
        placeholder="Guest",
    )
    st.divider()

    # 현재 응답 담당 에이전트 배지
    cur = agent_profile(st.session_state["agent"].name)
    st.markdown("**현재 담당 · Now serving**")
    st.markdown(f"### {cur['emoji']} {cur['label']}")
    st.divider()

    # 최근 연결 내역(handoff) — '현재 담당' 아래에 카드로 표시
    hb = st.session_state.get("last_handoff")
    if hb:
        st.markdown("**📋 최근 연결 · Last handoff**")
        with st.container(border=True):
            if hb.get("issue_type"):
                st.markdown(f"**{hb['issue_type']}**")
            if hb.get("description"):
                st.write(hb["description"])
            if hb.get("reason"):
                st.caption(f"💬 {hb['reason']}")
        st.divider()

    if st.button("🔄 대화 초기화 · Reset", use_container_width=True):
        asyncio.run(session.clear_session())
        st.session_state["agent"] = triage_agent
        st.session_state["msg_count"] = 0
        st.session_state.pop("last_handoff", None)
        st.session_state.pop("pending_prompt", None)
        st.rerun()

    # 개발용: 세션 원본 기록 + 전역 사용량 (기본 접힘)
    with st.expander("🛠 세션 기록 (dev)"):
        st.caption(
            f"전역 사용량 오늘: {usage.current_usage()} / {GLOBAL_DAILY_MESSAGE_LIMIT}"
        )
        st.write(asyncio.run(session.get_items()))
