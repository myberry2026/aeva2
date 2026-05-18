import inspect
import json
import re
import types
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints, Callable

# === 核心正则与基础类型 ===
BASIC_TYPES = (int, float, str, bool, Any, type(None), ...)
description_re = re.compile(r"^(.*?)[\n\s]*(Args:|Returns:|Raises:|\Z)", re.DOTALL)
args_re = re.compile(r"\n\s*Args:\n\s*(.*?)[\n\s]*(Returns:|Raises:|\Z)", re.DOTALL)
args_split_re = re.compile(
    r"""
(?:^|\n)  # Match the start of the args block, or a newline
\s*(\w+):\s*  # Capture the argument name and strip spacing
(.*?)\s*  # Capture the argument description, which can span multiple lines, and strip trailing spacing
(?=\n\s*\w+:|\Z)  # Stop when you hit the next argument or the end of the block
""",
    re.DOTALL | re.VERBOSE,
)
returns_re = re.compile(r"\n\s*Returns:\n\s*(.*?)[\n\s]*(Raises:|\Z)", re.DOTALL)

class TypeHintParsingException(Exception): pass
class DocstringParsingException(Exception): pass

def _get_json_schema_type(param_type: type) -> dict[str, str]:
    type_mapping = {
        int: {"type": "integer"},
        float: {"type": "number"},
        str: {"type": "string"},
        bool: {"type": "boolean"},
        type(None): {"type": "null"},
        Any: {},
    }
    return type_mapping.get(param_type, {"type": "object"})

def _parse_type_hint(hint: Any) -> dict:
    origin = get_origin(hint)
    args = get_args(hint)

    if origin is None:
        try:
            return _get_json_schema_type(hint)
        except Exception:
            raise TypeHintParsingException("Couldn't parse this type hint: ", hint)

    elif origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType):
        subtypes = [_parse_type_hint(t) for t in args if t is not type(None)]
        if len(subtypes) == 1:
            return_dict = subtypes[0]
        elif all("type" in subtype and isinstance(subtype["type"], str) for subtype in subtypes):
            return_dict = {"type": sorted([subtype["type"] for subtype in subtypes])}
        else:
            return_dict = {"anyOf": subtypes}
        if type(None) in args:
            return_dict["nullable"] = True
        return return_dict

    elif origin is Literal and len(args) > 0:
        LITERAL_TYPES = (int, float, str, bool, type(None))
        args_types = []
        for arg in args:
            if type(arg) not in LITERAL_TYPES:
                raise TypeHintParsingException("Only literals can be listed in typing.Literal.")
            arg_type = _get_json_schema_type(type(arg)).get("type")
            if arg_type is not None and arg_type not in args_types:
                args_types.append(arg_type)
        return {
            "type": args_types.pop() if len(args_types) == 1 else list(args_types),
            "enum": list(args),
        }

    elif origin is list or origin is list:
        if not args:
            return {"type": "array"}
        return {"type": "array", "items": _parse_type_hint(args[0])}

    elif origin is dict:
        out = {"type": "object"}
        if len(args) == 2:
            out["additionalProperties"] = _parse_type_hint(args[1])
        return out

    return {"type": "object"} # Fallback

def _convert_type_hints_to_json_schema(func: Callable) -> dict:
    try:
        type_hints = get_type_hints(func)
    except Exception:
        type_hints = {}
    
    signature = inspect.signature(func)
    func_name = getattr(func, "__name__", "operation")
    
    first_param_name = next(iter(signature.parameters), None)
    implicit_arg_name = first_param_name if first_param_name in {"self", "cls"} else None
    
    required = []
    properties = {}
    for param_name, param in signature.parameters.items():
        if param_name == implicit_arg_name:
            continue
        
        # Get type from hint or default value
        if param_name in type_hints:
            properties[param_name] = _parse_type_hint(type_hints[param_name])
        elif param.default != inspect.Parameter.empty and param.default is not None:
            properties[param_name] = _get_json_schema_type(type(param.default))
        else:
            properties[param_name] = {"type": "string"} # Default to string
            
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema

def parse_google_format_docstring(docstring: str) -> tuple[str | None, dict | None, str | None]:
    description_match = description_re.search(docstring)
    args_match = args_re.search(docstring)
    returns_match = returns_re.search(docstring)

    description = description_match.group(1).strip() if description_match else None
    docstring_args = args_match.group(1).strip() if args_match else None
    returns = returns_match.group(1).strip() if returns_match else None

    if docstring_args is not None:
        docstring_args = "\n".join([line for line in docstring_args.split("\n") if line.strip()])
        matches = args_split_re.findall(docstring_args)
        args_dict = {match[0]: re.sub(r"\s*\n+\s*", " ", match[1].strip()) for match in matches}
    else:
        args_dict = {}

    return description, args_dict, returns

def get_json_schema(func: Callable) -> dict:
    doc = inspect.getdoc(func)
    func_name = getattr(func, "__name__", "operation")

    if not doc:
        return {"type": "function", "function": {"name": func_name, "description": "", "parameters": {"type": "object", "properties": {}}}}
    
    doc = doc.strip()
    main_doc, param_descriptions, return_doc = parse_google_format_docstring(doc)

    json_schema = _convert_type_hints_to_json_schema(func)
    
    # Merge descriptions from docstring into schema
    for arg, schema in json_schema["properties"].items():
        desc = param_descriptions.get(arg, "")
        enum_choices = re.search(r"\(choices:\s*(.*?)\)\s*$", desc, flags=re.IGNORECASE)
        if enum_choices:
            try:
                schema["enum"] = [c.strip() for c in json.loads(enum_choices.group(1))]
                desc = enum_choices.string[: enum_choices.start()].strip()
            except Exception: pass
        schema["description"] = desc

    output = {"name": func_name, "description": main_doc or "", "parameters": json_schema}
    return {"type": "function", "function": output}
