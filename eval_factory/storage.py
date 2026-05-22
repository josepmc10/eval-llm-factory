import os
import json
from eval_factory.config import config
from eval_factory.serialization import RobustEncoder

def save_run(dataset_name: str, run_data: dict, base_dir: str = None):
    """
    Appends a run record as a single JSON line to the target dataset file.

    Args:
        dataset_name: Name of the dataset (e.g. 'my_pipeline').
        run_data: Dict containing run information (run_id, timestamp, inputs, outputs, metadata).
        base_dir: Optional override for the target directory.
    """
    target_dir = base_dir or config.base_dir
    os.makedirs(target_dir, exist_ok=True)

    # Sanitize the dataset name to prevent directory traversal or bad filenames
    safe_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in dataset_name])
    file_path = os.path.join(target_dir, f"{safe_name}.jsonl")

    # Serialize using the RobustEncoder
    line = json.dumps(run_data, cls=RobustEncoder)

    # Append to the file
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def update_run(
    dataset_name: str,
    run_id: str,
    evaluation_update: dict,
    item_index: int = 0,
    base_dir: str = None
) -> bool:
    """
    Locates a run by its UUID inside the dataset file and updates its evaluation data.
    Supports pair-wise indexing and dynamic legacy dictionary to list migration.
    Uses atomic file swapping to prevent data loss or file corruption.

    Args:
        dataset_name: The name of the dataset.
        run_id: The UUID string of the run to update.
        evaluation_update: Dict containing update fields (e.g. {'correct': True, 'ground_truth': '...'})
        item_index: The specific input/output pair index to update (defaults to 0).
        base_dir: Optional base directory override.

    Returns:
        bool: True if the run was found and updated, False otherwise.
    """
    import tempfile

    target_dir = base_dir or config.base_dir
    safe_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in dataset_name])
    file_path = os.path.join(target_dir, f"{safe_name}.jsonl")

    if not os.path.exists(file_path):
        return False

    updated = False
    temp_fd, temp_path = tempfile.mkstemp(dir=target_dir, suffix=".tmp")

    try:
        with open(file_path, "r", encoding="utf-8") as rf, \
             os.fdopen(temp_fd, "w", encoding="utf-8") as wf:
            for line in rf:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if record.get("run_id") == run_id:
                        # Normalize evaluation to a list
                        eval_block = record.get("evaluation")
                        if not isinstance(eval_block, list):
                            inputs = record.get("inputs")
                            outputs = record.get("outputs")
                            is_batch = isinstance(inputs, list) and isinstance(outputs, list) and len(inputs) == len(outputs)
                            num_items = len(inputs) if is_batch else 1
                            
                            if isinstance(eval_block, dict):
                                record["evaluation"] = [eval_block] + [{"correct": None, "ground_truth": None} for _ in range(num_items - 1)]
                            else:
                                record["evaluation"] = [{"correct": None, "ground_truth": None} for _ in range(num_items)]

                        # Defensive padding to ensure item_index is within bounds
                        while len(record["evaluation"]) <= item_index:
                            record["evaluation"].append({"correct": None, "ground_truth": None})

                        # Update specific evaluation fields for the targeted pair index
                        target_item = record["evaluation"][item_index]
                        if not isinstance(target_item, dict):
                            target_item = {"correct": None, "ground_truth": None}
                            record["evaluation"][item_index] = target_item

                        for k, v in evaluation_update.items():
                            target_item[k] = v

                        updated = True

                    wf.write(json.dumps(record, cls=RobustEncoder) + "\n")
                except Exception:
                    # Fallback to write back original line if corrupt
                    wf.write(line)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e

    if updated:
        # Atomic swap: remove original and rename temp
        # Windows requires removing the destination first if using os.rename
        if os.path.exists(file_path):
            os.remove(file_path)
        os.rename(temp_path, file_path)
        return True
    else:
        # No updates done, discard temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False
