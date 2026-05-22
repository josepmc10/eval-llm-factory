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
