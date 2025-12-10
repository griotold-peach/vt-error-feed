# app/services/schemas.py
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field
import re


class Fact(BaseModel):
    """
    Teams MessageCard 의 sections[].facts[] 한 줄.
    ex) { "name": "Error Detail", "value": "Failure Reason: ENGINE_ERROR ..." }
    """
    name: str
    value: str


class Section(BaseModel):
    """
    Teams MessageCard 의 sections[] 하나.
    우리가 쓰는 건 activityTitle / facts 정도라서 나머지는 생략.
    """
    activityTitle: Optional[str] = None
    facts: List[Fact] = Field(default_factory=list)


class VTWebhookMessage(BaseModel):
    """
    VT 서버 → 우리 서버로 들어오는 MessageCard 전체 페이로드.
    실제 사용하는 필드만 정의해도 되고, 나머지는 자동으로 무시된다.
    """
    title: Optional[str] = None
    summary: Optional[str] = None
    sections: List[Section] = Field(default_factory=list)

    def get_fact(self, name: str) -> Optional[str]:
        """
        sections[].facts[] 중에서 name 이 일치하는 value 를 찾아준다.
        ex) get_fact("Error Detail") -> "Failure Reason: ENGINE_ERROR ..."
        """
        for section in self.sections:
            for fact in section.facts:
                if fact.name == name:
                    return fact.value
        return None


class VTErrorEvent(BaseModel):
    """
    비즈니스 로직에서 다루기 편하게 정제된 에러 이벤트.
    MessageCard에서 뽑은 값들을 모아둔다.
    """
    project: str
    error_message: str
    error_detail: str
    time: str

    # Error Detail 문자열에서 파싱해낸 Failure Reason (없을 수도 있음)
    failure_reason: Optional[str] = None
    cause_or_stack_trace: Optional[str] = None  # NEW! VIDEO_QUEUE_FULL 체크용도

    @classmethod
    def from_message(cls, msg: VTWebhookMessage) -> "VTErrorEvent":
        """
        VTWebhookMessage (원본 MessageCard) -> VTErrorEvent 로 변환.
        """
        project = msg.get_fact("Project") or ""
        error_message = msg.get_fact("Error Message") or ""
        error_detail = msg.get_fact("Error Detail") or ""
        time = msg.get_fact("Time") or ""
        cause = msg.get_fact("Cause or Stack Trace") or ""

        # "Failure Reason: ENGINE_ERROR ..." 형태에서 Failure Reason 값만 추출
        failure_reason = None
        if error_detail:
            m = re.search(r"Failure Reason:\s*([A-Z0-9_]+)", error_detail)
            if m:
                failure_reason = m.group(1)

        return cls(
            project=project,
            error_message=error_message,
            error_detail=error_detail,
            time=time,
            failure_reason=failure_reason,
            cause_or_stack_trace=cause,
        )
