from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from .prompt import STORY_WRITER_DESCRIPTION, STORY_WRITER_PROMPT
from .models import StoryWriterOutput


MODEL = LiteLlm(model="openai/gpt-4o-mini")

story_writer_agent = Agent(
    name="StoryWriterAgent",
    model=MODEL,
    description=STORY_WRITER_DESCRIPTION,
    instruction=STORY_WRITER_PROMPT,
    output_schema=StoryWriterOutput,
    output_key="story_writer_output",
)

