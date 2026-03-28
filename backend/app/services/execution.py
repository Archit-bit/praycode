from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

from app.schemas.execution import ExecutionResponse, SupportedLanguage
from app.schemas.problem import TestCaseCreate
from app.services.language_support import (
    TypeSpec,
    cpp_type_name,
    infer_signature,
    is_random_pointer_runtime_shape,
    java_type_name,
    render_cpp_literal,
    render_java_literal,
)


PYTHON_RUNNER_TEMPLATE = """import ast
import contextlib
import io
import json
import sys
import traceback
from typing import List, Optional


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class Node:
    def __init__(self, x=0, next=None, random=None):
        self.val = int(x)
        self.next = next
        self.random = random


def is_linked_list_shape(runtime_shape):
    return runtime_shape == "linked_list"


def is_random_pointer_linked_list_shape(runtime_shape):
    return runtime_shape == "random_pointer_linked_list"


def serialize_random_list(head):
    if head is None:
        return []

    nodes = []
    index_by_id = {{}}
    current = head
    seen = set()

    while current is not None and id(current) not in seen:
        seen.add(id(current))
        index_by_id[id(current)] = len(nodes)
        nodes.append(current)
        current = current.next

    serialized = []
    for current in nodes:
        random_index = None
        if current.random is not None:
            random_index = index_by_id.get(id(current.random))
        serialized.append([current.val, random_index])

    return serialized


def normalize(value, runtime_shape):
    if is_random_pointer_linked_list_shape(runtime_shape):
        if isinstance(value, Node):
            return serialize_random_list(value)
    if isinstance(value, ListNode):
        items = []
        seen = set()
        current = value

        while current is not None:
            if id(current) in seen:
                items.append("[cycle]")
                break

            seen.add(id(current))
            items.append(normalize(current.val, runtime_shape))
            current = current.next

        return items
    if isinstance(value, tuple):
        return [normalize(item, runtime_shape) for item in value]
    if isinstance(value, list):
        return [normalize(item, runtime_shape) for item in value]
    if isinstance(value, dict):
        return {{str(key): normalize(val, runtime_shape) for key, val in value.items()}}
    return value


def normalize_result(value, runtime_shape):
    if (is_linked_list_shape(runtime_shape) or is_random_pointer_linked_list_shape(runtime_shape)) and value is None:
        return []
    return normalize(value, runtime_shape)


def build_linked_list(values):
    if values is None:
        return None
    if not isinstance(values, list):
        return values

    dummy = ListNode()
    tail = dummy
    for item in values:
        tail.next = ListNode(item)
        tail = tail.next
    return dummy.next


def build_random_list(values):
    if values is None:
        return None
    if not isinstance(values, list):
        return values
    if len(values) == 0:
        return None

    nodes = [Node(pair[0]) for pair in values]
    for index, pair in enumerate(values):
        if index + 1 < len(nodes):
            nodes[index].next = nodes[index + 1]
        random_index = pair[1] if len(pair) > 1 else None
        if random_index is not None:
            nodes[index].random = nodes[random_index]
    return nodes[0]


def adapt_input(case_input, runtime_shape):
    if is_random_pointer_linked_list_shape(runtime_shape):
        if isinstance(case_input, list):
            return [build_random_list(item) if isinstance(item, list) or item is None else item for item in case_input]
        if isinstance(case_input, dict):
            return {{
                key: build_random_list(value) if isinstance(value, list) or value is None else value
                for key, value in case_input.items()
            }}
        return case_input

    if not is_linked_list_shape(runtime_shape):
        return case_input
    if isinstance(case_input, list):
        return [build_linked_list(item) if isinstance(item, list) or item is None else item for item in case_input]
    if isinstance(case_input, dict):
        return {{
            key: build_linked_list(value) if isinstance(value, list) or value is None else value
            for key, value in case_input.items()
        }}
    return case_input


def attach_common_aliases(fn, adapted_input, runtime_shape):
    if not (is_linked_list_shape(runtime_shape) or is_random_pointer_linked_list_shape(runtime_shape)):
        return
    fn_globals = getattr(fn, "__globals__", None)
    if not isinstance(fn_globals, dict):
        return

    positional_values = adapted_input if isinstance(adapted_input, list) else [adapted_input]
    aliases = ["head", "l1", "l2", "list1", "list2", "headA", "headB"]
    for index, value in enumerate(positional_values):
        if index >= len(aliases):
            break
        if isinstance(value, (ListNode, Node)) or value is None:
            fn_globals[aliases[index]] = value


def call_target(fn, case_input):
    if isinstance(case_input, list):
        return fn(*case_input)
    if isinstance(case_input, dict):
        return fn(**case_input)
    return fn(case_input)


def extract_defined_symbols(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [], []

    top_level_functions = []
    solution_methods = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            top_level_functions.append(node.name)
        elif isinstance(node, ast.ClassDef) and node.name == "Solution":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name != "__init__":
                    solution_methods.append(child.name)

    return top_level_functions, solution_methods


namespace = {{}}

try:
    with open("solution.py", "r", encoding="utf-8") as source_file:
        source = source_file.read()
    namespace.update({{"ListNode": ListNode, "Node": Node, "Optional": Optional, "List": List}})
    exec(compile(source, "solution.py", "exec"), namespace)
except Exception:
    payload = {{
        "status": "error",
        "error": "Failed to load submitted code:\\n" + traceback.format_exc(),
        "results": [],
    }}
    sys.__stdout__.write(json.dumps(payload))
    raise SystemExit(0)

function_name = {function_name}
problem_topic = {problem_topic}
runtime_shape = {runtime_shape}
defined_functions, solution_methods = extract_defined_symbols(source)
target = namespace.get(function_name)

if not callable(target):
    solution_class = namespace.get("Solution")
    if callable(solution_class):
        try:
            solution_instance = solution_class()
            solution_method = getattr(solution_instance, function_name, None)
            if callable(solution_method):
                target = solution_method
        except Exception:
            solution_instance = None

if not callable(target) and len(defined_functions) == 1:
    candidate = namespace.get(defined_functions[0])
    if callable(candidate):
        target = candidate

if not callable(target) and len(solution_methods) == 1:
    solution_class = namespace.get("Solution")
    if callable(solution_class):
        try:
            solution_instance = solution_class()
            candidate = getattr(solution_instance, solution_methods[0], None)
            if callable(candidate):
                target = candidate
        except Exception:
            solution_instance = None

if not callable(target):
    available_symbols = []
    if defined_functions:
        available_symbols.append("top-level functions: " + ", ".join(defined_functions))
    if solution_methods:
        available_symbols.append("Solution methods: " + ", ".join(solution_methods))
    available_text = "; ".join(available_symbols) if available_symbols else "No runnable function was detected."
    payload = {{
        "status": "error",
        "error": (
            f"Expected a callable named '{{function_name}}' but it was not found. "
            f"{{available_text}} Rename your function or click Reset Draft."
        ),
        "results": [],
    }}
    sys.__stdout__.write(json.dumps(payload))
    raise SystemExit(0)

cases = json.loads({test_cases_json})
results = []

for case in cases:
    buffer = io.StringIO()
    try:
        adapted_input = adapt_input(case["input"], runtime_shape)
        attach_common_aliases(target, adapted_input, runtime_shape)
        with contextlib.redirect_stdout(buffer):
            actual = call_target(target, adapted_input)
        normalized_actual = normalize_result(actual, runtime_shape)
        normalized_expected = normalize_result(case["expected_output"], runtime_shape)
        results.append(
            {{
                "input": case["input"],
                "expected_output": case["expected_output"],
                "actual_output": normalized_actual,
                "passed": normalized_actual == normalized_expected,
                "stdout": buffer.getvalue(),
                "error": None,
                "explanation": case.get("explanation", ""),
            }}
        )
    except Exception:
        results.append(
            {{
                "input": case["input"],
                "expected_output": case["expected_output"],
                "actual_output": None,
                "passed": False,
                "stdout": buffer.getvalue(),
                "error": traceback.format_exc(),
                "explanation": case.get("explanation", ""),
            }}
        )

payload = {{
    "status": "success",
    "error": None,
    "results": results,
}}
sys.__stdout__.write(json.dumps(payload))
"""


