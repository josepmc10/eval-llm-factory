import time
import uuid
import inspect
from functools import wraps
from datetime import datetime, timezone

from eval_factory.storage import save_run

try:
    from langchain_community.callbacks import get_openai_callback
except ImportError:
    try:
        from langchain.callbacks import get_openai_callback
    except ImportError:
        get_openai_callback = None


def _default_input_extractor(args, kwargs):
    """By default, extracts the first positional argument, or kwargs, or None."""
    if len(args) > 0:
        return args[0]
    if len(kwargs) > 0:
        return kwargs
    return None


def _default_output_extractor(result):
    """By default, extracts the exact return value."""
    return result


def capture_eval(
    dataset_name: str,
    input_extractor=None,
    output_extractor=None,
    base_dir: str = None
):
    """
    Decorator to capture prompt inputs, outputs, and metadata, writing them to a JSONL dataset.

    Args:
        dataset_name: The name of the dataset/file (e.g. 'my_model_runs').
        input_extractor: Optional callable `func(args, kwargs)` to extract evaluation inputs.
        output_extractor: Optional callable `func(result)` to extract evaluation outputs.
        base_dir: Optional directory override where dataset files are stored.
    """
    inp_ext = input_extractor or _default_input_extractor
    out_ext = output_extractor or _default_output_extractor

    def decorator(func):
        # Asynchronous function wrapper
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    inputs = inp_ext(args, kwargs)
                except Exception as e:
                    inputs = f"<Input extraction failed: {str(e)}>"

                start_time = time.perf_counter()
                if get_openai_callback is not None:
                    with get_openai_callback() as cb:
                        result = await func(*args, **kwargs)
                        duration = time.perf_counter() - start_time
                        cb_data = {
                            "total_tokens": cb.total_tokens,
                            "prompt_tokens": cb.prompt_tokens,
                            "completion_tokens": cb.completion_tokens,
                            "total_cost": cb.total_cost,
                        }
                else:
                    result = await func(*args, **kwargs)
                    duration = time.perf_counter() - start_time
                    cb_data = None

                try:
                    outputs = out_ext(result)
                except Exception as e:
                    outputs = f"<Output extraction failed: {str(e)}>"

                run_data = {
                    "run_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "inputs": inputs,
                    "outputs": outputs,
                    "metadata": {
                        "duration_seconds": duration,
                    }
                }
                if cb_data:
                    run_data["metadata"]["tokens"] = cb_data

                save_run(dataset_name, run_data, base_dir=base_dir)
                return result

            return async_wrapper

        # Synchronous function wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    inputs = inp_ext(args, kwargs)
                except Exception as e:
                    inputs = f"<Input extraction failed: {str(e)}>"

                start_time = time.perf_counter()
                if get_openai_callback is not None:
                    with get_openai_callback() as cb:
                        result = func(*args, **kwargs)
                        duration = time.perf_counter() - start_time
                        cb_data = {
                            "total_tokens": cb.total_tokens,
                            "prompt_tokens": cb.prompt_tokens,
                            "completion_tokens": cb.completion_tokens,
                            "total_cost": cb.total_cost,
                        }
                else:
                    result = func(*args, **kwargs)
                    duration = time.perf_counter() - start_time
                    cb_data = None

                try:
                    outputs = out_ext(result)
                except Exception as e:
                    outputs = f"<Output extraction failed: {str(e)}>"

                run_data = {
                    "run_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "inputs": inputs,
                    "outputs": outputs,
                    "metadata": {
                        "duration_seconds": duration,
                    }
                }
                if cb_data:
                    run_data["metadata"]["tokens"] = cb_data

                save_run(dataset_name, run_data, base_dir=base_dir)
                return result

            return sync_wrapper

    return decorator
