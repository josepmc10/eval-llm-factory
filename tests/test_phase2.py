import os
import json
import pytest
from eval_factory import config, save_run, update_run
from eval_factory.decorators import _extract_prompts_from_trace

# --- Fixtures ---

@pytest.fixture(autouse=True)
def temp_eval_dir(tmp_path):
    original_base = config.base_dir
    config.base_dir = str(tmp_path)
    yield tmp_path
    config.base_dir = original_base


# --- Mock classes for LangChain Runs ---

class MockRunMessage:
    def __init__(self, msg_type, content):
        self.type = msg_type
        self.content = content


class MockRun:
    def __init__(self, run_type, inputs, child_runs=None):
        self.run_type = run_type
        self.inputs = inputs
        self.child_runs = child_runs or []


# --- Tests ---

def test_extract_prompts_from_trace_dict_format():
    # Simulate a serialized dictionary trace structure
    llm_run = MockRun(
        run_type="llm",
        inputs={
            "messages": [
                [
                    {"type": "system", "content": "System directive A"},
                    {"type": "human", "content": "User input text"}
                ]
            ]
        }
    )
    parent_chain = MockRun(
        run_type="chain",
        inputs={},
        child_runs=[llm_run]
    )

    extracted = _extract_prompts_from_trace([parent_chain])
    assert extracted["system_prompts"] == ["System directive A"]
    assert extracted["user_prompts"] == ["User input text"]


def test_extract_prompts_from_trace_object_format():
    # Simulate a raw BaseMessage object trace structure
    sys_msg = MockRunMessage("system", "System directive B")
    human_msg = MockRunMessage("human", "User query B")
    
    llm_run = MockRun(
        run_type="chat_model",
        inputs={
            "messages": [[sys_msg, human_msg]]
        }
    )

    extracted = _extract_prompts_from_trace([llm_run])
    assert extracted["system_prompts"] == ["System directive B"]
    assert extracted["user_prompts"] == ["User query B"]


class MockPromptOutput:
    def __init__(self, messages):
        self.messages = messages


def test_extract_prompts_from_trace_prompt_run():
    sys_msg = MockRunMessage("system", "Prompt System Msg")
    human_msg = MockRunMessage("human", "Prompt Human Msg")
    prompt_run = MockRun(
        run_type="prompt",
        inputs={},
        child_runs=[]
    )
    prompt_run.outputs = {"output": MockPromptOutput([sys_msg, human_msg])}
    
    parent_chain = MockRun(
        run_type="chain",
        inputs={},
        child_runs=[prompt_run]
    )
    
    extracted = _extract_prompts_from_trace([parent_chain])
    assert extracted["system_prompts"] == ["Prompt System Msg"]
    assert extracted["user_prompts"] == ["Prompt Human Msg"]


def test_extract_prompts_from_trace_string_fallback():
    llm_run = MockRun(
        run_type="llm",
        inputs={
            "prompts": ["System: Helper Directive\nHuman: User Question Details"]
        }
    )
    extracted = _extract_prompts_from_trace([llm_run])
    assert extracted["system_prompts"] == ["Helper Directive"]
    assert extracted["user_prompts"] == ["User Question Details"]