def _error_response(
    *,
    language: SupportedLanguage,
    mode: str,
    test_cases: list[TestCaseCreate],
    error: str,
    status: str = "error",
) -> ExecutionResponse:
    return ExecutionResponse(
        status=status,  # type: ignore[arg-type]
        mode=mode,  # type: ignore[arg-type]
        language=language,
        passed_count=0,
        total_count=len(test_cases),
        all_passed=False,
        results=[],
        error=error,
    )


def _parse_runner_payload(
    *,
    language: SupportedLanguage,
    mode: str,
    test_cases: list[TestCaseCreate],
    completed: subprocess.CompletedProcess[str],
) -> ExecutionResponse:
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if not stdout:
        return _error_response(
            language=language,
            mode=mode,
            test_cases=test_cases,
            error=stderr or "Execution did not produce a result payload.",
        )

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return _error_response(
            language=language,
            mode=mode,
            test_cases=test_cases,
            error=stderr or stdout,
        )

    results = payload.get("results", [])
    passed_count = sum(1 for item in results if item.get("passed"))
    total_count = len(results)

    return ExecutionResponse(
        status=payload.get("status", "error"),
        mode=mode,  # type: ignore[arg-type]
        language=language,
        passed_count=passed_count,
        total_count=total_count,
        all_passed=total_count > 0 and passed_count == total_count,
        results=results,
        error=payload.get("error") or stderr or None,
    )


