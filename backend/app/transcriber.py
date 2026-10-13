"""받아쓰기 - Gemini 2단계. 테스트에서는 process 를 바꿔 끼우는 유일한 지점

1단계: 녹취 오디오 -> 전문
2단계: 전문을 같은 모델에 다시 넣어 요약 / 결정사항 / 할 일 로 구분 (정의서 9절 받아쓰기)
"""
import json
import os

from .errors import AppError

TIMEOUT_MS = 30_000  # 단계당. 두 단계 합쳐 60초 이내

TRANSCRIBE_PROMPT = "이 회의 녹음을 한국어로 빠짐없이 받아쓰세요. 설명 없이 받아쓴 전문만 출력하세요."
STRUCTURE_PROMPT = (
    "다음은 회의 전문입니다. 세 항목으로 나누어 JSON 으로만 답하세요.\n"
    '{"summary": ["요약 문장", ...], "decisions": ["결정사항", ...], '
    '"todos": [{"what": "할 일", "due_text": "기한(없으면 빈 문자열)"}]}\n\n'
    "회의 전문:\n"
)


def _client():
    from google import genai
    from google.genai import types

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise AppError(500, "INTERNAL_ERROR", "GEMINI_API_KEY 가 설정되지 않았습니다")
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_MS)), types


def process(data: bytes, mime_type: str) -> dict:
    """오디오 바이트 -> {body, summary, decisions, todos}"""
    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    try:
        client, types = _client()
        raw = client.models.generate_content(
            model=model,
            contents=[types.Part.from_bytes(data=data, mime_type=mime_type), TRANSCRIBE_PROMPT],
        )
        body = (raw.text or "").strip()
        structured = client.models.generate_content(
            model=model,
            contents=STRUCTURE_PROMPT + body,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        parsed = json.loads(structured.text)
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001 - 외부 API 오류는 한 가지 응답으로 통일
        raise AppError(500, "INTERNAL_ERROR", f"받아쓰기에 실패했습니다: {type(e).__name__}")
    summary = parsed.get("summary", "")
    if isinstance(summary, list):
        summary = "\n".join(str(s) for s in summary)
    todos = []
    for t in parsed.get("todos", []):
        if isinstance(t, str):
            t = {"what": t}
        if t.get("what"):
            todos.append({"what": str(t["what"]), "due_text": str(t.get("due_text", ""))})
    return {
        "body": body,
        "summary": summary,
        "decisions": [str(d) for d in parsed.get("decisions", []) if str(d).strip()],
        "todos": todos,
    }
