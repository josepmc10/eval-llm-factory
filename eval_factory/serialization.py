import json
import dataclasses
from datetime import datetime, date
from uuid import UUID

class RobustEncoder(json.JSONEncoder):
    """
    A robust JSON encoder that handles datetimes, dates, UUIDs, dataclasses,
    Pydantic models (v1 and v2), and LangChain messages gracefully without ever
    crashing on un-serializable objects.
    """
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()

        if isinstance(obj, UUID):
            return str(obj)

        if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
            try:
                return obj.model_dump()
            except Exception:
                pass
        if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
            try:
                return obj.dict()
            except Exception:
                pass

        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)

        if hasattr(obj, "content") and hasattr(obj, "type"):
            return {
                "type": getattr(obj, "type"),
                "content": getattr(obj, "content"),
                "additional_kwargs": getattr(obj, "additional_kwargs", {}),
                "response_metadata": getattr(obj, "response_metadata", {})
            }

        if isinstance(obj, (set, range)) or hasattr(obj, "__iter__") and not isinstance(obj, (str, dict, list, tuple)):
            try:
                return list(obj)
            except Exception:
                pass

        if hasattr(obj, "__dict__"):
            try:
                # Extract all non-private attributes
                return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
            except Exception:
                pass

        try:
            return super().default(obj)
        except TypeError:
            try:
                return str(obj)
            except Exception:
                return repr(obj)


def serialize_data(data) -> str:
    """Helper to convert any Python object into a JSON string using RobustEncoder."""
    return json.dumps(data, cls=RobustEncoder)
