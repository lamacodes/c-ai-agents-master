# 개발 중 발견한 문제와 해결 기록

`day-17` 미션(SequentialAgent + ParallelAgent + Callbacks) 구현 과정에서 실제로
`adk web`으로 테스트하며 발견한 문제들과 원인, 해결 방법을 정리한다.

## 1. `before_agent_callback`이 Content를 반환하면 실제 실행이 스킵됨

**증상**: 진행 상황 메시지(`📝 스토리 작성 중...`, `🎨 이미지 1/5 생성 중...` ~ `5/5`)까지는
채팅에 정상적으로 뜨는데, 그 이후로 아무 응답도 오지 않고 멈춘 것처럼 보임.

**원인**: ADK의 `base_agent.py`를 보면

```python
if event := await self._handle_before_agent_callback(ctx):
    yield event
if ctx.end_invocation:
    return   # 실제 _run_async_impl을 건너뜀
```

그리고 `_handle_before_agent_callback` 내부:

```python
if before_agent_callback_content:
    ...
    ctx.end_invocation = True   # Content를 반환하면 무조건 True
    return ret_event
```

즉 `before_agent_callback`이 `Content`를 반환하면 "진행 상황을 알리고 계속 실행"이
아니라 **"이 에이전트는 여기서 끝, 이 Content가 최종 응답"**으로 처리된다. 진행
메시지를 보여주려고 `Content`를 반환하도록 짠 콜백이 `StoryWriterAgent`와 5개
`IllustratorPageNAgent`의 실제 작업(LLM 호출, 이미지 생성 tool 호출)을 매번
스킵시켜버렸다.

**해결**: `callbacks.py`의 `make_progress_callback`이 `Content`를 반환하지 않도록
변경. 대신 로그 출력(`logger.info`)과 `state` 기록만 수행하고 `None`을 반환한다.
이 경로는 `ctx.end_invocation`을 건드리지 않아 실제 실행에 영향을 주지 않는다.

```python
def _progress_callback(callback_context):
    logger.info(message)
    callback_context.state["progress_message"] = message
    return None
```

트레이드오프: 진행 메시지가 채팅창에 말풍선으로는 안 뜨고, `adk web`을 실행 중인
터미널 로그로만 확인 가능하다.

## 2. 같은 세션에서 테마를 바꿔 다시 실행하면 이전 이미지가 그대로 나옴

**증상**: 첫 테마("용감한 아기 고양이")로 정상 생성 후, 같은 세션에서 두 번째
테마("우주를 여행하는 강아지")를 실행했더니 화면에 첫 번째 테마의 이미지가 그대로
보임.

**원인**: `illustrator/tools.py`의 이미지 생성 tool에 다음과 같은 "이미 생성된
파일이면 재생성하지 않는다" 로직이 있었다.

```python
existing_artifacts = await tool_context.list_artifacts()
if filename in existing_artifacts:
    return {"status": "complete", "filename": filename, "skipped": True}
```

파일명이 `page_1_image.jpeg`처럼 페이지 번호로만 고정되어 있어서, 같은 세션
안에서는 테마가 바뀌어도 "이미 있으니 스킵"으로 판단해버렸다. 원래는 같은 요청 내
재시도 시 중복 생성을 막으려던 안전장치였는데, 세션을 이어서 다른 테마를 생성하는
경우엔 오히려 버그가 됐다.

**해결**: skip 로직을 완전히 제거. 호출될 때마다 항상 새로 생성하고
`save_artifact`를 호출한다. ADK는 같은 파일명이라도 매번 새 버전
(`versions/0`, `versions/1`, ...)으로 저장하므로, 각 턴의 이벤트가 자기 버전을
정확히 참조해 이전 테마와 섞이지 않는다.

## 3. `StoryWriterAgent`가 가끔 5개가 아닌 더 적은 장면(scene)을 생성함

**증상**: 5페이지 중 1페이지 이미지만 생성되고 나머지 2~5페이지의
`IllustratorPageNAgent`는 전부 "story_writer_output에 page_number=N scene이
없습니다" 에러를 반환.

**원인**: `state.story_writer_output.scenes`를 확인해보니 실제로 배열 안에
`page_number: 1` 장면 하나만 들어있었다. 프롬프트에 "정확히 5개"라고 지시해도,
`gpt-4o-mini`가 가끔 이 지시를 지키지 않고 더 적은 개수를 생성하는 경우가 있었다
(schema 자체에는 개수 제약이 없어서, 모델이 몇 개를 반환하든 검증을 통과함).

**해결**: `sub_agents/story_writer/models.py`의 `scenes` 필드에 pydantic 제약을
추가해 스키마 레벨에서 강제.

```python
scenes: List[SceneOutput] = Field(min_length=5, max_length=5, ...)
```

`output_schema` 검증은 `model_validate_json`(pydantic)으로 이뤄지므로, 5개가
아니면 검증 단계에서 걸러진다. OpenAI strict 구조화 출력 모드에서 `minItems`/
`maxItems` 제약이 거부되지는 않는지 별도로 확인했고(텍스트 생성 1회로 저비용
검증), 정상적으로 5개(`page_number: 1~5`)가 나오는 것을 확인했다.

이 제약을 어기면(모델이 그래도 규칙을 안 지키면) 그 턴이 pydantic
`ValidationError`로 실패한다 — 이전처럼 "1페이지만 있고 나머지는 애매한 에러"보다
명확하게 실패해서 재시도가 필요함을 바로 알 수 있는 게 낫다고 판단했다.

