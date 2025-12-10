# tests/conftest.py
import os
import sys

# 프로젝트 루트 경로를 계산해서 sys.path 맨 앞에 넣어준다.
# 이러면 어디서 pytest를 실행해도 'app' 패키지를 안정적으로 import 할 수 있다.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
