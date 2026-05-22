import time
import uuid
import inspect
from functools import wraps
from datetime import datetime, timezone

from eval_factory.storage import save_run

# Safe, dynamic import of LangChain's get_openai_callback
try:
    from langchain_community.callbacks import get_openai_callback
except ImportError:
    try:
        from langchain.callbacks import get_openai_callback
    except ImportError:
        get_openai_callback = None

# Safe, dynamic import of LangChain's collect_runs tracer
try:
    from langchain_core.tracers.context import collect_runs
except ImportError:
    try:
        from langchain_core.callbacks.context import collect_runs
    except ImportError:
        try:
            from langchain_core.callbacks import collect_runs
        except ImportError:
            try:
                from langchain.callbacks import collect_runs
            except ImportError:
                collect_runs = None


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


def _extract_prompts_from_trace(traced_runs):
    """
    Recursively inspects execution runs to extract system and human prompts.
    Handles Pydantic/serialized dictionary messages and actual message objects safely.
    """
    system_prompts = []
    user_prompts = []

    def traverse(run):
        run_type = getattr(run, "run_type", None)
        
        # 1. Capture from prompt template runs (contains fully-rendered high-fidelity message objects)
        if run_type == "prompt":
            outputs = getattr(run, "outputs", {}) or {}
            for out_val in outputs.values():
                messages = getattr(out_val, "messages", [])
                for msg in messages:
                    m_type = getattr(msg, "type", None)
                    m_content = getattr(msg, "content", None)
                    if m_type == "system" and m_content:
                        system_prompts.append(m_content)
                    elif m_type in ("human", "user") and m_content:
                        user_prompts.append(m_content)

        # 2. Capture from LLM or Chat Model runs
        if run_type in ("llm", "chat_model"):
            inputs = getattr(run, "inputs", {}) or {}
            messages = inputs.get("messages", [])
            for msg_list in messages:
                for msg in msg_list:
                    # Parse serialized dictionary messages
                    if isinstance(msg, dict):
                        m_type = msg.get("type")
                        m_content = msg.get("content")
                        
                        # Fallback parsing for LangChain's LCEL serialization structures
                        # (e.g. type='constructor', id=['...', 'SystemMessage'], kwargs={'content': '...'})
                        if (not m_type or m_type not in ("system", "human")) and "id" in msg:
                            id_parts = msg.get("id", [])
                            if isinstance(id_parts, list) and len(id_parts) > 0:
                                last_part = id_parts[-1]
                                if "SystemMessage" in last_part:
                                    m_type = "system"
                                elif "HumanMessage" in last_part:
                                    m_type = "human"
                            # Also check if content is in kwargs
                            if not m_content and "kwargs" in msg:
                                m_content = msg.get("kwargs", {}).get("content")
                        
                        # Fallback for key role
                        if not m_type:
                            role = msg.get("role")
                            if role in ("system", "human", "user"):
                                m_type = "system" if role == "system" else "human"

                        if m_type == "system" and m_content:
                            system_prompts.append(m_content)
                        elif m_type in ("human", "user") and m_content:
                            user_prompts.append(m_content)
                    
                    # Parse actual BaseMessage objects
                    elif hasattr(msg, "type") and hasattr(msg, "content"):
                        m_type = getattr(msg, "type")
                        m_content = getattr(msg, "content")
                        if m_type == "system" and m_content:
                            system_prompts.append(m_content)
                        elif m_type in ("human", "user") and m_content:
                            user_prompts.append(m_content)
            
            # String prompts parsing fallback
            prompts = inputs.get("prompts", [])
            for p in prompts:
                if isinstance(p, str):
                    if "System: " in p:
                        parts = p.split("System: ", 1)
                        if len(parts) > 1:
                            subparts = parts[1].split("\nHuman: ", 1)
                            system_prompts.append(subparts[0].strip())
                            if len(subparts) > 1:
                                user_prompts.append(subparts[1].strip())

        # Traverse nested child runs
        for child in getattr(run, "child_runs", []):
            traverse(child)

    for run in traced_runs:
        traverse(run)

    # Deduplicate prompts while maintaining order
    return {
        "system_prompts": list(dict.fromkeys(system_prompts)),
        "user_prompts": list(dict.fromkeys(user_prompts))
    }