## 4. (참고) LlmAgent + tool 방식의 신뢰성 리스크

`IllustratorPageNAgent`가 가끔 tool을 호출하지 않고, 프롬프트에 적어둔 "데이터가
없으면 이렇게 말해라"는 안내 문구를 그대로 베껴서 답하는 현상을 한 번 관찰했다
(state에는 실제로 데이터가 있었는데도). `illustrator/prompt.py`에서 "state 유무를
스스로 판단하지 말고 무조건 tool을 먼저 호출하라"고 지시를 강하게 바꿔 완화했다.
다만 이건 작은 모델(`gpt-4o-mini`)을 쓰는 한 100% 근절되는 문제는 아니라서, 이후에도
간헐적으로 재현될 수 있다는 점은 알아두는 게 좋다.

## 5. 모범답안(`solutions.md`)과 비교

과제 모범답안이 뒤늦게 제공되어 우리 구현과 비교했다. 아키텍처의 뼈대
(`SequentialAgent(StoryWriterAgent, ParallelAgent(5개 페이지 Agent))`,
`output_schema` + `output_key`로 State 공유)는 동일하다. 세부 설계에서 다음과
같은 차이가 있었다.

### 동일하게 확인된 것: callback은 Content를 반환하면 안 된다
모범답안의 `on_story_start`/`on_story_done`/`on_illustrations_start`/
`on_illustrations_done`는 전부 `print()`만 하고 `return None`한다. 우리가 겪은
"before_agent_callback이 Content를 반환하면 실제 실행을 스킵한다"는 버그(위 1번)를
모범답안은 애초에 안전한 패턴으로 피해간 셈이다. 다만 모범답안은 콜백을
`story_writer_agent`와 `ParallelAgent` 전체에만 붙이고, 페이지별 진행 메시지
("🖼️ Generating image N/5...")는 agent 콜백이 아니라 **tool 함수 내부에서 그냥
print**로 처리한다 — 5개 agent 각각에 `before_agent_callback`을 붙인 우리 방식보다
더 단순하다.

### 모범답안에도 남아있는 잠재적 버그
- **세션 재사용 시 이미지 재사용(위 2번)**: 모범답안의 `generate_page_image`도
  `if filename in existing: return {"status": "cached", ...}`로 동일한 스킵
  로직을 갖고 있다. 즉 모범답안 코드 그대로 구현해도 같은 세션에서 테마를 바꾸면
  이전 이미지가 재사용되는 문제가 그대로 재현될 것이다.
- **"정확히 5페이지" 미보장(위 3번)**: `pages: List[PageOutput] = Field(description="List of 5 story pages")`에
  개수 제약이 없다. 우리가 겪은 "1페이지만 생성되는" 문제가 모범답안 코드에서도
  똑같이 발생할 수 있다.

### 모범답안과 다른 설계 선택
- **`page_number`를 tool 인자로 받음(모범답안) vs 클로저로 고정(우리)**:
  모범답안은 `generate_page_image(tool_context, page_number: int)`처럼 LLM이
  `page_number`를 직접 채우게 하고 프롬프트로 "page_number={page_num}을 써서
  호출해"라고 지시한다. 우리는 `make_generate_page_image_tool(page_number)`
  팩토리로 페이지 번호를 아예 고정해, LLM이 tool 호출을 생략하거나 엉뚱한 페이지
  번호를 넣을 위험(위 4번과 연결되는 리스크)을 원천 차단했다.
- **캐릭터/화풍 일관성**: 모범답안의 이미지 프롬프트는
  `"Children's book illustration, colorful, whimsical..." + visual_description`뿐이라
  페이지마다 캐릭터 생김새나 화풍이 달라질 위험이 크다. 우리는 `art_style` +
  `character_bible`을 스키마에 추가하고 `build_consistency_prefix`로 모든
  페이지에 동일하게 주입한다.
- **최종 "완성된 동화책" 출력**: 모범답안은 `root_agent = SequentialAgent(sub_agents=[story_writer_agent, parallel_illustrator])`로
  끝나서 조립 단계가 없다 — 마지막 사용자 응답이 마지막 페이지 tool의 짧은 응답
  정도에 그칠 가능성이 높다. 우리는 `after_agent_callback=assemble_storybook_callback`으로
  제목 + 5페이지(Text/Visual) + 이미지 파일명을 정리한 최종 메시지를 만든다.
- **기타**: 모델(`gemini-2.0-flash` vs `openai/gpt-4o-mini`), 이미지 사이즈/포맷
  (`1024x1024 png` vs `1024x1536 jpeg` + no-text negative prompt) — 환경/취향 차이.

## 아키텍처 요약 (최종)

```
root_agent = SequentialAgent("StoryBookPipeline")
├─ story_writer_agent (LlmAgent, output_schema=StoryWriterOutput)
│    before_agent_callback: "📝 스토리 작성 중..." (로그만)
└─ illustrator_parallel_agent = ParallelAgent
     ├─ IllustratorPage1Agent (LlmAgent + generate_page_1_image tool)
     ├─ IllustratorPage2Agent
     ├─ IllustratorPage3Agent
     ├─ IllustratorPage4Agent
     └─ IllustratorPage5Agent
          각각 before_agent_callback: "🎨 이미지 N/5 생성 중..." (로그만)

root_agent.after_agent_callback = assemble_storybook_callback
  → state의 story_writer_output을 모아 제목 + 5페이지(Text/Visual/이미지파일명)로 조립
```
