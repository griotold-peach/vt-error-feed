# app/domain/events.py
#
# TODO: If future "pattern B" bots send text-only payloads, consider wiring an adapter
# (e.g., `adapt_raw_payload_to_vt_event(raw: dict | str) -> VTErrorEvent`) that converts
# arbitrary payloads into VTWebhookMessage / VTErrorEvent before business logic consumes them.
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import re

from pydantic import BaseModel

from app.adapters.messagecard import VTWebhookMessage


class VTErrorEvent(BaseModel):
    """
    Domain model for business logic.

    Derived from VTWebhookMessage via get_fact lookups so callers can work with
    structured fields instead of raw MessageCards.
    failure_reason / cause_or_stack_trace are optional results of parsing.
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

    def event_datetime(self) -> datetime:
        """
        Parse the `time` field into a timezone-aware UTC datetime.

        Expected input format resembles `2025-12-08T03:40:00.000000000Z[Etc/UTC]`.
        Implementation takes the substring before `Z`, trims fractional seconds to 6 digits,
        then feeds the result to `datetime.fromisoformat`.
        If parsing fails, falls back to `datetime.now(timezone.utc)`.
        """
        # 예: "2025-12-09T20:10:51.796441041Z[Etc/UTC]"
        raw = self.time
        if not raw:
            return datetime.now(timezone.utc)

        # Z 앞까지만 사용
        # 2025-12-09T20:10:51.796441041Z[Etc/UTC] -> 2025-12-09T20:10:51.796441
        try:
            # 소수점 6자리까지만 자르고 파싱
            before_z = raw.split("Z", 1)[0]  # "2025-12-09T20:10:51.796441041"
            if "." in before_z:
                date_part, frac = before_z.split(".", 1)
                frac = (frac + "000000")[:6]  # 6자리로 패딩/자르기
                trimmed = f"{date_part}.{frac}"
            else:
                trimmed = before_z

            return datetime.fromisoformat(trimmed)
        except Exception:
            # 포맷이 예상과 다르면 일단 현재 시각으로 fallback
            return datetime.now(timezone.utc)
