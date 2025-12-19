"""
로깅 설정
"""
import logging
import sys


def setup_logging():
    """
    애플리케이션 로깅 설정

    - Console handler 사용
    - stdout 출력
    - 포맷: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    """
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 기존 핸들러 제거 (중복 방지)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler 생성
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    root_logger.addHandler(console_handler)
