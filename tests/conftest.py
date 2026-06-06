import os

# Import tips are opt-in during tests (avoid stderr noise in CI).
os.environ.setdefault("local_llm_router_IMPORT_TIPS", "off")