def capture_eval(
    dataset_name: str,
    input_extractor=None,
    output_extractor=None,
    base_dir: str = None,
    system_prompt: str = None
):
    """
    Decorator to capture prompt inputs, outputs, and metadata, writing them to a JSONL dataset.
    Automatically captures token usage/costs and system prompts from LangChain traces.

    Args:
        dataset_name: The name of the dataset/file (e.g. 'my_model_runs').
        input_extractor: Optional callable `func(args, kwargs)` to extract evaluation inputs.
        output_extractor: Optional callable `func(result)` to extract evaluation outputs.
        base_dir: Optional directory override where dataset files are stored.
        system_prompt: Optional manual override to declare the system prompt/context.
    """
    inp_ext = input_extractor or _default_input_extractor
    out_ext = output_extractor or _default_output_extractor

    def decorator(func):
        # Asynchronous function wrapper
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Capture inputs before execution
                try:
                    inputs = inp_ext(args, kwargs)
                except Exception as e:
                    inputs = f"<Input extraction failed: {str(e)}>"

                # Setup tracking context managers
                start_time = time.perf_counter()
                
                # Active context managers
                cb_data = None
                prompts_data = None
                
                # 1. Both get_openai_callback and collect_runs are available
                if get_openai_callback is not None and collect_runs is not None:
                    with get_openai_callback() as cb, collect_runs() as runs_cb:
                        result = await func(*args, **kwargs)
                        duration = time.perf_counter() - start_time
                        cb_data = {
                            "total_tokens": cb.total_tokens,
                            "prompt_tokens": cb.prompt_tokens,
                            "completion_tokens": cb.completion_tokens,
                            "total_cost": cb.total_cost,
                        }
                        prompts_data = _extract_prompts_from_trace(runs_cb.traced_runs)
                
                # 2. Only get_openai_callback is available
                elif get_openai_callback is not None:
                    with get_openai_callback() as cb:
                        result = await func(*args, **kwargs)
                        duration = time.perf_counter() - start_time
                        cb_data = {
                            "total_tokens": cb.total_tokens,
                            "prompt_tokens": cb.prompt_tokens,
                            "completion_tokens": cb.completion_tokens,
                            "total_cost": cb.total_cost,
                        }
                
                # 3. Only collect_runs is available
                elif collect_runs is not None:
                    with collect_runs() as runs_cb:
                        result = await func(*args, **kwargs)
                        duration = time.perf_counter() - start_time
                        prompts_data = _extract_prompts_from_trace(runs_cb.traced_runs)
                
                # 4. Neither is available
                else:
                    result = await func(*args, **kwargs)
                    duration = time.perf_counter() - start_time

                # Capture outputs
                try:
                    outputs = out_ext(result)
                except Exception as e:
                    outputs = f"<Output extraction failed: {str(e)}>"

                # Determine if inputs/outputs represent a batch execution of identical length
                is_batch = isinstance(inputs, list) and isinstance(outputs, list) and len(inputs) == len(outputs)
                num_items = len(inputs) if is_batch else 1

                # Construct record
                run_data = {
                    "run_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "inputs": inputs,
                    "outputs": outputs,
                    "metadata": {
                        "duration_seconds": duration,
                    },
                    "evaluation": [{"correct": None, "ground_truth": None} for _ in range(num_items)]
                }
                
                # Append callback tokens if captured
                if cb_data:
                    run_data["metadata"]["tokens"] = cb_data
                
                # Append system prompts (supporting trace and manual override)
                system_prompts_list = []
                if prompts_data and prompts_data["system_prompts"]:
                    system_prompts_list.extend(prompts_data["system_prompts"])
                if system_prompt and system_prompt not in system_prompts_list:
                    system_prompts_list.append(system_prompt)
                
                if system_prompts_list:
                    run_data["metadata"]["system_prompts"] = system_prompts_list

                # Append user prompts if captured
                if prompts_data and prompts_data["user_prompts"]:
                    run_data["metadata"]["user_prompts"] = prompts_data["user_prompts"]

                save_run(dataset_name, run_data, base_dir=base_dir)
                return result

            return async_wrapper

        # Synchronous function wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Capture inputs before execution
                try:
                    inputs = inp_ext(args, kwargs)
                except Exception as e:
                    inputs = f"<Input extraction failed: {str(e)}>"

                start_time = time.perf_counter()
                cb_data = None
                prompts_data = None

                # 1. Both managers available
                if get_openai_callback is not None and collect_runs is not None:
                    with get_openai_callback() as cb, collect_runs() as runs_cb:
                        result = func(*args, **kwargs)
                        duration = time.perf_counter() - start_time
                        cb_data = {
                            "total_tokens": cb.total_tokens,
                            "prompt_tokens": cb.prompt_tokens,
                            "completion_tokens": cb.completion_tokens,
                            "total_cost": cb.total_cost,
                        }
                        prompts_data = _extract_prompts_from_trace(runs_cb.traced_runs)

                # 2. Only get_openai_callback available
                elif get_openai_callback is not None:
                    with get_openai_callback() as cb:
                        result = func(*args, **kwargs)
                        duration = time.perf_counter() - start_time
                        cb_data = {
                            "total_tokens": cb.total_tokens,
                            "prompt_tokens": cb.prompt_tokens,
                            "completion_tokens": cb.completion_tokens,
                            "total_cost": cb.total_cost,
                        }

                # 3. Only collect_runs available
                elif collect_runs is not None:
                    with collect_runs() as runs_cb:
                        result = func(*args, **kwargs)
                        duration = time.perf_counter() - start_time
                        prompts_data = _extract_prompts_from_trace(runs_cb.traced_runs)

                # 4. Neither available
                else:
                    result = func(*args, **kwargs)
                    duration = time.perf_counter() - start_time

                # Capture outputs
                try:
                    outputs = out_ext(result)
                except Exception as e:
                    outputs = f"<Output extraction failed: {str(e)}>"

                # Determine if inputs/outputs represent a batch execution of identical length
                is_batch = isinstance(inputs, list) and isinstance(outputs, list) and len(inputs) == len(outputs)
                num_items = len(inputs) if is_batch else 1

                # Construct record
                run_data = {
                    "run_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "inputs": inputs,
                    "outputs": outputs,
                    "metadata": {
                        "duration_seconds": duration,
                    },
                    "evaluation": [{"correct": None, "ground_truth": None} for _ in range(num_items)]
                }

                if cb_data:
                    run_data["metadata"]["tokens"] = cb_data
                
                # Append system prompts (supporting trace and manual override)
                system_prompts_list = []
                if prompts_data and prompts_data["system_prompts"]:
                    system_prompts_list.extend(prompts_data["system_prompts"])
                if system_prompt and system_prompt not in system_prompts_list:
                    system_prompts_list.append(system_prompt)
                
                if system_prompts_list:
                    run_data["metadata"]["system_prompts"] = system_prompts_list

                # Append user prompts if captured
                if prompts_data and prompts_data["user_prompts"]:
                    run_data["metadata"]["user_prompts"] = prompts_data["user_prompts"]

                save_run(dataset_name, run_data, base_dir=base_dir)
                return result

            return sync_wrapper

    return decorator
