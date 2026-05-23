import json
from datetime import datetime, date, timezone
from uuid import UUID, uuid4
import pytest
from eval_factory.serialization import RobustEncoder, serialize_data

# Dummy Pydantic-like v2 model
class DummyPydanticV2:
    def model_dump(self):
        return {"a": 1, "b": "hello"}

# Dummy Pydantic-like v1 model
class DummyPydanticV1:
    def dict(self):
        return {"x": 10, "y": "world"}

# Dummy LangChain Message
class DummyLCMessage:
    def __init__(self, msg_type, content):
        self.type = msg_type
        self.content = content
        self.additional_kwargs = {"key": "val"}
        self.response_metadata = {"meta": "data"}

# Dummy Custom Class
class CustomObject:
    def __init__(self):
        self.name = "Josep"
        self._private = "secret"

# Unserializable class (raises TypeError on str, etc. and has no __dict__)
class ExtremelyBadObject:
    __slots__ = []
    def __str__(self):
        raise ValueError("Cannot stringify")
    def __repr__(self):
        return "ExtremelyBadObjectRepr"


def test_serialize_standard_types():
    data = {"str": "abc", "int": 123, "float": 45.6, "bool": True, "none": None}
    serialized = serialize_data(data)
    decoded = json.loads(serialized)
    assert decoded == data


def test_serialize_dates_and_times():
    dt = datetime(2026, 5, 22, 12, 34, 56, tzinfo=timezone.utc)
    d = date(2026, 5, 22)
    data = {"datetime": dt, "date": d}
    serialized = serialize_data(data)
    decoded = json.loads(serialized)
    assert decoded["datetime"] == "2026-05-22T12:34:56+00:00"
    assert decoded["date"] == "2026-05-22"


def test_serialize_uuid():
    uid = uuid4()
    data = {"uuid": uid}
    serialized = serialize_data(data)
    decoded = json.loads(serialized)
    assert decoded["uuid"] == str(uid)


def test_serialize_pydantic_models():
    data = {
        "v2": DummyPydanticV2(),
        "v1": DummyPydanticV1()
    }
    serialized = serialize_data(data)
    decoded = json.loads(serialized)
    assert decoded["v2"] == {"a": 1, "b": "hello"}
    assert decoded["v1"] == {"x": 10, "y": "world"}


def test_serialize_langchain_messages():
    msg = DummyLCMessage("ai", "Hello AI World")
    serialized = serialize_data({"msg": msg})
    decoded = json.loads(serialized)
    assert decoded["msg"]["type"] == "ai"
    assert decoded["msg"]["content"] == "Hello AI World"
    assert decoded["msg"]["additional_kwargs"] == {"key": "val"}
    assert decoded["msg"]["response_metadata"] == {"meta": "data"}


def test_serialize_iterables_and_custom_classes():
    custom = CustomObject()
    data = {
        "set": {1, 2, 3},
        "custom": custom,
        "generator": (i for i in range(3))
    }
    serialized = serialize_data(data)
    decoded = json.loads(serialized)
    assert set(decoded["set"]) == {1, 2, 3}
    assert decoded["custom"] == {"name": "Josep"}  # _private should be ignored
    assert decoded["generator"] == [0, 1, 2]


def test_serialize_fallback_unserializable():
    bad = ExtremelyBadObject()
    serialized = serialize_data({"bad": bad})
    decoded = json.loads(serialized)
    # Since __str__ raises an error, fallback to __repr__
    assert decoded["bad"] == "ExtremelyBadObjectRepr"
