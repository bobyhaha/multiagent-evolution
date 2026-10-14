"""Phase-specific strict output contracts and conservative, offline decoding.

The wire envelope expresses optional actions without ambiguous null/no-op fields.
It is translated to the existing action protocol only after complete validation.
No repair here calls a model, guesses an action, or bypasses runtime authorization.
"""

from copy import deepcopy
import json
import math


FORMAT = "actions-v1"
MAX_SCHEMA_BYTES = 24_000
WIRE_RULES = '''
OUTPUT ENCODING (actions-v1): Return one object with an actions array, for example
{"actions":[{"action":"memory","value":"evidence from this turn"}]}.
The observation's schema is an ACTION CATALOG, not the top-level output shape.
Choose only actions in that catalog, at most once each; omit unused actions.
Return {"actions":[]} for no actions. Never concatenate replies or simulate the
next turn. Every selected action uses the provider's typed value schema. Nested
optional fields listed in the provider schema must be present with null when
unused, even if the catalog describes them as optional or says to omit them.
A null action value is permitted only for
opening, recruitment_request or liaison and explicitly clears/cancels that item.
For tool.files use [{"path":"relative/path","content":"file text"}], not a
filename-keyed object. No duplicate actions, keys or file paths. JSON only.
The runtime validates the complete reply before executing actions. Tool results
arrive next turn; never invent them or include a simulated follow-up response.
'''

LEGACY_WIRE_RULES = '''
OUTPUT ENCODING (legacy): Return one JSON object with selected action names as
top-level keys, for example {"memory":"evidence from this turn"}. The observation's
schema lists optional actions. Omit unused actions and optional nested fields;
return {} for no actions. The tool action uses the top-level "tool" key and
tool.files is a filename-keyed object. No prose, fences, duplicate keys or extra
objects. Never simulate a subsequent turn or tool result.
'''

# Nested optional fields are explicit nulls on the strict wire and omitted in
# the internal protocol. Required fields are never silently filled or guessed.
OPTIONAL = {
    "proposal": {"task_id"}, "offer": {"task_id"},
    "opening": {"candidate", "trial"},
    "recruitment_request": {"candidate", "trial"},
    "decisions": {"introduce_to", "renewal"},
    "tool": {"command", "path", "start", "lines", "base_sha256", "content",
             "old", "new", "args", "stdin", "files", "capture"},
    "inspect": {"path", "start"},
    "tasks": {"status", "feedback"},
}
CLEAR = {"opening", "recruitment_request", "liaison"}


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def typed(example, path=()):
    """Compile the host's finite phase catalog; never infer from model replies."""
    key = path[-1] if path else ""
    if key == "files":
        return {"type": "array", "items": typed({"path": "", "content": ""}, ("file",))}
    if isinstance(example, dict):
        properties = {k: typed(v, (*path, k)) for k, v in example.items()}
        for name in OPTIONAL.get(key, set()) & properties.keys():
            properties[name] = nullable(properties[name])
        return {"type": "object", "properties": properties, "required": list(properties),
                "additionalProperties": False}
    if isinstance(example, list):
        return {"type": "array", "items": typed(example[0], path) if example else {"type": "string"}}
    if type(example) is bool:
        return {"type": "boolean"}
    if type(example) is int or (len(path) >= 2 and path[-2] == "renewal"):
        return {"type": "integer"}
    if isinstance(example, str):
        result = {"type": "string"}
        if "|" in example and all(part.isidentifier() for part in example.split("|")):
            result["enum"] = example.split("|")
        return result
    raise ValueError("Unsupported host action catalog")


def reply_schema(catalog):
    cases = []
    for name, example in catalog.items():
        value = typed(example, (name,))
        if name in CLEAR:
            value = nullable(value)
        cases.append({"type": "object", "properties": {
            "action": {"type": "string", "enum": [name]}, "value": value},
            "required": ["action", "value"], "additionalProperties": False})
    if not cases:
        raise ValueError("Empty host action catalog")
    result = {"type": "object", "properties": {
        "actions": {"type": "array", "items": {"anyOf": cases}}},
        "required": ["actions"], "additionalProperties": False}
    if len(json.dumps(result).encode()) > MAX_SCHEMA_BYTES:
        raise ValueError("Structured reply schema exceeds fixed bound")
    return result


def observation(messages):
    if not messages or messages[-1].get("role") != "user":
        return {}
    try:
        result = json.loads(messages[-1]["content"])
        return result if isinstance(result, dict) else {}
    except (ValueError, TypeError):
        return {}


