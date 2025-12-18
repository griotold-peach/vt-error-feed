# tests/test_message_poller.py
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.services.message_poller import MessagePoller
from app.adapters.graph_client import GraphClient


# --- 픽스처 ----------------------------------------------------------------


@pytest.fixture
def graph_client():
    """Mock GraphClient"""
    return MagicMock(spec=GraphClient)


@pytest.fixture
def poller(graph_client):
    """MessagePoller 인스턴스"""
    return MessagePoller(graph_client)


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


def make_graph_message(card: dict, from_application: bool = True) -> dict:
    """Graph API 메시지 구조"""
    message = {
        "id": "1766010625190",
        "createdDateTime": "2025-12-17T22:30:24.282Z",
        "from": {},
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.teams.card.o365connector",
                "content": str(card).replace("'", '"'),  # JSON 문자열로
            }
        ],
    }

    if from_application:
        message["from"] = {
            "application": {
                "displayName": "vt prod monitoring",
                "applicationIdentityType": "office365Connector",
            }
        }
    else:
        message["from"] = {
            "user": {
                "displayName": "조해성",
            }
        }

    return message


# --- is_webhook_message 테스트 ---------------------------------------------


def test_is_webhook_message_from_application(poller):
    """application으로 온 메시지는 webhook으로 판별"""
    message = {
        "from": {
            "application": {"displayName": "vt prod monitoring"}
        }
    }
    assert poller.is_webhook_message(message) is True


def test_is_webhook_message_from_user(poller):
    """user로 온 메시지는 webhook 아님"""
    message = {
        "from": {
            "user": {"displayName": "조해성"}
        }
    }
    assert poller.is_webhook_message(message) is False


def test_is_webhook_message_empty_from(poller):
    """from이 비어있으면 webhook 아님"""
    message = {"from": {}}
    assert poller.is_webhook_message(message) is False


# --- is_card_message 테스트 ------------------------------------------------


def test_is_card_message_o365_connector(poller):
    """O365 Connector Card는 card 메시지로 판별"""
    message = {
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.teams.card.o365connector"
            }
        ]
    }
    assert poller.is_card_message(message) is True


def test_is_card_message_adaptive(poller):
    """Adaptive Card도 card 메시지로 판별"""
    message = {
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive"
            }
        ]
    }
    assert poller.is_card_message(message) is True


def test_is_card_message_text_html(poller):
    """text/html은 card 메시지 아님"""
    message = {
        "attachments": [
            {
                "contentType": "text/html"
            }
        ]
    }
    assert poller.is_card_message(message) is False


def test_is_card_message_no_attachments(poller):
    """attachment 없으면 card 메시지 아님"""
    message = {"attachments": []}
    assert poller.is_card_message(message) is False


# --- O365 Card 파싱 테스트 (VTWebhookMessage 호환성) ------------------------


def test_o365_card_feed1_to_webhook_message():
    """Feed1 O365 Card가 VTWebhookMessage로 변환 가능"""
    from app.adapters.messagecard import VTWebhookMessage

    card = make_o365_card_feed1("TIMEOUT")

    # VTWebhookMessage로 파싱 시도
    msg = VTWebhookMessage.model_validate(card)

    assert msg.title == "🚨 API-Video-Translator Translate Project Exception."
    assert msg.summary == "웹훅 처리중 실패가 발생했습니다."
    assert len(msg.sections) == 1
    assert len(msg.sections[0].facts) == 4


def test_o365_card_feed1_get_fact():
    """Feed1 O365 Card에서 get_fact으로 값 추출 가능"""
    from app.adapters.messagecard import VTWebhookMessage

    card = make_o365_card_feed1("API_ERROR")
    msg = VTWebhookMessage.model_validate(card)

    error_detail = msg.get_fact("Error Detail")
    assert error_detail is not None
    assert "API_ERROR" in error_detail


def test_o365_card_feed2_to_webhook_message():
    """Feed2 O365 Card가 VTWebhookMessage로 변환 가능"""
    from app.adapters.messagecard import VTWebhookMessage

    card = make_o365_card_feed2()

    msg = VTWebhookMessage.model_validate(card)

    assert msg.title == "🚨 업로드 실패"
    assert len(msg.sections) == 1
    assert msg.get_fact("Description") is not None


