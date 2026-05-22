import os
import json
import asyncio
import pytest
from datetime import datetime
from eval_factory import config, capture_eval
import eval_factory.decorators as decorators

# Isolates the eval directory for each test run
@pytest.fixture(autouse=True)
def temp_eval_dir(tmp_path):
    original_base = config.base_dir
    config.base_dir = str(tmp_path)
    yield tmp_path
    config.base_dir = original_base


# Mock LangChain OpenAI Callback class
class MockOpenAICallback:
    def __init__(self):
        self.total_tokens = 150
        self.prompt_tokens = 100
        self.completion_tokens = 50
        self.total_cost = 0.0003

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_langchain_callback(monkeypatch):
    monkeypatch.setattr(decorators, "get_openai_callback", MockOpenAICallback)


# --- Tests for Synchronous Functions ---

def test_sync_decorator_defaults(temp_eval_dir):
    @capture_eval(dataset_name="sync_defaults")
    def my_sync_fn(prompt_input, optional_arg=None):
        return f"Response to: {prompt_input}"

    res = my_sync_fn("Hello Europe")
    assert res == "Response to: Hello Europe"

    dataset_file = os.path.join(str(temp_eval_dir), "sync_defaults.jsonl")
    assert os.path.exists(dataset_file)

    with open(dataset_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        
        assert "run_id" in record
        assert "timestamp" in record
        assert record["inputs"] == "Hello Europe"  # First positional argument by default
        assert record["outputs"] == "Response to: Hello Europe"
        assert "duration_seconds" in record["metadata"]


def test_sync_decorator_custom_extractors(temp_eval_dir):
    @capture_eval(
        dataset_name="sync_custom",
        input_extractor=lambda args, kwargs: kwargs.get("payload", "missing"),
        output_extractor=lambda res: res["answer"]
    )
    def my_sync_fn(dummy, payload=None):
        return {"answer": f"Processed: {payload}", "other": "ignored"}

    res = my_sync_fn(123, payload="Secret Data")
    assert res["answer"] == "Processed: Secret Data"

    dataset_file = os.path.join(str(temp_eval_dir), "sync_custom.jsonl")
    with open(dataset_file, "r") as f:
        record = json.loads(f.readline())
        assert record["inputs"] == "Secret Data"
        assert record["outputs"] == "Processed: Secret Data"


# --- Tests for Asynchronous Functions ---

@pytest.mark.asyncio
async def test_async_decorator_defaults(temp_eval_dir):
    @capture_eval(dataset_name="async_defaults")
    async def my_async_fn(prompt_input):
        await asyncio.sleep(0.01)
        return f"Async response to: {prompt_input}"

    res = await my_async_fn("Hello Async")
    assert res == "Async response to: Hello Async"

    dataset_file = os.path.join(str(temp_eval_dir), "async_defaults.jsonl")
    assert os.path.exists(dataset_file)

    with open(dataset_file, "r") as f:
        record = json.loads(f.readline())
        assert record["inputs"] == "Hello Async"
        assert record["outputs"] == "Async response to: Hello Async"
        assert "duration_seconds" in record["metadata"]


# --- Test Callback Capture (LangChain) ---

def test_langchain_callback_sync(temp_eval_dir, mock_langchain_callback):
    @capture_eval(dataset_name="callback_sync")
    def call_llm(prompt):
        return f"Output: {prompt}"

    call_llm("Calculate tokens")

    dataset_file = os.path.join(str(temp_eval_dir), "callback_sync.jsonl")
    with open(dataset_file, "r") as f:
        record = json.loads(f.readline())
        assert "tokens" in record["metadata"]
        tokens = record["metadata"]["tokens"]
        assert tokens["total_tokens"] == 150
        assert tokens["prompt_tokens"] == 100
        assert tokens["completion_tokens"] == 50
        assert tokens["total_cost"] == 0.0003
