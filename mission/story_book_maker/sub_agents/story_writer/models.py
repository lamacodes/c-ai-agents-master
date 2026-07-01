from pydantic import BaseModel, Field
from typing import List


class CharacterSpec(BaseModel):
    name: str = Field(description="캐릭터의 이름")
    appearance: str = Field(
        description=(
            "캐릭터의 고정 외형 묘사. 종류(토끼/거북이 등), 털/피부 색, 크기, 옷, "
            "액세서리 등 모든 페이지에서 동일하게 유지되어야 할 핵심 외형 특징을 구체적으로 작성한다."
        )
    )


class SceneOutput(BaseModel):
    page_number: int = Field(description="장면의 페이지 번호 (1~5)")
    narration: str = Field(
        description="해당 페이지에 들어갈 동화 텍스트(내레이션, Text)"
    )
    image_prompt: str = Field(
        description=(
            "해당 페이지만의 장면(상황/동작/배경/구도)을 묘사하는 시각 설명(Visual). "
            "IllustratorAgent가 이미지를 생성할 때 사용한다. "
            "캐릭터는 character_bible에 정의한 이름으로 지정하되, 외형은 반복해 묘사하지 않는다 "
            "(외형과 화풍은 art_style·character_bible에서 공통 적용됨)."
        )
    )


class StoryWriterOutput(BaseModel):
    title: str = Field(description="동화책 제목")
    summary: str = Field(description="동화 전체 줄거리 요약")
    art_style: str = Field(
        description=(
            "동화책 전체에 적용될 고정 화풍/색감. "
            "예: '따뜻한 수채화 일러스트, 파스텔 톤, 부드러운 텍스처, 어린이 동화책 스타일'. "
            "모든 페이지에 동일하게 적용된다."
        )
    )
    character_bible: List[CharacterSpec] = Field(
        description=(
            "동화에 등장하는 모든 캐릭터의 고정 외형 정의 목록. "
            "여기 정의된 외형은 모든 페이지의 이미지에서 동일하게 유지된다."
        )
    )
    scenes: List[SceneOutput] = Field(
        description="5페이지 분량의 장면 목록 (정확히 5개)"
    )
