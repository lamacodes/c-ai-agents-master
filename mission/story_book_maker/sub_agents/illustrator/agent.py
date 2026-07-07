from google.adk.agents import Agent, ParallelAgent
from google.adk.models.lite_llm import LiteLlm
from .prompt import build_illustrator_page_description, build_illustrator_page_prompt
from .tools import make_generate_page_image_tool
from ...callbacks import make_progress_callback

MODEL = LiteLlm(model="openai/gpt-4o-mini")

TOTAL_PAGES = 5


def make_illustrator_page_agent(page_number: int) -> Agent:
    return Agent(
        name=f"IllustratorPage{page_number}Agent",
        model=MODEL,
        description=build_illustrator_page_description(page_number),
        instruction=build_illustrator_page_prompt(page_number),
        output_key=f"illustrator_output_page_{page_number}",
        tools=[make_generate_page_image_tool(page_number)],
        before_agent_callback=make_progress_callback(
            f"🎨 이미지 {page_number}/{TOTAL_PAGES} 생성 중..."
        ),
    )


illustrator_parallel_agent = ParallelAgent(
    name="IllustratorParallelAgent",
    description=(
        f"{TOTAL_PAGES}개의 IllustratorPageAgent를 동시에 실행해 모든 페이지의 삽화를 "
        "병렬로 생성합니다."
    ),
    sub_agents=[
        make_illustrator_page_agent(page_number)
        for page_number in range(1, TOTAL_PAGES + 1)
    ],
)
