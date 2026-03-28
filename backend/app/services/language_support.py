from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.schemas.problem import RuntimeShape, TestCaseCreate


SUPPORTED_LANGUAGES = ("python", "javascript", "java", "cpp")
COMMON_PARAMETER_NAMES = [
    "head",
    "root",
    "list1",
    "list2",
    "nums",
    "target",
    "n",
    "k",
    "s",
    "t",
    "word1",
    "word2",
    "grid",
    "matrix",
    "intervals",
    "points",
    "prices",
]
IDENTIFIER_STOPWORDS = {
    "overview",
    "example",
    "examples",
    "constraint",
    "constraints",
    "input",
    "output",
    "explanation",
    "return",
    "returns",
    "given",
    "list",
    "lists",
    "linked",
    "node",
    "nodes",
    "value",
    "values",
    "array",
    "arrays",
    "string",
    "strings",
    "integer",
    "integers",
    "tree",
    "graph",
    "pattern",
    "practice",
    "version",
    "python",
    "java",
    "javascript",
    "cpp",
    "c",
}


@dataclass(frozen=True)
class TypeSpec:
    kind: str
    item: TypeSpec | None = None


def escape_regexp(value: str) -> str:
    return re.escape(value)


def infer_runtime_shape(topic: str, description: str, starter_code: str = "") -> RuntimeShape:
    normalized = " ".join([topic, description, starter_code]).strip().lower().replace("-", " ")
    if "random" in normalized and "linked list" in normalized:
        return "random_pointer_linked_list"
    if "linked list" in normalized:
        return "linked_list"
    return "plain"


def detect_unsupported_problem_shape(topic: str, description: str, starter_code: str = "") -> str | None:
    normalized = " ".join([topic, description, starter_code]).strip().lower().replace("-", " ")
    if "random" in normalized and "linked list" in normalized:
        return None
    if "linked list" in normalized:
        return None
    if "binary tree" in normalized or "binary search tree" in normalized or "treenode" in normalized:
        return "Binary tree problems are not supported yet. The app currently supports plain problems, linked lists, and random-pointer linked lists."
    if "n ary tree" in normalized or "n-ary tree" in normalized:
        return "N-ary tree problems are not supported yet. The app currently supports plain problems, linked lists, and random-pointer linked lists."
    if "graph" in normalized or "adjacency list" in normalized or "adjacency matrix" in normalized:
        return "Graph problems are not supported yet. The app currently supports plain problems, linked lists, and random-pointer linked lists."
    if "trie" in normalized:
        return "Trie problems are not supported yet. The app currently supports plain problems, linked lists, and random-pointer linked lists."
    return None


def is_linked_list_runtime_shape(runtime_shape: RuntimeShape) -> bool:
    return runtime_shape in {"linked_list", "random_pointer_linked_list"}


def is_random_pointer_runtime_shape(runtime_shape: RuntimeShape) -> bool:
    return runtime_shape == "random_pointer_linked_list"


def extract_parameter_names(
    starter_code: str,
    function_name: str,
    topic: str = "",
    runtime_shape: RuntimeShape | None = None,
) -> list[str]:
    resolved_shape = runtime_shape or infer_runtime_shape(topic, starter_code, starter_code)
    signature_pattern = re.compile(rf"def\s+{escape_regexp(function_name)}\s*\(([^)]*)\)")
    signature_match = signature_pattern.search(starter_code)

    if signature_match is None:
        if is_linked_list_runtime_shape(resolved_shape):
            return ["head"]
        return []

    names = [
        raw_param.replace("=", " ").replace(":", " ").split()[0].strip()
        for raw_param in signature_match.group(1).split(",")
        if raw_param.strip()
    ]
    names = [name for name in names if name not in {"self", "cls", "/", "*"}]

    if is_linked_list_runtime_shape(resolved_shape) and len(names) == 1:
        return ["head"]

    return names


def _input_arity(test_cases: list[TestCaseCreate]) -> int:
    if not test_cases:
        return 0

    first_input = test_cases[0].input
    if isinstance(first_input, list):
        return len(first_input)
    if isinstance(first_input, dict):
        return len(first_input)
    return 1


