from google.adk.agents import SequentialAgent
from .sub_agents.story_writer.agent import story_writer_agent
from .sub_agents.illustrator.agent import illustrator_parallel_agent
from .callbacks import assemble_storybook_callback

root_agent = SequentialAgent(
    name="StoryBookPipeline",
    description=(
        "사용자가 제시한 테마로 5페이지 동화(StoryWriterAgent)를 작성한 뒤, "
        "5개 페이지의 삽화를 동시에 생성(IllustratorParallelAgent)해 "
        "완성된 동화책을 반환하는 파이프라인입니다."
    ),
    sub_agents=[story_writer_agent, illustrator_parallel_agent],
    after_agent_callback=assemble_storybook_callback,
)