def _run_subprocess(
    command: list[str],
    *,
    cwd: str,
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None


def _prepare_java_code(code: str) -> str:
    stripped = code.strip()
    if re.search(r"\bclass\s+Solution\b", stripped):
        return stripped + ("\n" if not stripped.endswith("\n") else "")
    return (
        "import java.util.*;\n\n"
        "class Solution {\n"
        f"{stripped}\n"
        "}\n"
    )


def _prepare_cpp_code(code: str) -> str:
    stripped = code.strip()
    if re.search(r"\b(class|struct)\s+Solution\b", stripped):
        return stripped + ("\n" if not stripped.endswith("\n") else "")
    return (
        "#include <bits/stdc++.h>\n"
        "using namespace std;\n\n"
        "class Solution {\n"
        "public:\n"
        f"{stripped}\n"
        "};\n"
    )


def _javascript_runner(function_name: str, problem_topic: str, test_cases: list[TestCaseCreate]) -> str:
    cases_json = json.dumps([case.model_dump() for case in test_cases])
    return f"""import fs from "fs";
import vm from "vm";

class ListNode {{
  constructor(val = 0, next = null) {{
    this.val = val;
    this.next = next;
  }}
}}

function isLinkedListProblem(topic) {{
  return topic.trim().toLowerCase().replace(/-/g, " ").includes("linked list");
}}

function buildLinkedList(values) {{
  if (values === null) return null;
  if (!Array.isArray(values)) return values;
  const dummy = new ListNode();
  let tail = dummy;
  for (const item of values) {{
    tail.next = new ListNode(item);
    tail = tail.next;
  }}
  return dummy.next;
}}

function normalize(value, topic) {{
  if (isLinkedListProblem(topic) && value === null) return [];
  if (value instanceof ListNode) {{
    const items = [];
    const seen = new Set();
    let current = value;
    while (current !== null) {{
      if (seen.has(current)) {{
        items.push("[cycle]");
        break;
      }}
      seen.add(current);
      items.push(normalize(current.val, topic));
      current = current.next;
    }}
    return items;
  }}
  if (Array.isArray(value)) return value.map((item) => normalize(item, topic));
  if (value && typeof value === "object") {{
    const mapped = {{}};
    for (const [key, item] of Object.entries(value)) mapped[key] = normalize(item, topic);
    return mapped;
  }}
  return value ?? null;
}}

function adaptInput(caseInput, topic) {{
  if (!isLinkedListProblem(topic)) return caseInput;
  if (Array.isArray(caseInput)) {{
    return caseInput.map((item) => Array.isArray(item) || item === null ? buildLinkedList(item) : item);
  }}
  if (caseInput && typeof caseInput === "object") {{
    const mapped = {{}};
    for (const [key, item] of Object.entries(caseInput)) {{
      mapped[key] = Array.isArray(item) || item === null ? buildLinkedList(item) : item;
    }}
    return mapped;
  }}
  return caseInput;
}}

function callTarget(fn, caseInput) {{
  if (Array.isArray(caseInput)) return fn(...caseInput);
  if (caseInput && typeof caseInput === "object") return fn(...Object.values(caseInput));
  return fn(caseInput);
}}

const logs = [];
const consoleProxy = {{
  log: (...args) => logs.push(args.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join(" ")),
  error: (...args) => logs.push(args.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join(" ")),
  warn: (...args) => logs.push(args.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join(" ")),
}};

const source = fs.readFileSync("solution.js", "utf8");
const context = vm.createContext({{ ListNode, console: consoleProxy, module: {{ exports: {{}} }}, exports: {{}} }});

try {{
  vm.runInContext(source, context);
}} catch (error) {{
  process.stdout.write(JSON.stringify({{
    status: "error",
    error: "Failed to load submitted code:\\n" + error.stack,
    results: [],
  }}));
  process.exit(0);
}}

let target = context[{json.dumps(function_name)}];
if (typeof target !== "function" && typeof context.module?.exports?.[{json.dumps(function_name)}] === "function") {{
  target = context.module.exports[{json.dumps(function_name)}];
}}
if (typeof target !== "function" && typeof context.Solution === "function") {{
  const instance = new context.Solution();
  if (typeof instance[{json.dumps(function_name)}] === "function") {{
    target = instance[{json.dumps(function_name)}].bind(instance);
  }} else {{
    const methods = Object.getOwnPropertyNames(context.Solution.prototype).filter((name) => name !== "constructor");
    if (methods.length === 1 && typeof instance[methods[0]] === "function") {{
      target = instance[methods[0]].bind(instance);
    }}
  }}
}}

if (typeof target !== "function") {{
  process.stdout.write(JSON.stringify({{
    status: "error",
    error: "Expected a callable named {function_name} but it was not found.",
    results: [],
  }}));
  process.exit(0);
}}

const problemTopic = {json.dumps(problem_topic)};
const cases = {cases_json};
const results = [];

for (const caseItem of cases) {{
  logs.length = 0;
  try {{
    const adaptedInput = adaptInput(caseItem.input, problemTopic);
    if (isLinkedListProblem(problemTopic) && Array.isArray(adaptedInput)) {{
      if (adaptedInput.length > 0) context.head = adaptedInput[0];
      if (adaptedInput.length > 1) context.l1 = adaptedInput[0];
      if (adaptedInput.length > 1) context.l2 = adaptedInput[1];
    }}
    const actual = callTarget(target, adaptedInput);
    const normalizedActual = normalize(actual, problemTopic);
    const normalizedExpected = normalize(caseItem.expected_output, problemTopic);
    results.push({{
      input: caseItem.input,
      expected_output: caseItem.expected_output,
      actual_output: normalizedActual,
      passed: JSON.stringify(normalizedActual) === JSON.stringify(normalizedExpected),
      stdout: logs.join("\\n"),
      error: null,
      explanation: caseItem.explanation ?? "",
    }});
  }} catch (error) {{
    results.push({{
      input: caseItem.input,
      expected_output: caseItem.expected_output,
      actual_output: null,
      passed: false,
      stdout: logs.join("\\n"),
      error: error.stack,
      explanation: caseItem.explanation ?? "",
    }});
  }}
}}

process.stdout.write(JSON.stringify({{ status: "success", error: null, results }}));
"""


def _java_escape_json(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _java_serializer_name(spec) -> str:
    if spec.kind == "int":
        return "serializeInt"
    if spec.kind == "bool":
        return "serializeBoolean"
    if spec.kind == "string":
        return "serializeString"
    if spec.kind == "linked_list":
        return "serializeListNode"
    if spec.kind == "list":
        return f"serialize{re.sub(r'[^a-zA-Z0-9]', '', java_type_name(spec).title())}"
    return "serializeInt"


def _java_serializer_defs(spec, seen: set[str]) -> list[str]:
    name = _java_serializer_name(spec)
    if name in seen:
        return []
    seen.add(name)

    if spec.kind == "int":
        return ["private static String serializeInt(int value) { return Integer.toString(value); }"]
    if spec.kind == "bool":
        return ["private static String serializeBoolean(boolean value) { return value ? \"true\" : \"false\"; }"]
    if spec.kind == "string":
        return [
            "private static String serializeString(String value) { return value == null ? \"null\" : \"\\\"\" + escapeJson(value) + \"\\\"\"; }"
        ]
    if spec.kind == "linked_list":
        defs = _java_serializer_defs(TypeSpec("int"), seen)
        defs.append(
            """private static String serializeListNode(ListNode head) {
        if (head == null) return "[]";
        StringBuilder builder = new StringBuilder("[");
        Set<ListNode> seen = new HashSet<>();
        ListNode current = head;
        boolean first = true;
        while (current != null) {
            if (seen.contains(current)) {
                if (!first) builder.append(",");
                builder.append("\\"[cycle]\\"");
                break;
            }
            seen.add(current);
            if (!first) builder.append(",");
            builder.append(serializeInt(current.val));
            first = false;
            current = current.next;
        }
        builder.append("]");
        return builder.toString();
    }"""
        )
        return defs
    if spec.kind == "list" and spec.item is not None:
        defs = _java_serializer_defs(spec.item, seen)
        defs.append(
            f"""private static String {name}({java_type_name(spec)} values) {{
        if (values == null) return "null";
        StringBuilder builder = new StringBuilder("[");
        for (int i = 0; i < values.length; i++) {{
            if (i > 0) builder.append(",");
            builder.append({_java_serializer_name(spec.item)}(values[i]));
        }}
        builder.append("]");
        return builder.toString();
    }}"""
        )
        return defs
    return []


def _java_runner(function_name: str, problem_topic: str, test_cases: list[TestCaseCreate]) -> str:
    parameter_names, parameter_types, return_type = infer_signature(problem_topic, function_name, "", "", test_cases)
    serializer_defs = "\n\n".join(_java_serializer_defs(return_type, set()))
    uses_linked_list = any(spec.kind == "linked_list" for spec in parameter_types) or return_type.kind == "linked_list"

    linked_list_helpers = ""
    if uses_linked_list:
        linked_list_helpers = """
class ListNode {
    int val;
    ListNode next;
    ListNode() {}
    ListNode(int val) { this.val = val; }
    ListNode(int val, ListNode next) { this.val = val; this.next = next; }
}

"""

    case_blocks: list[str] = []
    for index, case in enumerate(test_cases, start=1):
        case_input = case.input if isinstance(case.input, list) else [case.input]
        argument_literals = ", ".join(
            render_java_literal(value, spec)
            for value, spec in zip(case_input, parameter_types, strict=False)
        )
        expected_json = _java_escape_json(json.dumps(case.expected_output, separators=(",", ":")))
        input_json = json.dumps(case.input, separators=(",", ":"))
        expected_output_json = json.dumps(case.expected_output, separators=(",", ":"))
        explanation_json = _java_escape_json(case.explanation)
        serializer_name = _java_serializer_name(return_type)
        return_type_name = java_type_name(return_type)

        case_blocks.append(
            f"""
        capture.reset();
        try {{
            System.setOut(captureStream);
            {return_type_name} actualValue = solution.{function_name}({argument_literals});
            System.out.flush();
            System.setOut(originalOut);
            String actualJson = {serializer_name}(actualValue);
            appendCaseResult(
                results,
                {json.dumps(input_json)},
                {json.dumps(expected_output_json)},
                actualJson,
                actualJson.equals("{expected_json}"),
                capture.toString(),
                null,
                {json.dumps(explanation_json)}
            );
        }} catch (Throwable error) {{
            System.out.flush();
            System.setOut(originalOut);
            appendCaseResult(
                results,
                {json.dumps(input_json)},
                {json.dumps(expected_output_json)},
                "null",
                false,
                capture.toString(),
                stackTrace(error),
                {json.dumps(explanation_json)}
            );
        }}
"""
        )

    build_linked_list = ""
    if uses_linked_list:
        build_linked_list = """private static ListNode buildLinkedList(int[] values) {
        if (values == null) return null;
        ListNode dummy = new ListNode();
        ListNode tail = dummy;
        for (int value : values) {
            tail.next = new ListNode(value);
            tail = tail.next;
        }
        return dummy.next;
    }

"""

    return f"""import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

{linked_list_helpers}public class Runner {{
    private static String escapeJson(String value) {{
        return value
            .replace("\\\\", "\\\\\\\\")
            .replace("\\"", "\\\\\\"")
            .replace("\\n", "\\\\n")
            .replace("\\r", "\\\\r");
    }}

    private static String quote(String value) {{
        return value == null ? "null" : "\\"" + escapeJson(value) + "\\"";
    }}

{build_linked_list}{serializer_defs}

    private static String stackTrace(Throwable error) {{
        StringWriter writer = new StringWriter();
        error.printStackTrace(new PrintStream(new java.io.OutputStream() {{
            @Override
            public void write(int value) {{
                writer.write(value);
            }}
        }}));
        return writer.toString();
    }}

    private static void appendCaseResult(
        List<String> results,
        String inputJson,
        String expectedJson,
        String actualJson,
        boolean passed,
        String stdout,
        String error,
        String explanation
    ) {{
        results.add(
            "{{\\"input\\":" + inputJson +
            ",\\"expected_output\\":" + expectedJson +
            ",\\"actual_output\\":" + (actualJson == null ? "null" : actualJson) +
            ",\\"passed\\":" + (passed ? "true" : "false") +
            ",\\"stdout\\":" + quote(stdout) +
            ",\\"error\\":" + (error == null ? "null" : quote(error)) +
            ",\\"explanation\\":" + quote(explanation) +
            "}}"
        );
    }}

    public static void main(String[] args) {{
        Solution solution = new Solution();
        List<String> results = new ArrayList<>();
        ByteArrayOutputStream capture = new ByteArrayOutputStream();
        PrintStream originalOut = System.out;
        PrintStream captureStream = new PrintStream(capture);
{''.join(case_blocks)}
        System.out.print("{{\\"status\\":\\"success\\",\\"error\\":null,\\"results\\":[" + String.join(",", results) + "]}}");
    }}
}}
"""


def _cpp_serializer_name(spec) -> str:
    if spec.kind == "int":
        return "serializeInt"
    if spec.kind == "bool":
        return "serializeBool"
    if spec.kind == "string":
        return "serializeString"
    if spec.kind == "linked_list":
        return "serializeListNode"
    if spec.kind == "list":
        return f"serialize{re.sub(r'[^a-zA-Z0-9]', '', cpp_type_name(spec).title())}"
    return "serializeInt"


def _cpp_serializer_defs(spec, seen: set[str]) -> list[str]:
    name = _cpp_serializer_name(spec)
    if name in seen:
        return []
    seen.add(name)

    if spec.kind == "int":
        return ["static string serializeInt(int value) { return to_string(value); }"]
    if spec.kind == "bool":
        return ["static string serializeBool(bool value) { return value ? \"true\" : \"false\"; }"]
    if spec.kind == "string":
        return [
            """static string serializeString(const string& value) {
    return "\\\"" + escapeJson(value) + "\\\"";
}"""
        ]
    if spec.kind == "linked_list":
        defs = _cpp_serializer_defs(TypeSpec("int"), seen)
        defs.append(
            """static string serializeListNode(ListNode* head) {
    if (head == nullptr) return "[]";
    stringstream builder;
    builder << "[";
    unordered_set<ListNode*> seen;
    ListNode* current = head;
    bool first = true;
    while (current != nullptr) {
        if (seen.count(current)) {
            if (!first) builder << ",";
            builder << "\\"[cycle]\\"";
            break;
        }
        seen.insert(current);
        if (!first) builder << ",";
        builder << serializeInt(current->val);
        first = false;
        current = current->next;
    }
    builder << "]";
    return builder.str();
}"""
        )
        return defs
    if spec.kind == "list" and spec.item is not None:
        defs = _cpp_serializer_defs(spec.item, seen)
        defs.append(
            f"""static string {name}(const {cpp_type_name(spec)}& values) {{
    stringstream builder;
    builder << "[";
    for (size_t i = 0; i < values.size(); i++) {{
        if (i > 0) builder << ",";
        builder << {_cpp_serializer_name(spec.item)}(values[i]);
    }}
    builder << "]";
    return builder.str();
}}"""
        )
        return defs
    return []


def _cpp_runner(function_name: str, problem_topic: str, test_cases: list[TestCaseCreate], use_solution_class: bool) -> str:
    _, parameter_types, return_type = infer_signature(problem_topic, function_name, "", "", test_cases)
    serializer_defs = "\n\n".join(_cpp_serializer_defs(return_type, set()))
    uses_linked_list = any(spec.kind == "linked_list" for spec in parameter_types) or return_type.kind == "linked_list"

    linked_list_helpers = ""
    if uses_linked_list:
        linked_list_helpers = """struct ListNode {
    int val;
    ListNode* next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode* next) : val(x), next(next) {}
};

static ListNode* buildLinkedList(const vector<int>& values) {
    ListNode dummy;
    ListNode* tail = &dummy;
    for (int value : values) {
        tail->next = new ListNode(value);
        tail = tail->next;
    }
    return dummy.next;
}

"""

    case_blocks: list[str] = []
    for case in test_cases:
        case_input = case.input if isinstance(case.input, list) else [case.input]
        argument_literals = ", ".join(
            render_cpp_literal(value, spec)
            for value, spec in zip(case_input, parameter_types, strict=False)
        )
        call_expression = (
            f"solution.{function_name}({argument_literals})"
            if use_solution_class
            else f"{function_name}({argument_literals})"
        )
        expected_json = _java_escape_json(json.dumps(case.expected_output, separators=(",", ":")))
        input_json = json.dumps(case.input, separators=(",", ":"))
        expected_output_json = json.dumps(case.expected_output, separators=(",", ":"))
        explanation_json = _java_escape_json(case.explanation)
        serializer_name = _cpp_serializer_name(return_type)
        return_type_name = cpp_type_name(return_type)
        case_blocks.append(
            f"""
    capture.str("");
    capture.clear();
    try {{
        cout.rdbuf(capture.rdbuf());
        {return_type_name} actualValue = {call_expression};
        cout.flush();
        cout.rdbuf(originalBuffer);
        string actualJson = {serializer_name}(actualValue);
        appendCaseResult(results, {json.dumps(input_json)}, {json.dumps(expected_output_json)}, actualJson, actualJson == "{expected_json}", capture.str(), "", {json.dumps(explanation_json)});
    }} catch (const exception& error) {{
        cout.flush();
        cout.rdbuf(originalBuffer);
        appendCaseResult(results, {json.dumps(input_json)}, {json.dumps(expected_output_json)}, "null", false, capture.str(), error.what(), {json.dumps(explanation_json)});
    }}
"""
        )

    solution_instance_line = "    Solution solution;\n" if use_solution_class else ""
    case_blocks_text = "".join(case_blocks)

    return f"""#include <bits/stdc++.h>
using namespace std;

{linked_list_helpers}
#include "solution.cpp"

static string escapeJson(const string& value) {{
    string escaped;
    for (char character : value) {{
        if (character == '\\\\') escaped += "\\\\\\\\";
        else if (character == '\"') escaped += "\\\\\\"";
        else if (character == '\\n') escaped += "\\\\n";
        else if (character == '\\r') escaped += "\\\\r";
        else escaped += character;
    }}
    return escaped;
}}

static string quote(const string& value) {{
    return "\\""+ escapeJson(value) + "\\"";
}}

{serializer_defs}

static void appendCaseResult(
    vector<string>& results,
    const string& inputJson,
    const string& expectedJson,
    const string& actualJson,
    bool passed,
    const string& stdoutValue,
    const string& error,
    const string& explanation
) {{
    results.push_back(
        "{{\\"input\\":" + inputJson +
        ",\\"expected_output\\":" + expectedJson +
        ",\\"actual_output\\":" + actualJson +
        ",\\"passed\\":" + string(passed ? "true" : "false") +
        ",\\"stdout\\":" + quote(stdoutValue) +
        ",\\"error\\":" + (error.empty() ? "null" : quote(error)) +
        ",\\"explanation\\":" + quote(explanation) +
        "}}"
    );
}}

int main() {{
    vector<string> results;
    ostringstream capture;
    streambuf* originalBuffer = cout.rdbuf();
{solution_instance_line}{case_blocks_text}
    cout << "{{\\"status\\":\\"success\\",\\"error\\":null,\\"results\\":["; 
    for (size_t i = 0; i < results.size(); i++) {{
        if (i > 0) cout << ",";
        cout << results[i];
    }}
    cout << "]}}";
    return 0;
}}
"""


def execute_code(
    *,
    code: str,
    language: SupportedLanguage,
    function_name: str,
    problem_topic: str,
    runtime_shape: str,
    test_cases: list[TestCaseCreate],
    mode: str,
    timeout_seconds: int = 3,
) -> ExecutionResponse:
    if is_random_pointer_runtime_shape(runtime_shape) and language != "python":
        return _error_response(
            language=language,
            mode=mode,
            test_cases=test_cases,
            error="Random-pointer linked list problems are currently supported only in Python.",
        )

    if language == "python":
        return _execute_python(code, function_name, problem_topic, runtime_shape, test_cases, mode, timeout_seconds)
    if language == "javascript":
        return _execute_javascript(code, function_name, problem_topic, test_cases, mode, timeout_seconds)
    if language == "java":
        return _execute_java(code, function_name, problem_topic, test_cases, mode, timeout_seconds)
    if language == "cpp":
        return _execute_cpp(code, function_name, problem_topic, test_cases, mode, timeout_seconds)

    return _error_response(
        language=language,
        mode=mode,
        test_cases=test_cases,
        error=f"Unsupported language: {language}",
    )


def _execute_python(
    code: str,
    function_name: str,
    problem_topic: str,
    runtime_shape: str,
    test_cases: list[TestCaseCreate],
    mode: str,
    timeout_seconds: int,
) -> ExecutionResponse:
    with tempfile.TemporaryDirectory(prefix="dsa-python-runner-") as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "solution.py").write_text(code, encoding="utf-8")
        (temp_path / "runner.py").write_text(
            PYTHON_RUNNER_TEMPLATE.format(
                function_name=json.dumps(function_name),
                problem_topic=json.dumps(problem_topic),
                runtime_shape=json.dumps(runtime_shape),
                test_cases_json=json.dumps(json.dumps([case.model_dump() for case in test_cases])),
            ),
            encoding="utf-8",
        )
        completed = _run_subprocess(
            ["python3", str(temp_path / "runner.py")],
            cwd=temp_dir,
            timeout_seconds=timeout_seconds,
        )
        if completed is None:
            return _error_response(
                language="python",
                mode=mode,
                test_cases=test_cases,
                error=f"Execution timed out after {timeout_seconds} seconds.",
                status="timeout",
            )
        return _parse_runner_payload(language="python", mode=mode, test_cases=test_cases, completed=completed)


def _execute_javascript(
    code: str,
    function_name: str,
    problem_topic: str,
    test_cases: list[TestCaseCreate],
    mode: str,
    timeout_seconds: int,
) -> ExecutionResponse:
    with tempfile.TemporaryDirectory(prefix="dsa-js-runner-") as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "solution.js").write_text(code, encoding="utf-8")
        (temp_path / "runner.mjs").write_text(
            _javascript_runner(function_name, problem_topic, test_cases),
            encoding="utf-8",
        )
        completed = _run_subprocess(
            ["node", str(temp_path / "runner.mjs")],
            cwd=temp_dir,
            timeout_seconds=timeout_seconds,
        )
        if completed is None:
            return _error_response(
                language="javascript",
                mode=mode,
                test_cases=test_cases,
                error=f"Execution timed out after {timeout_seconds} seconds.",
                status="timeout",
            )
        return _parse_runner_payload(language="javascript", mode=mode, test_cases=test_cases, completed=completed)