def _extract_names_from_description(description: str) -> list[str]:
    candidates: list[str] = []

    for match in re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=", description):
        candidates.append(match.group(1))

    for match in re.finditer(r"`([a-zA-Z_][a-zA-Z0-9_]*)`", description):
        candidates.append(match.group(1))

    seen: set[str] = set()
    filtered: list[str] = []
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in IDENTIFIER_STOPWORDS:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        filtered.append(normalized)

    return filtered


def _fallback_parameter_names(topic: str, arg_count: int, description: str) -> list[str]:
    if arg_count <= 0:
        return []

    description_names = {name.lower() for name in _extract_names_from_description(description)}

    runtime_shape = infer_runtime_shape(topic, description)

    if is_linked_list_runtime_shape(runtime_shape):
        if {"list1", "list2"}.issubset(description_names):
            return ["list1", "list2"][:arg_count]
        if "head" in description_names and "n" in description_names:
            return ["head", "n"][:arg_count]
        if "head" in description_names and "k" in description_names:
            return ["head", "k"][:arg_count]
        if arg_count == 1:
            return ["head"]

    fallback: list[str] = []
    for name in COMMON_PARAMETER_NAMES:
        if name in description_names and name not in fallback:
            fallback.append(name)
        if len(fallback) == arg_count:
            return fallback

    for index in range(arg_count):
        preferred = "head" if is_linked_list_runtime_shape(runtime_shape) and index == 0 else f"arg{index + 1}"
        while preferred in fallback:
            preferred = f"arg{index + 1}"
        fallback.append(preferred)
        if len(fallback) == arg_count:
            break

    return fallback


def resolve_parameter_names(
    topic: str,
    function_name: str,
    starter_code: str,
    description: str,
    test_cases: list[TestCaseCreate],
    runtime_shape: RuntimeShape | None = None,
) -> tuple[list[str], list[str]]:
    resolved_shape = runtime_shape or infer_runtime_shape(topic, description, starter_code)
    extracted_names = extract_parameter_names(starter_code, function_name, topic, resolved_shape)
    expected_arity = _input_arity(test_cases)

    if expected_arity == 0:
        return extracted_names, []

    if test_cases and isinstance(test_cases[0].input, dict):
        return list(test_cases[0].input.keys()), []

    if len(extracted_names) == expected_arity:
        return extracted_names, []

    description_names = _extract_names_from_description(description)
    resolved: list[str] = []
    for name in description_names:
        if name not in resolved:
            resolved.append(name)
        if len(resolved) == expected_arity:
            break

    if len(resolved) < expected_arity:
        resolved = _fallback_parameter_names(topic, expected_arity, description)

    warnings: list[str] = []
    if extracted_names != resolved:
        before = ", ".join(extracted_names) if extracted_names else "no parameters"
        after = ", ".join(resolved) if resolved else "no parameters"
        warnings.append(
            f"Adjusted the generated function signature from `{before}` to `{after}` to match the detected problem inputs."
        )

    return resolved, warnings


