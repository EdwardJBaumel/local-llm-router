import os

# Import tips are opt-in during tests (avoid stderr noise in CI).
os.environ.setdefault("SPLIT_STACK_IMPORT_TIPS", "off")
