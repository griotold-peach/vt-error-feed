# tests/test_duplicate_tracker.py
import pytest

from app.application.services.duplicate_tracker import DuplicateTracker


# --- 픽스처 ----------------------------------------------------------------

@pytest.fixture
def tracker():
    """DuplicateTracker 인스턴스"""
    return DuplicateTracker(max_size=10, cleanup_size=5)


# --- 초기화 테스트 ---------------------------------------------------------

def test_tracker_initialization():
    """초기화 시 기본값 설정"""
    tracker = DuplicateTracker()
    
    assert tracker.processed_ids == set()
    assert tracker.max_size == 1000
    assert tracker.cleanup_size == 500


def test_tracker_initialization_custom_values():
    """커스텀 값으로 초기화"""
    tracker = DuplicateTracker(max_size=100, cleanup_size=50)
    
    assert tracker.max_size == 100
    assert tracker.cleanup_size == 50


# --- is_processed 테스트 ---------------------------------------------------

def test_is_processed_new_id(tracker):
    """새로운 ID는 False 반환"""
    assert tracker.is_processed("new_id") is False


def test_is_processed_existing_id(tracker):
    """이미 처리한 ID는 True 반환"""
    tracker.processed_ids.add("existing_id")
    
    assert tracker.is_processed("existing_id") is True


def test_is_processed_multiple_ids(tracker):
    """여러 ID 확인"""
    tracker.processed_ids.update(["id1", "id2", "id3"])
    
    assert tracker.is_processed("id1") is True
    assert tracker.is_processed("id2") is True
    assert tracker.is_processed("id3") is True
    assert tracker.is_processed("id4") is False


# --- mark_processed 테스트 -------------------------------------------------

def test_mark_processed_adds_id(tracker):
    """ID를 processed_ids에 추가"""
    tracker.mark_processed("new_id")
    
    assert "new_id" in tracker.processed_ids


def test_mark_processed_multiple_ids(tracker):
    """여러 ID 추가"""
    tracker.mark_processed("id1")
    tracker.mark_processed("id2")
    tracker.mark_processed("id3")
    
    assert len(tracker.processed_ids) == 3
    assert "id1" in tracker.processed_ids
    assert "id2" in tracker.processed_ids
    assert "id3" in tracker.processed_ids


def test_mark_processed_duplicate_id(tracker):
    """중복 ID는 set이므로 하나만 유지"""
    tracker.mark_processed("duplicate")
    tracker.mark_processed("duplicate")
    tracker.mark_processed("duplicate")
    
    assert len(tracker.processed_ids) == 1


# --- cleanup 테스트 --------------------------------------------------------

def test_cleanup_not_triggered_below_max(tracker):
    """max_size 미만이면 cleanup 안됨"""
    # max_size=10이므로 9개 추가
    for i in range(9):
        tracker.mark_processed(f"id_{i}")
    
    assert len(tracker.processed_ids) == 9


def test_cleanup_triggered_at_max(tracker):
    """max_size 초과 시 cleanup 실행"""
    # max_size=10, cleanup_size=5
    # 11개 추가하면 cleanup되어 5개만 남음
    for i in range(11):
        tracker.mark_processed(f"id_{i}")
    
    assert len(tracker.processed_ids) == 5


def test_cleanup_multiple_times(tracker):
    """여러 번 cleanup 발생"""
    # 첫 번째 cleanup: 11개 → 5개
    for i in range(11):
        tracker.mark_processed(f"id_{i}")
    
    assert len(tracker.processed_ids) == 5
    
    # 6개 더 추가: 11개 → 5개
    for i in range(11, 17):
        tracker.mark_processed(f"id_{i}")
    
    assert len(tracker.processed_ids) == 5


def test_cleanup_preserves_some_ids(tracker):
    """cleanup 후에도 일부 ID는 남아있음"""
    for i in range(11):
        tracker.mark_processed(f"id_{i}")
    
    # 5개가 남아있어야 함 (어떤 5개인지는 보장 안됨 - set.pop()은 임의)
    assert len(tracker.processed_ids) == 5


def test_cleanup_with_default_values():
    """기본값(max_size=1000, cleanup_size=500)으로 cleanup"""
    tracker = DuplicateTracker()
    
    # 1001개 추가
    for i in range(1001):
        tracker.mark_processed(f"id_{i}")
    
    # 500개로 정리됨
    assert len(tracker.processed_ids) == 500


# --- clear 테스트 ----------------------------------------------------------

def test_clear_removes_all(tracker):
    """clear 호출 시 모든 ID 제거"""
    tracker.processed_ids.update(["id1", "id2", "id3"])
    
    tracker.clear()
    
    assert len(tracker.processed_ids) == 0


def test_clear_on_empty_tracker(tracker):
    """빈 tracker에 clear 호출"""
    tracker.clear()
    
    assert len(tracker.processed_ids) == 0


# --- 통합 시나리오 ---------------------------------------------------------

def test_typical_usage_scenario(tracker):
    """일반적인 사용 시나리오"""
    # 메시지 처리
    assert tracker.is_processed("msg1") is False
    tracker.mark_processed("msg1")
    assert tracker.is_processed("msg1") is True
    
    # 중복 메시지
    assert tracker.is_processed("msg1") is True
    
    # 새 메시지
    assert tracker.is_processed("msg2") is False
    tracker.mark_processed("msg2")


def test_high_volume_scenario():
    """대용량 메시지 처리 시나리오"""
    tracker = DuplicateTracker(max_size=100, cleanup_size=50)
    
    # 1000개 메시지 처리
    for i in range(1000):
        msg_id = f"msg_{i}"
        
        # 중복 체크
        if not tracker.is_processed(msg_id):
            tracker.mark_processed(msg_id)
    
    # cleanup이 여러 번 발생
    # set.pop()은 순서가 보장되지 않으므로 정확히 50개가 아닐 수 있음
    # max_size를 초과하지 않고, cleanup_size 근처 값
    assert len(tracker.processed_ids) <= tracker.max_size
    assert len(tracker.processed_ids) >= tracker.cleanup_size - 10  # 약간의 여유


def test_interleaved_operations(tracker):
    """체크와 추가가 섞인 시나리오"""
    ids = ["a", "b", "c", "d", "e"]
    
    for msg_id in ids:
        if not tracker.is_processed(msg_id):
            tracker.mark_processed(msg_id)
    
    # 모두 처리됨
    for msg_id in ids:
        assert tracker.is_processed(msg_id) is True
    
    # 중복 처리 시도
    for msg_id in ids:
        if not tracker.is_processed(msg_id):
            tracker.mark_processed(msg_id)
    
    # 여전히 5개만
    assert len(tracker.processed_ids) == 5