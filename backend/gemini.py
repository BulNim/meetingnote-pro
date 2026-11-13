"""Gemini 호출 - 받아쓰기와 세 항목(요약 · 결정사항 · 할 일) 구분. 바꿔 끼울 수 있게 이 파일 한 곳에만 둔다.

시험은 transcribe · classify 두 함수를 가짜로 바꿔 키와 네트워크 없이 돈다.
"""
import io
import json
import logging

from pydantic import BaseModel

from . import config

log = logging.getLogger("meetingnote.gemini")


class GeminiError(Exception):
    """받아쓰기 · 구분 실패. 라우터가 502 VALIDATION_ERROR 로 바꾼다."""


class TodoItem(BaseModel):
    what: str
    assignee: str = ""
    due: str = ""


class Classified(BaseModel):
    summary: str
    decisions: list[str]
    todos: list[TodoItem]


TRANSCRIBE_PROMPT = (
    "다음 회의 녹음을 한국어로 받아써라. 들리는 말만 그대로 적고, 요약하거나 꾸미지 마라. "
    "화자를 구분하지 말고 한 덩어리 본문으로 적어라."
)

CLASSIFY_PROMPT = """다음은 회의를 받아쓴 본문이다. 세 항목으로 나눠 JSON 으로 답하라.

- summary: 회의 전체를 3~5줄로. 본문에 없는 사실을 보태지 않는다.
- decisions: 합의가 끝난 것만 한 항목씩 (「하기로 했다 · 확정 · 승인」). 논의만 한 것은 넣지 않는다. 없으면 빈 배열.
- todos: 담당자나 기한이 본문에 드러난 할 일만. what=할 일 내용, assignee=본문에 나온 담당자 이름(없으면 빈 문자열), due=본문에 나온 기한 글자 그대로(없으면 빈 문자열). 없으면 빈 배열.

팀 멤버 이름: {members}

본문:
{body}
"""


def _client():
    key = config.gemini_key()
    if not key:
        raise GeminiError("GEMINI_API_KEY 없음")
    from google import genai

    return genai.Client(api_key=key)


def _call(fn):
    """공급자 5xx 는 1회 재시도한 뒤 실패로 본다."""
    from google.genai import errors

    for attempt in (1, 2):
        try:
            return fn()
        except errors.ServerError as e:
            log.warning("Gemini 5xx (%s회차): %s", attempt, e)
            if attempt == 2:
                raise GeminiError(f"Gemini 서버 오류 - {e.code}") from e
        except errors.APIError as e:
            raise GeminiError(f"Gemini 응답 오류 - {e.code}") from e


def transcribe(data: bytes, mime_type: str) -> str:
    client = _client()
    from google.genai import types

    if len(data) > config.INLINE_MAX:
        uploaded = _call(lambda: client.files.upload(
            file=io.BytesIO(data), config=types.UploadFileConfig(mime_type=mime_type)))
        part = uploaded
    else:
        part = types.Part.from_bytes(data=data, mime_type=mime_type)
    res = _call(lambda: client.models.generate_content(
        model=config.gemini_model(), contents=[TRANSCRIBE_PROMPT, part]))
    text = (getattr(res, "text", None) or "").strip()
    if not text:
        raise GeminiError("받아쓰기 결과가 비어 있음")
    return text


def classify(body: str, members: list[str]) -> Classified:
    client = _client()
    from google.genai import types

    prompt = CLASSIFY_PROMPT.format(members=", ".join(members) or "(없음)", body=body)
    res = _call(lambda: client.models.generate_content(
        model=config.gemini_model(),
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Classified),
    ))
    try:
        parsed = getattr(res, "parsed", None)
        if isinstance(parsed, Classified):
            return parsed
        return Classified.model_validate(json.loads(res.text))
    except Exception as e:  # noqa: BLE001 - 어떤 형식 오류든 구분 실패
        raise GeminiError("세 항목 구분 응답을 읽지 못함") from e


def audio_mime(data: bytes) -> str | None:
    """확장자가 아니라 파일 머리 바이트로 판정한다. wav · mp3 만."""
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:3] == b"ID3":
        return "audio/mpeg"
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "audio/mpeg"
    return None


def normalize_name(name: str) -> str:
    """담당자 대조용 - 공백과 끝의 「님」을 지운다."""
    n = "".join((name or "").split())
    while n.endswith("님"):
        n = n[:-1]
    return n
