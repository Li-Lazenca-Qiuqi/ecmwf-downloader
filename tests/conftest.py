"""为当前应用包提供源码导入路径，测试标记统一由 pyproject.toml 配置。"""

import sys
from pathlib import Path

source_root = str(Path(__file__).resolve().parents[1] / "src")
if source_root not in sys.path:
    sys.path.insert(0, source_root)