def test_update_run_evaluation(temp_eval_dir):
    dataset_name = "test_updater"
    
    run_1 = {
        "run_id": "uuid-1111",
        "timestamp": "2026-05-22T12:00:00Z",
        "inputs": "Input A",
        "outputs": "Output A",
        "evaluation": {"correct": None, "ground_truth": None}
    }
    run_2 = {
        "run_id": "uuid-2222",
        "timestamp": "2026-05-22T12:05:00Z",
        "inputs": "Input B",
        "outputs": "Output B",
        "evaluation": {"correct": None, "ground_truth": None}
    }

    # Save initial runs
    save_run(dataset_name, run_1)
    save_run(dataset_name, run_2)

    # Verify initial save
    dataset_file = os.path.join(str(temp_eval_dir), "test_updater.jsonl")
    assert os.path.exists(dataset_file)

    # Perform updates
    success = update_run(
        dataset_name=dataset_name,
        run_id="uuid-2222",
        evaluation_update={"correct": True, "ground_truth": "Expected Output B"}
    )
    
    assert success is True

    # Read back and assert updates
    with open(dataset_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 2
        
        parsed_1 = json.loads(lines[0])
        parsed_2 = json.loads(lines[1])

        # Run 1 should be completely untouched
        assert parsed_1["run_id"] == "uuid-1111"
        assert parsed_1["evaluation"]["correct"] is None
        assert parsed_1["evaluation"]["ground_truth"] is None

        # Run 2 should be correctly updated and migrated to list evaluation format
        assert parsed_2["run_id"] == "uuid-2222"
        assert isinstance(parsed_2["evaluation"], list)
        assert parsed_2["evaluation"][0]["correct"] is True
        assert parsed_2["evaluation"][0]["ground_truth"] == "Expected Output B"


def test_update_run_not_found(temp_eval_dir):
    dataset_name = "test_not_found"
    run_1 = {
        "run_id": "uuid-1111",
        "inputs": "Input A",
        "outputs": "Output A",
    }
    save_run(dataset_name, run_1)

    # Attempt to update non-existent UUID
    success = update_run(
        dataset_name=dataset_name,
        run_id="uuid-does-not-exist",
        evaluation_update={"correct": True}
    )
    
    assert success is False


def test_decorators_batch_capture(temp_eval_dir):
    # Verify that capture_eval decorator correctly detects a batch execution
    # and initializes evaluation as a list matching the length of inputs/outputs
    from eval_factory import capture_eval
    
    @capture_eval(dataset_name="test_batch_decorator")
    def my_batch_func(inputs):
        return [f"Output for {inp}" for inp in inputs]
        
    my_batch_func(["apple", "banana", "cherry"])
    
    # Read the saved run
    dataset_file = os.path.join(str(temp_eval_dir), "test_batch_decorator.jsonl")
    assert os.path.exists(dataset_file)
    
    with open(dataset_file, "r", encoding="utf-8") as f:
        line = f.readline()
        record = json.loads(line)
        
        assert record["inputs"] == ["apple", "banana", "cherry"]
        assert record["outputs"] == ["Output for apple", "Output for banana", "Output for cherry"]
        assert isinstance(record["evaluation"], list)
        assert len(record["evaluation"]) == 3
        for item in record["evaluation"]:
            assert item["correct"] is None
            assert item["ground_truth"] is None


def test_update_run_index_based(temp_eval_dir):
    # Verify that updating a specific index in a batch evaluation updates only that index
    dataset_name = "test_batch_update"
    run = {
        "run_id": "uuid-batch",
        "inputs": ["A", "B", "C"],
        "outputs": ["outA", "outB", "outC"],
        "evaluation": [
            {"correct": None, "ground_truth": None},
            {"correct": None, "ground_truth": None},
            {"correct": None, "ground_truth": None}
        ]
    }
    save_run(dataset_name, run)
    
    # Update index 1
    success = update_run(
        dataset_name=dataset_name,
        run_id="uuid-batch",
        item_index=1,
        evaluation_update={"correct": True, "ground_truth": "Expected B"}
    )
    assert success is True
    
    # Verify the file
    dataset_file = os.path.join(str(temp_eval_dir), "test_batch_update.jsonl")
    with open(dataset_file, "r", encoding="utf-8") as f:
        record = json.loads(f.readline())
        evals = record["evaluation"]
        assert len(evals) == 3
        
        # Index 0 should be untouched
        assert evals[0]["correct"] is None
        assert evals[0]["ground_truth"] is None
        
        # Index 1 should be updated
        assert evals[1]["correct"] is True
        assert evals[1]["ground_truth"] == "Expected B"
        
        # Index 2 should be untouched
        assert evals[2]["correct"] is None
        assert evals[2]["ground_truth"] is None


def test_update_run_backward_compatibility(temp_eval_dir):
    # Verify that a legacy run with a dictionary evaluation block is successfully 
    # migrated to a list on-the-fly when calling update_run
    dataset_name = "test_legacy_compat"
    run = {
        "run_id": "uuid-legacy",
        "inputs": ["A", "B"],
        "outputs": ["outA", "outB"],
        "evaluation": {"correct": True, "ground_truth": "Expected Legacy"}
    }
    save_run(dataset_name, run)
    
    # Update index 1 of the legacy run
    success = update_run(
        dataset_name=dataset_name,
        run_id="uuid-legacy",
        item_index=1,
        evaluation_update={"correct": False, "ground_truth": "Expected B"}
    )
    assert success is True
    
    # Verify migration and update
    dataset_file = os.path.join(str(temp_eval_dir), "test_legacy_compat.jsonl")
    with open(dataset_file, "r", encoding="utf-8") as f:
        record = json.loads(f.readline())
        evals = record["evaluation"]
        
        # Should be migrated to a list of length 2
        assert isinstance(evals, list)
        assert len(evals) == 2
        
        # Index 0 should preserve legacy data
        assert evals[0]["correct"] is True
        assert evals[0]["ground_truth"] == "Expected Legacy"
        
        # Index 1 should be updated
        assert evals[1]["correct"] is False
        assert evals[1]["ground_truth"] == "Expected B"
