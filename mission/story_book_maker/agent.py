from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm
from .sub_agents.story_writer.agent import story_writer_agent
from .sub_agents.illustrator.agent import illustrator_agent
from .prompt import STORYBOOK_MAKER_DESCRIPTION, STORYBOOK_MAKER_PROMPT

MODEL = LiteLlm(model="openai/gpt-4o-mini")

storybook_maker_agent = Agent(
    name="StoryBookMakerAgent",
    model=MODEL,
    description=STORYBOOK_MAKER_DESCRIPTION,
    instruction=STORYBOOK_MAKER_PROMPT,
    tools=[
        AgentTool(agent=story_writer_agent),
        AgentTool(agent=illustrator_agent),
    ]
)

root_agent = storybook_maker_agent