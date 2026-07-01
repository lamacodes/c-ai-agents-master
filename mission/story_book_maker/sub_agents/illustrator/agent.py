from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from .prompt import ILLUSTRATOR_DESCRIPTION, ILLUSTRATOR_PROMPT
from .tools import generate_images


MODEL = LiteLlm(model="openai/gpt-4o-mini")

illustrator_agent = Agent(
    name="IllustratorAgent",
    model=MODEL,
    description=ILLUSTRATOR_DESCRIPTION,
    instruction=ILLUSTRATOR_PROMPT,
    output_key="illustrator_output",
    tools=[generate_images],
)
