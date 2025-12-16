# app/domain/incident_type.py
from enum import Enum, auto


class IncidentType(Enum):
    """
    장애 유형 정의.

    - TIMEOUT: Live API 웹훅 처리 중 타임아웃
    - API_ERROR: Live API 웹훅 처리 중 API 에러
    - LIVE_API_DB_OVERLOAD: 영상 생성 실패 (더빙/오디오), Live API DB 부하
    - YT_DOWNLOAD_FAIL: YouTube URL 다운로드 실패
    - YT_EXTERNAL_FAIL: 외부 요인으로 인한 영상 업로드 실패 (Video 파일 업로드 실패)
    """

    TIMEOUT = auto()                  # auto() 는 자동으로 값을 할당해주는 함수, 순서대로 1,2,3,4,5 할당해줌
    API_ERROR = auto()                # 파이썬에서는 값이 필수
    LIVE_API_DB_OVERLOAD = auto()
    YT_DOWNLOAD_FAIL = auto()
    YT_EXTERNAL_FAIL = auto()