def _execute_java(
    code: str,
    function_name: str,
    problem_topic: str,
    test_cases: list[TestCaseCreate],
    mode: str,
    timeout_seconds: int,
) -> ExecutionResponse:
    with tempfile.TemporaryDirectory(prefix="dsa-java-runner-") as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "Solution.java").write_text(_prepare_java_code(code), encoding="utf-8")
        (temp_path / "Runner.java").write_text(
            _java_runner(function_name, problem_topic, test_cases),
            encoding="utf-8",
        )

        compile_step = _run_subprocess(
            ["javac", "Solution.java", "Runner.java"],
            cwd=temp_dir,
            timeout_seconds=10,
        )
        if compile_step is None:
            return _error_response(
                language="java",
                mode=mode,
                test_cases=test_cases,
                error="Java compilation timed out.",
                status="timeout",
            )
        if compile_step.returncode != 0:
            return _error_response(
                language="java",
                mode=mode,
                test_cases=test_cases,
                error=compile_step.stderr.strip() or compile_step.stdout.strip() or "Java compilation failed.",
            )

        completed = _run_subprocess(["java", "Runner"], cwd=temp_dir, timeout_seconds=timeout_seconds)
        if completed is None:
            return _error_response(
                language="java",
                mode=mode,
                test_cases=test_cases,
                error=f"Execution timed out after {timeout_seconds} seconds.",
                status="timeout",
            )
        return _parse_runner_payload(language="java", mode=mode, test_cases=test_cases, completed=completed)