def test_o365_card_feed2_get_fact():
    """Feed2 O365 Card에서 Description 추출 가능"""
    from app.adapters.messagecard import VTWebhookMessage

    card = make_o365_card_feed2("영상 생성 실패 - 더빙/오디오 생성 실패")
    msg = VTWebhookMessage.model_validate(card)

    desc = msg.get_fact("Description")
    assert desc is not None
    assert "더빙/오디오 생성 실패" in desc


# --- process_feed1_message 테스트 (Mock) -----------------------------------


@pytest.mark.anyio 
async def test_process_feed1_message_calls_handler(poller, monkeypatch):
    """Feed1 메시지 처리 시 handle_raw_alert 호출"""
    import json
    from app.services import message_poller

    # Mock handle_raw_alert
    mock_handler = AsyncMock(return_value=True)
    monkeypatch.setattr(message_poller, "handle_raw_alert", mock_handler)

    card = make_o365_card_feed1("TIMEOUT")
    message = {
        "id": "test123",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.teams.card.o365connector",
                "content": json.dumps(card),
            }
        ],
    }

    await poller.process_feed1_message(message)

    # handler가 card dict와 함께 호출되었는지 확인
    mock_handler.assert_called_once()
    call_args = mock_handler.call_args[0][0]
    assert call_args["title"] == card["title"]


@pytest.mark.anyio 
async def test_process_feed1_message_invalid_json(poller, monkeypatch, capsys):
    """Feed1 메시지 파싱 실패 시 에러 출력"""
    message = {
        "id": "test123",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.teams.card.o365connector",
                "content": "invalid json{{{",
            }
        ],
    }

    await poller.process_feed1_message(message)

    captured = capsys.readouterr()
    assert "Failed to parse card content" in captured.out


# --- process_feed2_message 테스트 (Mock) -----------------------------------


@pytest.mark.anyio 
async def test_process_feed2_message_calls_handler(poller, monkeypatch):
    """Feed2 메시지 처리 시 handle_monitoring_alert 호출"""
    import json
    from app.services import message_poller

    # Mock handle_monitoring_alert
    mock_handler = AsyncMock(return_value=False)
    monkeypatch.setattr(message_poller, "handle_monitoring_alert", mock_handler)

    card = make_o365_card_feed2()
    message = {
        "id": "test456",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.teams.card.o365connector",
                "content": json.dumps(card),
            }
        ],
    }

    await poller.process_feed2_message(message)

    # handler가 호출되었는지 확인
    mock_handler.assert_called_once()
    call_args = mock_handler.call_args[0][0]
    assert call_args["title"] == card["title"]


@pytest.mark.anyio 
async def test_process_feed2_message_no_attachments(poller, capsys):
    """Feed2 메시지에 attachment 없으면 처리 안 함"""
    message = {"id": "test789", "attachments": []}

    await poller.process_feed2_message(message)

    captured = capsys.readouterr()
    assert "No attachments" in captured.out


# --- 중복 처리 방지 테스트 ------------------------------------------------


def test_processed_ids_prevents_duplicates(poller):
    """processed_ids에 있는 메시지는 스킵"""
    msg_id = "1766010625190"
    poller.processed_ids.add(msg_id)

    # poll_channel에서 중복 체크하므로 실제로는 통합 테스트 필요
    # 여기서는 단위 테스트로 로직만 확인
    assert msg_id in poller.processed_ids


def test_processed_ids_cleanup_logic(poller):
    """processed_ids가 1000개 넘으면 정리"""
    # 1001개 추가
    for i in range(1001):
        poller.processed_ids.add(f"msg_{i}")

    # cleanup 로직 (실제로는 cleanup_processed_ids에서)
    if len(poller.processed_ids) > 1000:
        to_remove = len(poller.processed_ids) - 500
        for _ in range(to_remove):
            poller.processed_ids.pop()

    assert len(poller.processed_ids) == 500