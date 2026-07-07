import logging

from google.genai import types

logger = logging.getLogger("story_book_maker.progress")


def make_progress_callback(message: str):
    """진행 상황을 알리는 before_agent_callback을 생성"""

    def _progress_callback(callback_context):
        logger.info(message)
        callback_context.state["progress_message"] = message
        return None

    return _progress_callback


def assemble_storybook_callback(callback_context):
    """파이프라인 종료 후 state를 모아 완성된 동화책 형태로 조립"""

    story = callback_context.state.get("story_writer_output")
    if not story:
        return None

    lines = [f"# {story.get('title', '동화책')}", ""]
    summary = story.get("summary")
    if summary:
        lines.append(summary)
        lines.append("")

    for scene in story.get("scenes", []):
        page_number = scene.get("page_number")
        lines.append(f"## Page {page_number}")
        lines.append(f"Text: {scene.get('narration', '')}")
        lines.append(f"Visual: {scene.get('image_prompt', '')}")
        lines.append(f"Image: page_{page_number}_image.jpeg (Artifact)")
        lines.append("")

    return types.Content(
        role="model",
        parts=[types.Part(text="\n".join(lines))],
    )
