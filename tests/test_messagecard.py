# tests/test_messagecard.py
import pytest
from app.adapters.messagecard import VTWebhookMessage, Section, Fact


# --- Helper 데이터 ---------------------------------------------------------

def make_o365_card_feed1(failure_reason: str = "TIMEOUT") -> dict:
    """Feed1 O365 Connector Card 샘플"""
    return {
        "summary": "웹훅 처리중 실패가 발생했습니다.",
        "title": "🚨 API-Video-Translator Translate Project Exception.",
        "themeColor": "FF0000",
        "sections": [
            {
                "facts": [
                    {"name": "Project", "value": "<p>276459</p>"},
                    {
                        "name": "Error Message",
                        "value": "<p>Received Failed Webhook Event by Live API.</p>",
                    },
                    {
                        "name": "Error Detail",
                        "value": f"<p>Failure Reason: {failure_reason}</p>",
                    },
                    {
                        "name": "Time",
                        "value": "<p>2025-12-17T22:30:24.282061408Z[Etc/UTC]</p>",
                    },
                ],
                "activityTitle": "<p>웹훅 처리중 실패가 발생했습니다.</p>",
                "markdown": True,
                "startGroup": False,
            }
        ],
    }


def make_o365_card_feed2(description: str = "영상 업로드 실패 - Video 파일 업로드 실패") -> dict:
    """Feed2 O365 Connector Card 샘플"""
    return {
        "summary": "An exception occurred in the application",
        "title": "🚨 업로드 실패",
        "themeColor": "FFA500",
        "sections": [
            {
                "facts": [
                    {"name": "Description", "value": f"<p>{description}</p>"},
                    {
                        "name": "Time",
                        "value": "<p>2025-12-17T23:44:04.151606+0000[UTC]</p>",
                    },
                ],
                "activityTitle": "<p>Video 파일 업로드 실패</p>",
                "markdown": True,
                "startGroup": False,
            }
        ],
    }


# --- VTWebhookMessage 파싱 테스트 -----------------------------------------

def test_parse_feed1_o365_card():
    """Feed1 O365 Card를 VTWebhookMessage로 파싱"""
    card = make_o365_card_feed1("TIMEOUT")
    msg = VTWebhookMessage.model_validate(card)

    assert msg.title == "🚨 API-Video-Translator Translate Project Exception."
    assert msg.summary == "웹훅 처리중 실패가 발생했습니다."
    assert len(msg.sections) == 1
    assert len(msg.sections[0].facts) == 4


def test_parse_feed2_o365_card():
    """Feed2 O365 Card를 VTWebhookMessage로 파싱"""
    card = make_o365_card_feed2()
    msg = VTWebhookMessage.model_validate(card)

    assert msg.title == "🚨 업로드 실패"
    assert msg.summary == "An exception occurred in the application"
    assert len(msg.sections) == 1


def test_parse_minimal_card():
    """최소 필드만 있는 Card 파싱"""
    card = {"title": "Test"}
    msg = VTWebhookMessage.model_validate(card)

    assert msg.title == "Test"
    assert msg.summary is None
    assert msg.sections == []


def test_parse_card_with_extra_fields():
    """Pydantic이 모르는 필드는 무시"""
    card = {
        "title": "Test",
        "unknown_field": "should be ignored",
        "potentialAction": [],  # 우리가 쓰지 않는 필드
    }
    msg = VTWebhookMessage.model_validate(card)

    assert msg.title == "Test"
    # unknown_field는 모델에 없으므로 접근 불가


# --- get_fact() 메서드 테스트 ---------------------------------------------

def test_get_fact_found():
    """존재하는 fact를 찾을 수 있음"""
    card = make_o365_card_feed1("API_ERROR")
    msg = VTWebhookMessage.model_validate(card)

    error_detail = msg.get_fact("Error Detail")
    assert error_detail is not None
    assert "API_ERROR" in error_detail


def test_get_fact_not_found():
    """존재하지 않는 fact는 None 반환"""
    card = make_o365_card_feed1()
    msg = VTWebhookMessage.model_validate(card)

    result = msg.get_fact("Non Existent Field")
    assert result is None


def test_get_fact_multiple_sections():
    """여러 section에서 fact 찾기"""
    card = {
        "title": "Test",
        "sections": [
            {
                "facts": [
                    {"name": "Field1", "value": "Value1"}
                ]
            },
            {
                "facts": [
                    {"name": "Field2", "value": "Value2"}
                ]
            }
        ]
    }
    msg = VTWebhookMessage.model_validate(card)

    assert msg.get_fact("Field1") == "Value1"
    assert msg.get_fact("Field2") == "Value2"


def test_get_fact_returns_first_match():
    """같은 name이 여러 개면 첫 번째 반환"""
    card = {
        "title": "Test",
        "sections": [
            {
                "facts": [
                    {"name": "Duplicate", "value": "First"},
                    {"name": "Duplicate", "value": "Second"}
                ]
            }
        ]
    }
    msg = VTWebhookMessage.model_validate(card)

    assert msg.get_fact("Duplicate") == "First"


# --- Feed1 특화 테스트 ----------------------------------------------------

def test_feed1_extract_failure_reason():
    """Feed1에서 Failure Reason 추출"""
    card = make_o365_card_feed1("TIMEOUT")
    msg = VTWebhookMessage.model_validate(card)

    error_detail = msg.get_fact("Error Detail")
    assert "TIMEOUT" in error_detail


def test_feed1_extract_project_id():
    """Feed1에서 Project ID 추출"""
    card = make_o365_card_feed1()
    msg = VTWebhookMessage.model_validate(card)

    project = msg.get_fact("Project")
    assert "276459" in project


# --- Feed2 특화 테스트 ----------------------------------------------------

def test_feed2_extract_description():
    """Feed2에서 Description 추출"""
    card = make_o365_card_feed2("영상 생성 실패 - 더빙/오디오 생성 실패")
    msg = VTWebhookMessage.model_validate(card)

    desc = msg.get_fact("Description")
    assert desc is not None
    assert "더빙/오디오 생성 실패" in desc


def test_feed2_various_descriptions():
    """Feed2의 다양한 Description 케이스"""
    test_cases = [
        "영상 생성 실패 - 더빙/오디오 생성 실패",
        "영상 업로드 실패 - YouTube URL 다운로드 실패",
        "영상 업로드 실패 - Video 파일 업로드 실패",
    ]

    for desc_text in test_cases:
        card = make_o365_card_feed2(desc_text)
        msg = VTWebhookMessage.model_validate(card)
        
        desc = msg.get_fact("Description")
        assert desc_text in desc


# --- Section/Fact 모델 테스트 ---------------------------------------------

def test_fact_model():
    """Fact 모델 생성"""
    fact = Fact(name="Test", value="Value")
    assert fact.name == "Test"
    assert fact.value == "Value"


def test_section_model_default():
    """Section 모델 기본값"""
    section = Section()
    assert section.activityTitle is None
    assert section.facts == []


def test_section_model_with_facts():
    """Section 모델에 facts 추가"""
    section = Section(
        activityTitle="Title",
        facts=[
            Fact(name="A", value="1"),
            Fact(name="B", value="2")
        ]
    )
    assert section.activityTitle == "Title"
    assert len(section.facts) == 2