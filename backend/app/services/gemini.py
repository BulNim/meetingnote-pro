"""Gemini 호출은 이 파일 한 곳에서만 한다.

- transcribe: 녹취 파일 -> 받아쓴 본문 텍스트 (저장하지 않음, 길이 제한 없음)
- organize:   본문 -> 요약 · 결정사항 · 할 일 (본문은 그대로 두고 세 항목만 뽑음)
모델 이름과 키는 .env 의 GEMINI_MODEL · GEMINI_API_KEY 에서 온다.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, ValidationError

from ..config import get_settings

UNDECIDED = "미정"


class GeminiError(Exception):
    """Gemini 호출 실패 (키 없음 · 네트워크 · 응답 형식 오류 모두)"""


@dataclass
class TodoItem:
    what: str
    assignee: str | None = None  # 팀 멤버 이름과 일치할 때만 값이 있다
    due: str = UNDECIDED


@dataclass
class Organized:
    summary: str = ""
    decisions: list[str] = field(default_factory=list)
    todos: list[TodoItem] = field(default_factory=list)


class _TodoOut(BaseModel):
    what: str
    assignee: str = ""
    due: str = ""


class _OrganizedOut(BaseModel):
    summary: str = ""
    decisions: list[str] = []
    todos: list[_TodoOut] = []


TRANSCRIBE_PROMPT = (
    "이 녹취 파일의 말을 한국어 그대로 받아 적어라. 요약하거나 고치거나 설명을 붙이지 말고, "
    "화자 구분 없이 받아 적은 본문 텍스트만 출력하라."
)

ORGANIZE_PROMPT = """너는 회의록 정리기다. 아래 회의 본문을 세 항목으로 나눠 JSON 으로만 답하라.

규칙:
- summary: 회의 전체를 3~5줄로 쓴다. 본문에 없는 사실을 보태지 않는다.
- decisions: 합의가 끝난 것만 적는다 (「하기로 했다」 「확정」 「승인」). 논의만 하고 정하지 않은 것은 넣지 않는다. 없으면 빈 배열.
- todos: 담당자나 기한이 드러난 문장만 뽑는다. 없으면 빈 배열.
  - what: 할 일 내용
  - assignee: 아래 팀 멤버 이름 중 정확히 하나. 본문에서 담당자가 드러나지 않거나 멤버 이름과 맞지 않으면 빈 문자열. 지어내지 않는다.
  - due: 본문에 드러난 기한 표현 그대로 (예: 다음 주 금요일). 없으면 「미정」.

팀 멤버: {members}
회의 시각(UTC): {met_at}

회의 본문:
{body}
"""


def normalize(raw: _OrganizedOut, member_names: list[str]) -> Organized:
    """Gemini 응답을 규칙에 맞게 다듬는다. 담당자는 멤버 이름과 일치할 때만 인정"""
    names = {n: n for n in member_names}
    todos: list[TodoItem] = []
    for t in raw.todos:
        what = t.what.strip()
        if not what:
            continue
        assignee = names.get(t.assignee.strip())
        todos.append(TodoItem(what=what, assignee=assignee, due=t.due.strip() or UNDECIDED))
    return Organized(
        summary=raw.summary.strip(),
        decisions=[d.strip() for d in raw.decisions if d.strip()],
        todos=todos,
    )


class GeminiService:
    def _client(self):
        settings = get_settings()
        if not settings.gemini_api_key:
            raise GeminiError("GEMINI_API_KEY 가 비어 있음")
        from google import genai

        return genai.Client(api_key=settings.gemini_api_key), settings.gemini_model

    def transcribe(self, audio: bytes, mime_type: str) -> str:
        try:
            from google.genai import types

            client, model = self._client()
            resp = client.models.generate_content(
                model=model,
                contents=[TRANSCRIBE_PROMPT, types.Part.from_bytes(data=audio, mime_type=mime_type)],
            )
            text = (resp.text or "").strip()
        except GeminiError:
            raise
        except Exception as e:  # SDK 오류는 종류가 많아 한 곳에서 묶는다
            raise GeminiError(f"받아쓰기 실패: {e}") from e
        if not text:
            raise GeminiError("받아쓰기 결과가 비어 있음")
        return text

    def organize(self, body: str, member_names: list[str], met_at: datetime) -> Organized:
        try:
            from google.genai import types

            client, model = self._client()
            prompt = ORGANIZE_PROMPT.format(
                members=", ".join(member_names) or "(없음)",
                met_at=met_at.isoformat(),
                body=body,
            )
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_OrganizedOut,
                ),
            )
            raw = _OrganizedOut.model_validate(json.loads(resp.text))
        except GeminiError:
            raise
        except (ValidationError, json.JSONDecodeError, TypeError) as e:
            raise GeminiError(f"정리 응답 형식 오류: {e}") from e
        except Exception as e:
            raise GeminiError(f"정리 실패: {e}") from e
        return normalize(raw, member_names)


def get_gemini() -> GeminiService:
    """FastAPI 의존성. 테스트는 이 함수를 가짜로 바꾼다"""
    return GeminiService()
