# app/adapters/messagecard.py
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


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
    Teams MessageCard JSON payload used by VT → webhook.

    - sections[].facts[] carries name/value pairs such as "Project", "Error Message",
      "Error Detail", "Time", "Cause or Stack Trace".
    - We model only the subset of fields we rely on; Pydantic ignores the rest.
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
