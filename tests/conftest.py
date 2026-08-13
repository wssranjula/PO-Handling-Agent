import os

# Unit tests should never send document fixtures or fake model calls to LangSmith.
os.environ["LANGSMITH_TRACING"] = "false"
