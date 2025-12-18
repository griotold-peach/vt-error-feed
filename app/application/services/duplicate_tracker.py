# app/services/duplicate_tracker.py
"""
메시지 중복 처리 방지
"""
from typing import Set


class DuplicateTracker:
    """메시지 중복 처리 방지 및 메모리 관리"""
    
    def __init__(self, max_size: int = 1000, cleanup_size: int = 500):
        self.processed_ids: Set[str] = set()
        self.max_size = max_size
        self.cleanup_size = cleanup_size
    
    def is_processed(self, message_id: str) -> bool:
        """이미 처리한 메시지인지 확인"""
        return message_id in self.processed_ids
    
    def mark_processed(self, message_id: str):
        """메시지를 처리 완료로 표시"""
        self.processed_ids.add(message_id)
        self._cleanup_if_needed()
    
    def _cleanup_if_needed(self):
        """필요시 오래된 ID 정리"""
        if len(self.processed_ids) > self.max_size:
            to_remove = len(self.processed_ids) - self.cleanup_size
            for _ in range(to_remove):
                self.processed_ids.pop()
            
            print(f"🧹 Cleaned up processed_ids: {len(self.processed_ids)} remaining")
    
    def clear(self):
        """모든 기록 초기화"""
        self.processed_ids.clear()