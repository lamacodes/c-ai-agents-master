import base64
from google.genai import types
from openai import OpenAI
from google.adk.tools.tool_context import ToolContext

client = OpenAI()


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


async def generate_images(tool_context: ToolContext):

    story_writer_output = tool_context.state.get("story_writer_output")
    if not story_writer_output:
        return {
            "status": "error",
            "error_message": "state에 story_writer_output이 없습니다. 먼저 StoryWriterAgent를 실행하세요.",
        }

    scenes = story_writer_output.get("scenes", [])
    art_style = story_writer_output.get("art_style", "")
    character_bible = story_writer_output.get("character_bible", [])

    # 캐릭터 일관성: 모든 페이지에 동일한 화풍/캐릭터 외형을 prefix로 주입
    consistency_prefix = build_consistency_prefix(art_style, character_bible)

    existing_artifacts = await tool_context.list_artifacts()

    generated_images = []

    for scene in scenes:
        page_number = scene.get("page_number")
        image_prompt = scene.get("image_prompt")
        filename = f"page_{page_number}_image.jpeg"

        if filename in existing_artifacts:
            generated_images.append(
                {
                    "page_number": page_number,
                    "prompt": image_prompt[:100],
                    "filename": filename,
                }
            )
            continue

        # gpt-image-1이 이미지 안에 글자/텍스트를 그려 넣지 않도록 고정 부정 지시어 추가
        negative_prompt = (
            "No text, no words, no letters, no captions, no labels, no writing, "
            "no signage in the image. Pure illustration only."
        )
        full_prompt = f"{consistency_prefix} {image_prompt} {negative_prompt}".strip()

        image = client.images.generate(
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

        generated_images.append(
            {
                "page_number": page_number,
                "prompt": image_prompt[:100],
                "filename": filename,
            }
        )

    return {
        "total_images": len(generated_images),
        "generated_images": generated_images,
        "status": "complete",
    }
