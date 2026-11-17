"""Tests for tools/gen_types.py (loaded by path; tools/ is not a package)."""

import importlib.util
from pathlib import Path

import pytest

_path = Path(__file__).resolve().parent.parent / "tools" / "gen_types.py"
_spec = importlib.util.spec_from_file_location("gen_types", _path)
gt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gt)


def render(schemas, paths=None):
    spec = {"components": {"schemas": schemas}, "paths": paths or {}}
    text, ops, _ = gt.generate(spec, "t")
    ns: dict = {}
    exec(compile(text, "t", "exec"), ns)  # noqa: S102 - generated code must import cleanly
    return text, ops, ns


def test_nullable_and_scalars():
    text, _, _ = render(
        {
            "A": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "nullable": True},
                    "b": {"type": ["string", "null"]},
                    "c": {"type": "number", "format": "decimal"},
                    "d": {"type": "array", "items": {"type": "boolean"}},
                    "e": {"type": "object", "additionalProperties": True},
                    "f": {},
                },
            }
        }
    )
    for line in ("a: int | None", "b: str | None", "c: float", "d: list[bool]"):
        assert line in text
    assert "e: dict[str, Any]" in text
    assert "f: Any" in text


def test_allof_merges_and_enum_comment():
    text, _, _ = render(
        {
            "Base": {"properties": {"id": {"type": "integer"}}},
            "Child": {
                "allOf": [
                    {"$ref": "#/components/schemas/Base"},
                    {"properties": {"n": {"type": "string"}}},
                ]
            },
            "Kind": {"type": "integer", "enum": [0, 1], "x-enumNames": ["Off", "On"]},
        }
    )
    child = text.split("class Child")[1].split("\n\n\n")[0]
    assert "id: int" in child
    assert "n: str" in child
    assert "type Kind = int  # 0=Off, 1=On" in text


def test_inline_object_and_self_reference():
    text, _, ns = render(
        {
            "Node": {
                "properties": {
                    "next": {"$ref": "#/components/schemas/Node"},
                    "meta": {"type": "object", "properties": {"k": {"type": "string"}}},
                    "items": {"type": "array", "items": {"properties": {"z": {"type": "integer"}}}},
                }
            }
        }
    )
    assert "next: Node" in text
    assert "meta: NodeMeta" in text
    assert "items: list[NodeItemsItem]" in text
    assert "NodeMeta" in ns


def test_non_identifier_keys_use_functional_form():
    text, _, ns = render(
        {
            "A": {"properties": {"from": {"type": "string"}, "x-y": {"type": "integer"}}},
            "B": {"properties": {"ok": {"type": "string"}}},
        }
    )
    assert 'A = TypedDict("A", {"from": "str", "x-y": "int"}, total=False)' in text
    assert "class B(TypedDict, total=False)" in text
    assert "A" in ns


def test_name_collisions_are_unique():
    text, _, _ = render(
        {"Foo": {"properties": {}}, "Foo.": {"properties": {}}, "Any": {"properties": {}}}
    )
    assert "class Foo(" in text
    assert "class Foo2(" in text
    assert "class Any2(" in text


def test_operations_selection():
    j = {"application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}}
    paths = {
        "/pets": {
            "get": {
                "operationId": "ListPets",
                "responses": {
                    "400": {"content": j},
                    "206": {"content": {"text/plain": {"schema": {"type": "string"}}}},
                    "200": {
                        "content": {
                            "text/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Pet"},
                                }
                            },
                            "application/xml": {"schema": {"type": "string"}},
                        }
                    },
                },
            },
            "post": {
                "operationId": "AddPet",
                "requestBody": {
                    "content": {
                        "application/json": {"schema": {"properties": {"n": {"type": "string"}}}}
                    }
                },
                "responses": {"201": {"content": j}},
            },
        },
        "/file": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/octet-stream": {
                                "schema": {"type": "string", "format": "binary"}
                            }
                        }
                    }
                }
            },
            "delete": {"responses": {"204": {"description": "gone"}}},
        },
        "/dir": {  # storage's shape: examples-only application/json, schema under */*
            "get": {
                "operationId": "ListDir",
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {"examples": {}},
                            "*/*": j["application/json"],
                        }
                    }
                },
            }
        },
    }
    text, ops, ns = render({"Pet": {"properties": {"id": {"type": "integer"}}}}, paths)
    assert ops["GET /pets"] == (None, "ListPetsResponse")
    assert "type ListPetsResponse = list[Pet]" in text
    assert ops["POST /pets"] == ("AddPetRequest", "Pet")
    assert "class AddPetRequest(" in text
    assert ops["GET /file"] == (None, None)
    assert ops["DELETE /file"] == (None, None)
    assert ops["GET /dir"] == (None, "Pet")
    assert ns["OPERATIONS"]["POST /pets"] == ("AddPetRequest", "Pet")


def test_docstring_escaping():
    assert gt.docstring('say "hi" \\ ' + "x" * 200).endswith("...")
    assert gt.docstring("  ") is None


@pytest.mark.parametrize("mod", gt.MODULES)
def test_generated_modules_import_and_are_current(mod):
    import importlib

    m = importlib.import_module(f"bunny_cdn_sdk.models.{mod}")
    text, ops, _ = gt.generate(gt.load(mod), mod)
    assert (gt.OUT / f"{mod}.py").read_text() == text
    assert set(m.OPERATIONS) == set(ops)