def build_python_starter_code(
    function_name: str,
    parameter_names: list[str],
    starter_code: str,
    topic: str,
    runtime_shape: RuntimeShape | None = None,
) -> str:
    def render_solution_stub(prefix: str = "") -> str:
        signature = f"    def {function_name}(self, {', '.join(parameter_names)}):" if parameter_names else f"    def {function_name}(self):"
        return f"{prefix}class Solution:\n{signature}\n        pass\n"

    def is_trivial_top_level_stub(code: str) -> bool:
        expected_signature = f"def {function_name}({', '.join(parameter_names)}):" if parameter_names else f"def {function_name}():"
        lines = [line.rstrip() for line in code.splitlines() if line.strip()]
        return len(lines) == 2 and lines[0] == expected_signature and lines[1] == "    pass"

    resolved_shape = runtime_shape or infer_runtime_shape(topic, starter_code, starter_code)
    current_names = extract_parameter_names(starter_code, function_name, topic, resolved_shape)
    cleaned = starter_code.strip()
    if current_names == parameter_names and cleaned.startswith("class Solution:"):
        return cleaned + ("\n" if not cleaned.endswith("\n") else "")
    if current_names == parameter_names and cleaned.startswith(f"def {function_name}(") and not is_trivial_top_level_stub(cleaned):
        return cleaned + ("\n" if not cleaned.endswith("\n") else "")

    if resolved_shape == "linked_list":
        return (
            "# class ListNode:\n"
            "#     def __init__(self, val=0, next=None):\n"
            "#         self.val = val\n"
            "#         self.next = next\n\n"
            + render_solution_stub()
        )
    if resolved_shape == "random_pointer_linked_list":
        return (
            "# class Node:\n"
            "#     def __init__(self, x: int, next: 'Node' = None, random: 'Node' = None):\n"
            "#         self.val = int(x)\n"
            "#         self.next = next\n"
            "#         self.random = random\n\n"
            + render_solution_stub()
        )

    return render_solution_stub()


def is_linked_list_problem(topic: str) -> bool:
    normalized = topic.strip().lower().replace("-", " ")
    return "linked list" in normalized


def _pick_representative(values: list[object]) -> object:
    for value in values:
        if value is None:
            continue
        if isinstance(value, list) and len(value) == 0:
            continue
        return value

    for value in values:
        if value is not None:
            return value

    return 0


def _infer_type(value: object, *, linked_list: bool = False, random_linked_list: bool = False) -> TypeSpec:
    if random_linked_list:
        return TypeSpec("random_linked_list")
    if linked_list:
        return TypeSpec("linked_list")

    if isinstance(value, bool):
        return TypeSpec("bool")

    if isinstance(value, int) and not isinstance(value, bool):
        return TypeSpec("int")

    if isinstance(value, str):
        return TypeSpec("string")

    if isinstance(value, list):
        if len(value) == 0:
            return TypeSpec("list", TypeSpec("int"))
        return TypeSpec("list", _infer_type(_pick_representative(list(value))))

    return TypeSpec("int")


def infer_signature(
    topic: str,
    function_name: str,
    starter_code: str,
    description: str,
    test_cases: list[TestCaseCreate],
    runtime_shape: RuntimeShape | None = None,
) -> tuple[list[str], list[TypeSpec], TypeSpec]:
    resolved_shape = runtime_shape or infer_runtime_shape(topic, description, starter_code)
    parameter_names, _ = resolve_parameter_names(
        topic,
        function_name,
        starter_code,
        description,
        test_cases,
        resolved_shape,
    )

    representative_inputs: list[object] = []
    if test_cases:
        first_input = test_cases[0].input
        if isinstance(first_input, list):
            representative_inputs = [[] for _ in range(len(first_input))]
            for case in test_cases:
                case_input = case.input if isinstance(case.input, list) else [case.input]
                for index in range(len(representative_inputs)):
                    if index < len(case_input):
                        representative_inputs[index].append(case_input[index])  # type: ignore[attr-defined]
        elif isinstance(first_input, dict):
            parameter_names = list(first_input.keys())
            representative_inputs = [[] for _ in range(len(parameter_names))]
            for case in test_cases:
                case_input = case.input if isinstance(case.input, dict) else {}
                for index, name in enumerate(parameter_names):
                    representative_inputs[index].append(case_input.get(name))  # type: ignore[attr-defined]
        else:
            representative_inputs = [[case.input for case in test_cases]]

    if not parameter_names:
        parameter_names = [f"arg{index + 1}" for index in range(len(representative_inputs))]

    parameter_types: list[TypeSpec] = []
    for values in representative_inputs:
        representative_value = _pick_representative(values if isinstance(values, list) else [values])
        linked_list = resolved_shape == "linked_list" and (
            representative_value is None or isinstance(representative_value, list)
        )
        random_linked_list = resolved_shape == "random_pointer_linked_list" and (
            representative_value is None or isinstance(representative_value, list)
        )
        parameter_types.append(
            _infer_type(representative_value, linked_list=linked_list, random_linked_list=random_linked_list)
        )

    output_values = [case.expected_output for case in test_cases]
    representative_output = _pick_representative(output_values)
    linked_list_output = resolved_shape == "linked_list" and (
        representative_output is None or isinstance(representative_output, list)
    )
    random_linked_list_output = resolved_shape == "random_pointer_linked_list" and (
        representative_output is None or isinstance(representative_output, list)
    )
    return_type = _infer_type(
        representative_output,
        linked_list=linked_list_output,
        random_linked_list=random_linked_list_output,
    )

    return parameter_names, parameter_types, return_type