def response_format(messages):
    obs = observation(messages)
    if obs.get("reply_format") != FORMAT:
        return None
    return {"type": "json_schema", "json_schema": {
        "name": "colony_" + obs["phase"], "strict": True,
        "schema": reply_schema(obs["schema"])}}


def validate(value, schema, path="reply"):
    """Validate the complete supported schema subset, with exact JSON types."""
    if "anyOf" in schema:
        options = schema["anyOf"]
        # Select the named action first, so an invalid value reports its actual
        # field rather than losing the error among unrelated action alternatives.
        if all("action" in option.get("properties", {}) for option in options):
            if type(value) is not dict:
                raise ValueError(path + " must be object")
            for option in options:
                if value.get("action") in option["properties"]["action"]["enum"]:
                    return validate(value, option, path)
            raise ValueError(path + ".action must name an action in this phase's catalog")
        nonnull = [option for option in options if option.get("type") != "null"]
        if value is not None and len(nonnull) == 1 and len(nonnull) < len(options):
            return validate(value, nonnull[0], path)
        for option in options:
            try:
                validate(value, option, path)
                return
            except ValueError:
                pass
        raise ValueError(path + " does not match an allowed action/type")
    kind = schema["type"]
    types = {"object": dict, "array": list, "string": str, "integer": int,
             "boolean": bool, "null": type(None)}
    if type(value) is not types[kind]:
        raise ValueError(path + " must be " + kind)
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(path + " has an invalid enum value")
    if kind == "object":
        missing = set(schema["properties"]) - set(value)
        if missing:
            raise ValueError(path + "." + sorted(missing)[0] + " is required")
        unexpected = set(value) - set(schema["properties"])
        if unexpected:
            raise ValueError(path + "." + sorted(unexpected)[0] + " is not allowed")
        for key, item in value.items():
            validate(item, schema["properties"][key], path + "." + key)
    elif kind == "array":
        for index, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{index}]")


def normalize(value, key=""):
    if isinstance(value, dict):
        return {k: normalize(v, k) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        if key == "files":
            files = {}
            for row in value:
                if row["path"] in files:
                    raise ValueError("Duplicate tool file path")
                files[row["path"]] = row["content"]
            return files
        return [normalize(v) for v in value]
    return value


def actions(reply, catalog):
    validate(reply, reply_schema(catalog))
    result = {}
    for row in reply["actions"]:
        name = row["action"]
        if name in result:
            raise ValueError("Duplicate action: " + name)
        result[name] = normalize(row["value"], name)
    return result


def flat_to_wire(reply, catalog):
    """Validate legacy recoveries using the same phase schema; no new actions."""
    def fill(value, key):
        if value is None:
            return None
        if key == "files" and isinstance(value, dict):
            return [{"path": p, "content": c} for p, c in value.items()]
        if isinstance(value, dict):
            result = {k: fill(v, k) for k, v in value.items()}
            for field in OPTIONAL.get(key, set()) & set(catalog_fields(key, catalog)):
                result.setdefault(field, None)
            return result
        if isinstance(value, list):
            return [fill(v, key) for v in value]
        return value
    if not isinstance(reply, dict) or set(reply) - set(catalog):
        raise ValueError("Unexpected decision fields")
    return {"actions": [{"action": k, "value": fill(v, k)} for k, v in reply.items()]}


def catalog_fields(key, catalog):
    example = catalog.get(key, {})
    if isinstance(example, list):
        example = example[0] if example else {}
    return example if isinstance(example, dict) else {}


def decode(text, max_bytes):
    """Only recover a single nonempty object accompanied by empty objects."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > max_bytes:
        raise ValueError("Nontext or oversized reply")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def number(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Nonfinite JSON number")
        return result
    decoder = json.JSONDecoder(object_pairs_hook=pairs, parse_constant=number, parse_float=number)
    remaining, objects = text.strip(), []
    while remaining:
        if len(objects) == 4:
            raise ValueError("Too many concatenated objects")
        item, end = decoder.raw_decode(remaining)
        if not isinstance(item, dict):
            raise ValueError("Reply must be an object")
        objects.append(item)
        remaining = remaining[end:].lstrip()
    if len(objects) == 1:
        return objects[0], False
    nonempty = [obj for obj in objects if obj]
    if len(nonempty) != 1:
        raise ValueError("Ambiguous multiple JSON objects")
    return deepcopy(nonempty[0]), True