def _execute_cpp(
    code: str,
    function_name: str,
    problem_topic: str,
    test_cases: list[TestCaseCreate],
    mode: str,
    timeout_seconds: int,
) -> ExecutionResponse:
    with tempfile.TemporaryDirectory(prefix="dsa-cpp-runner-") as temp_dir:
        temp_path = Path(temp_dir)
        prepared_code = _prepare_cpp_code(code)
        (temp_path / "solution.cpp").write_text(prepared_code, encoding="utf-8")
        use_solution_class = bool(re.search(r"\b(class|struct)\s+Solution\b", prepared_code))
        (temp_path / "runner.cpp").write_text(
            _cpp_runner(function_name, problem_topic, test_cases, use_solution_class),
            encoding="utf-8",
        )

        compile_step = _run_subprocess(
            ["g++", "-std=c++17", "runner.cpp", "-o", "runner"],
            cwd=temp_dir,
            timeout_seconds=10,
        )
        if compile_step is None:
            return _error_response(
                language="cpp",
                mode=mode,
                test_cases=test_cases,
                error="C++ compilation timed out.",
                status="timeout",
            )
        if compile_step.returncode != 0:
            return _error_response(
                language="cpp",
                mode=mode,
                test_cases=test_cases,
                error=compile_step.stderr.strip() or compile_step.stdout.strip() or "C++ compilation failed.",
            )

        completed = _run_subprocess([str(temp_path / "runner")], cwd=temp_dir, timeout_seconds=timeout_seconds)
        if completed is None:
            return _error_response(
                language="cpp",
                mode=mode,
                test_cases=test_cases,
                error=f"Execution timed out after {timeout_seconds} seconds.",
                status="timeout",
            )
        return _parse_runner_payload(language="cpp", mode=mode, test_cases=test_cases, completed=completed)
