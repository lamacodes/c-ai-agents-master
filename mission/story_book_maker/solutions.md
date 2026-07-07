Assignment 16: Complete Story Book Maker (SequentialAgent + ParallelAgent + Callbacks)
Project structure:

story_book_maker/
    __init__.py
    agent.py
    .env
story_book_maker/__init__.py
from .agent import root_agent
story_book_maker/agent.py
from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from openai import OpenAI
import base64

client = OpenAI()

# Story Writer Output Schema

class PageOutput(BaseModel):
    page_number: int = Field(description="Page number")
    text: str = Field(description="The story text for this page")
    visual_description: str = Field(
        description="Detailed visual description for illustration"
    )

class StoryOutput(BaseModel):
    title: str = Field(description="The title of the story")
    pages: List[PageOutput] = Field(description="List of 5 story pages")

# Callbacks for progress tracking

def on_story_start(callback_context: CallbackContext) -> Optional[types.Content]:
    print("📝 Writing story...")
    return None

def on_story_done(callback_context: CallbackContext) -> Optional[types.Content]:
    story = callback_context.state.to_dict().get("story_output", {})
    title = story.get("title", "Untitled")
    print(f"✅ Story written: {title}")
    return None

def on_illustrations_start(callback_context: CallbackContext) -> Optional[types.Content]:
    print("🎨 Generating all illustrations in parallel...")
    return None

def on_illustrations_done(callback_context: CallbackContext) -> Optional[types.Content]:
    print("✅ All illustrations complete!")
    return None

# Story Writer Agent

story_writer_agent = Agent(
    name="StoryWriterAgent",
    model="gemini-2.0-flash",
    description="Writes a 5-page children's story based on a given theme",
    instruction="""You are a children's story writer. Given a theme, write a charming 5-page story for kids aged 4-8.

    For each page provide:
    - page_number: 1 through 5
    - text: 1-2 sentences of simple, engaging story text
    - visual_description: A detailed description of what the illustration should show (characters, setting, colors, mood)

    Guidelines:
    - Use simple, age-appropriate language
    - Make the story fun and heartwarming
    - Each page should advance the story
    - Visual descriptions should be vivid and specific for image generation
    - Include a satisfying ending on page 5
    """,
    output_schema=StoryOutput,
    output_key="story_output",
    before_agent_callback=on_story_start,
    after_agent_callback=on_story_done,
)

# Tool for generating a single page illustration

async def generate_page_image(tool_context: ToolContext, page_number: int):
    """Generate an illustration for a specific page of the story

    Args:
        tool_context: Tool context for accessing state and artifacts
        page_number: Which page to illustrate (1-5)
    """
    story_output = tool_context.state.get("story_output")
    pages = story_output.get("pages", [])

    page = None
    for p in pages:
        if p.get("page_number") == page_number:
            page = p
            break

    if not page:
        return {"status": "error", "message": f"Page {page_number} not found"}

    filename = f"page_{page_number}.png"
    existing = await tool_context.list_artifacts()
    if filename in existing:
        return {"status": "cached", "page_number": page_number, "filename": filename}

    print(f"  🖼️ Generating image {page_number}/5...")

    prompt = (
        f"Children's book illustration, colorful, whimsical, friendly style: "
        f"{page.get('visual_description')}. "
        f"Digital art, soft colors, suitable for children aged 4-8."
    )

    image = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        n=1,
        size="1024x1024",
        quality="low",
    )

    image_bytes = base64.b64decode(image.data[0].b64_json)

    artifact = types.Part(
        inline_data=types.Blob(mime_type="image/png", data=image_bytes)
    )

    await tool_context.save_artifact(filename=filename, artifact=artifact)

    return {"status": "complete", "page_number": page_number, "filename": filename}

# Create 5 illustrator agents (one per page) for parallel execution

def make_page_illustrator(page_num: int) -> Agent:
    return Agent(
        name=f"PageIllustrator_{page_num}",
        model="gemini-2.0-flash",
        description=f"Generates the illustration for page {page_num}",
        instruction=f"Use the generate_page_image tool with page_number={page_num} to create the illustration for page {page_num}.",
        tools=[generate_page_image],
    )

# Parallel agent runs all 5 illustrators simultaneously

parallel_illustrator = ParallelAgent(
    name="ParallelIllustrator",
    description="Generates all 5 illustrations simultaneously",
    sub_agents=[make_page_illustrator(i) for i in range(1, 6)],
    before_agent_callback=on_illustrations_start,
    after_agent_callback=on_illustrations_done,
)

# Full pipeline: Write story, then generate all illustrations in parallel

root_agent = SequentialAgent(
    name="StoryBookPipeline",
    description="Creates a complete children's story book with text and illustrations",
    sub_agents=[story_writer_agent, parallel_illustrator],
)
