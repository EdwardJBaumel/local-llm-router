import os
import sys
from pathlib import Path

# Ensure src/ is importable even when a stale split-stack editable install shadows paths.
_root = Path(__file__).resolve().parent.parent
_src = _root / "src"
_src_str = str(_src)
if _src_str not in sys.path:
    sys.path.insert(0, _src_str)

# Import tips are opt-in during tests (avoid stderr noise in CI).
os.environ.setdefault("local_llm_router_IMPORT_TIPS", "off")