def _java_type(spec: TypeSpec) -> str:
    if spec.kind == "int":
        return "int"
    if spec.kind == "bool":
        return "boolean"
    if spec.kind == "string":
        return "String"
    if spec.kind == "linked_list":
        return "ListNode"
    if spec.kind == "random_linked_list":
        return "Node"
    if spec.kind == "list" and spec.item is not None:
        return f"{_java_type(spec.item)}[]"
    return "int"


def _cpp_type(spec: TypeSpec) -> str:
    if spec.kind == "int":
        return "int"
    if spec.kind == "bool":
        return "bool"
    if spec.kind == "string":
        return "string"
    if spec.kind == "linked_list":
        return "ListNode*"
    if spec.kind == "random_linked_list":
        return "Node*"
    if spec.kind == "list" and spec.item is not None:
        return f"vector<{_cpp_type(spec.item)}>"
    return "int"


def java_type_name(spec: TypeSpec) -> str:
    return _java_type(spec)


def cpp_type_name(spec: TypeSpec) -> str:
    return _cpp_type(spec)


def _java_default_return(spec: TypeSpec) -> str:
    if spec.kind == "int":
        return "0"
    if spec.kind == "bool":
        return "false"
    if spec.kind == "string":
        return '""'
    if spec.kind == "linked_list":
        return "null"
    if spec.kind == "random_linked_list":
        return "null"
    if spec.kind == "list":
        return f"new {_java_type(spec)}{{}}"
    return "0"


def _cpp_default_return(spec: TypeSpec) -> str:
    if spec.kind == "int":
        return "0"
    if spec.kind == "bool":
        return "false"
    if spec.kind == "string":
        return '""'
    if spec.kind == "linked_list":
        return "nullptr"
    if spec.kind == "random_linked_list":
        return "nullptr"
    if spec.kind == "list":
        return "{}"
    return "0"


def render_java_literal(value: object, spec: TypeSpec) -> str:
    if spec.kind == "int":
        return str(int(value or 0))
    if spec.kind == "bool":
        return "true" if value else "false"
    if spec.kind == "string":
        return json.dumps("" if value is None else value)
    if spec.kind == "linked_list":
        if value is None:
            return "null"
        return f"buildLinkedList({render_java_literal(value, TypeSpec('list', TypeSpec('int')))})"
    if spec.kind == "random_linked_list":
        if value is None:
            return "null"
        pairs = value if isinstance(value, list) else []
        inner = ", ".join(
            "new Integer[]{" + ", ".join("null" if item is None else str(int(item)) for item in pair) + "}"
            for pair in pairs
        )
        return f"buildRandomList(new Integer[][]{{{inner}}})"
    if spec.kind == "list" and spec.item is not None:
        items = value if isinstance(value, list) else []
        if spec.item.kind == "linked_list":
            raise ValueError("Nested linked list literals are not supported.")
        inner = ", ".join(render_java_literal(item, spec.item) for item in items)
        return f"new {_java_type(spec)}{{{inner}}}"
    return "0"


