import base64
from google.genai import types
from openai import AsyncOpenAI
from google.adk.tools.tool_context import ToolContext

client = AsyncOpenAI()

NEGATIVE_PROMPT = (
    "No text, no words, no letters, no captions, no labels, no writing, "
    "no signage in the image. Pure illustration only."
)


def build_consistency_prefix(art_style: str, character_bible: list) -> str:
    """모든 페이지 이미지에 동일하게 적용할 '화풍 + 캐릭터 고정 외형' 프리픽스를 만든다.

    StoryWriter가 페이지마다 외형을 다르게 묘사하더라도, 이 프리픽스가 매번 동일하게
    붙음으로써 캐릭터의 종류/외형이 페이지 간에 변하는 현상을 줄인다.
    """
    parts = []

    if art_style:
        parts.append(
            f"Art style (apply to the entire image, keep identical across all pages): {art_style}."
        )

    if character_bible:
        char_lines = []
        for char in character_bible:
            name = (char.get("name") or "").strip()
            appearance = (char.get("appearance") or "").strip()
            if name and appearance:
                char_lines.append(f"- {name}: {appearance}")
        if char_lines:
            parts.append(
                "Characters (whenever a named character appears, use EXACTLY this appearance; "
                "do not change species, color, or outfit between pages):\n"
                + "\n".join(char_lines)
            )

    return " ".join(parts)


def make_generate_page_image_tool(page_number: int):
    """특정 페이지 번호에 고정된 이미지 생성 tool을 만든다.

    page_number를 클로저로 고정해 LLM이 페이지 번호를 잘못 지정할 위험을 없앤다
    (tool_context 외에는 LLM이 채워야 할 인자가 없다).
    """

    async def generate_page_image(tool_context: ToolContext):
        story_writer_output = tool_context.state.get("story_writer_output")
        if not story_writer_output:
            return {
                "status": "error",
                "error_message": "state에 story_writer_output이 없습니다. 먼저 StoryWriterAgent가 실행되어야 합니다.",
            }

        scene = next(
            (
                s
                for s in story_writer_output.get("scenes", [])
                if s.get("page_number") == page_number
            ),
            None,
        )
        if not scene:
            return {
                "status": "error",
                "error_message": f"story_writer_output에 page_number={page_number} scene이 없습니다.",
            }

        filename = f"page_{page_number}_image.jpeg"

        art_style = story_writer_output.get("art_style", "")
        character_bible = story_writer_output.get("character_bible", [])
        consistency_prefix = build_consistency_prefix(art_style, character_bible)

        image_prompt = scene.get("image_prompt", "")
        full_prompt = f"{consistency_prefix} {image_prompt} {NEGATIVE_PROMPT}".strip()

        image = await client.images.generate(
            model="gpt-image-1",
            prompt=full_prompt,
            n=1,
            quality="low",
            moderation="low",
            output_format="jpeg",
            background="opaque",
            size="1024x1536",
        )

        image_bytes = base64.b64decode(image.data[0].b64_json)

        artifact = types.Part(
            inline_data=types.Blob(
                mime_type="image/jpeg",
                data=image_bytes,
            )
        )

        await tool_context.save_artifact(
            filename=filename,
            artifact=artifact,
        )

        return {
            "status": "complete",
            "page_number": page_number,
            "filename": filename,
        }

    generate_page_image.__name__ = f"generate_page_{page_number}_image"
    return generate_page_image