def render_cpp_literal(value: object, spec: TypeSpec) -> str:
    if spec.kind == "int":
        return str(int(value or 0))
    if spec.kind == "bool":
        return "true" if value else "false"
    if spec.kind == "string":
        return json.dumps("" if value is None else value)
    if spec.kind == "linked_list":
        if value is None:
            return "nullptr"
        return f"buildLinkedList({render_cpp_literal(value, TypeSpec('list', TypeSpec('int')))})"
    if spec.kind == "random_linked_list":
        if value is None:
            return "nullptr"
        pairs = value if isinstance(value, list) else []
        inner = ", ".join(
            "{" + ", ".join(str(-1 if item is None else int(item)) for item in pair) + "}"
            for pair in pairs
        )
        return f"buildRandomList(vector<pair<int,int>>{{{inner}}})"
    if spec.kind == "list" and spec.item is not None:
        items = value if isinstance(value, list) else []
        inner = ", ".join(render_cpp_literal(item, spec.item) for item in items)
        return f"{_cpp_type(spec)}{{{inner}}}"
    return "0"


def build_starter_codes(
    topic: str,
    function_name: str,
    starter_code: str,
    description: str,
    test_cases: list[TestCaseCreate],
    runtime_shape: RuntimeShape | None = None,
) -> dict[str, str]:
    resolved_shape = runtime_shape or infer_runtime_shape(topic, description, starter_code)
    parameter_names, parameter_types, return_type = infer_signature(
        topic,
        function_name,
        starter_code,
        description,
        test_cases,
        resolved_shape,
    )
    parameter_list = ", ".join(parameter_names)
    js_signature = ", ".join(parameter_names)
    java_signature = ", ".join(
        f"{_java_type(spec)} {name}" for name, spec in zip(parameter_names, parameter_types, strict=False)
    )
    cpp_signature = ", ".join(
        f"{_cpp_type(spec)} {name}" for name, spec in zip(parameter_names, parameter_types, strict=False)
    )

    linked_list_comment_js = ""
    linked_list_comment_java = ""
    linked_list_comment_cpp = ""
    if resolved_shape == "linked_list":
        linked_list_comment_js = """// function ListNode(val, next) {
//   this.val = val ?? 0;
//   this.next = next ?? null;
// }

"""
        linked_list_comment_java = """class ListNode {
    int val;
    ListNode next;
    ListNode() {}
    ListNode(int val) { this.val = val; }
    ListNode(int val, ListNode next) { this.val = val; this.next = next; }
}

"""
        linked_list_comment_cpp = """struct ListNode {
    int val;
    ListNode *next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *next) : val(x), next(next) {}
};

"""
    if resolved_shape == "random_pointer_linked_list":
        linked_list_comment_js = """// function Node(val, next, random) {
//   this.val = val ?? 0;
//   this.next = next ?? null;
//   this.random = random ?? null;
// }

"""
        linked_list_comment_java = """class Node {
    int val;
    Node next;
    Node random;
    Node(int val) { this.val = val; }
    Node(int val, Node next, Node random) { this.val = val; this.next = next; this.random = random; }
}

"""
        linked_list_comment_cpp = """struct Node {
    int val;
    Node *next;
    Node *random;
    Node(int x) : val(x), next(nullptr), random(nullptr) {}
    Node(int x, Node *next, Node *random) : val(x), next(next), random(random) {}
};

"""

    javascript_code = (
        f"{linked_list_comment_js}function {function_name}({js_signature}) {{\n"
        "  // Write your solution here.\n"
        "}\n"
    )

    java_code = (
        "import java.util.*;\n\n"
        f"{linked_list_comment_java}"
        "class Solution {\n"
        f"    public {_java_type(return_type)} {function_name}({java_signature}) {{\n"
        "        // Write your solution here.\n"
        f"        return {_java_default_return(return_type)};\n"
        "    }\n"
        "}\n"
    )

    cpp_code = (
        "#include <bits/stdc++.h>\n"
        "using namespace std;\n\n"
        f"{linked_list_comment_cpp}"
        "class Solution {\n"
        "public:\n"
        f"    {_cpp_type(return_type)} {function_name}({cpp_signature}) {{\n"
        "        // Write your solution here.\n"
        f"        return {_cpp_default_return(return_type)};\n"
        "    }\n"
        "};\n"
    )

    return {
        "python": build_python_starter_code(function_name, parameter_names, starter_code, topic, resolved_shape),
        "javascript": javascript_code,
        "java": java_code,
        "cpp": cpp_code,
    }


def to_expected_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"))
