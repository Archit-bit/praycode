import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  fetchProblem,
  fetchProblemSubmissions,
  runProblem,
  submitProblem,
  updateProblemWorkspace,
} from "../api/client";
import { CodeEditor } from "../components/CodeEditor";
import { StatusBadge } from "../components/StatusBadge";
import { useLocalDraft } from "../hooks/useLocalDraft";
import type {
  ExecutionResponse,
  ProblemDetail,
  RuntimeShape,
  SubmissionHistoryItem,
  SupportedLanguage,
  TestCase,
} from "../types/problem";

type LeftTab = "question" | "notes" | "submissions";
type BottomTab = "testcases" | "output";

type DisplayField = {
  label: string;
  value: unknown;
};

const LANGUAGE_OPTIONS: Array<{ value: SupportedLanguage; label: string }> = [
  { value: "python", label: "Python" },
  { value: "javascript", label: "JavaScript" },
  { value: "java", label: "Java" },
  { value: "cpp", label: "C++" },
];

function normalizeLanguage(value: string | null): SupportedLanguage {
  if (value === "python" || value === "javascript" || value === "java" || value === "cpp") {
    return value;
  }
  return "python";
}

function isLinkedListTopic(topic: string) {
  return topic.trim().toLowerCase().replace(/-/g, " ").includes("linked list");
}

function supportsLanguageForRuntimeShape(language: SupportedLanguage, runtimeShape: RuntimeShape) {
  if (runtimeShape === "random_pointer_linked_list") {
    return language === "python";
  }
  return true;
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractParameterNames(starterCode: string, functionName: string, language: SupportedLanguage) {
  const patterns: Record<SupportedLanguage, RegExp[]> = {
    python: [new RegExp(`def\\s+${escapeRegExp(functionName)}\\s*\\(([^)]*)\\)`)],
    javascript: [
      new RegExp(`function\\s+${escapeRegExp(functionName)}\\s*\\(([^)]*)\\)`),
      new RegExp(`${escapeRegExp(functionName)}\\s*\\(([^)]*)\\)\\s*\\{`),
    ],
    java: [new RegExp(`${escapeRegExp(functionName)}\\s*\\(([^)]*)\\)\\s*\\{`)],
    cpp: [new RegExp(`${escapeRegExp(functionName)}\\s*\\(([^)]*)\\)\\s*\\{`)],
  };

  const signatureMatch = patterns[language]
    .map((pattern) => starterCode.match(pattern))
    .find((match): match is RegExpMatchArray => match !== null);

  if (!signatureMatch) {
    return [];
  }

  return signatureMatch[1]
    .split(",")
    .map((rawParam) => rawParam.trim())
    .filter((rawParam) => rawParam.length > 0)
    .map((rawParam) =>
      rawParam
        .replace(/=.*/, "")
        .replace(/:.*/, "")
        .replace(/\b(const|final)\b/g, "")
        .replace(/[<>\[\]?]/g, " ")
        .trim(),
    )
    .map((rawParam) => rawParam.split(/\s+/).filter(Boolean).pop() ?? rawParam)
    .filter((name) => name !== "self" && name !== "cls" && name !== "/" && name !== "*");
}

function getParameterNamesForProblem(
  problem: ProblemDetail | null,
  starterCode: string,
  selectedLanguage: SupportedLanguage,
) {
  if (!problem) {
    return [];
  }

  const names = extractParameterNames(starterCode, problem.function_name, selectedLanguage);
  const isLinkedListShape =
    problem.runtime_shape === "linked_list" ||
    problem.runtime_shape === "random_pointer_linked_list" ||
    isLinkedListTopic(problem.topic);

  if (isLinkedListShape) {
    if (names.length === 0) {
      return ["head"];
    }

    if (names.length === 1) {
      return ["head"];
    }
  }

  return names;
}

function formatInlineValue(value: unknown): string {
  if (typeof value === "string") {
    return JSON.stringify(value);
  }

  if (typeof value === "number" || typeof value === "boolean" || value === null) {
    return String(value);
  }

  if (Array.isArray(value)) {
    return `[${value.map((item) => formatInlineValue(item)).join(", ")}]`;
  }

  if (typeof value === "object" && value) {
    return `{${Object.entries(value as Record<string, unknown>)
      .map(([key, itemValue]) => `${JSON.stringify(key)}: ${formatInlineValue(itemValue)}`)
      .join(", ")}}`;
  }

  return String(value);
}

function getDisplayFields(input: unknown, parameterNames: string[]): DisplayField[] {
  if (Array.isArray(input)) {
    return input.map((value, index) => ({
      label: parameterNames[index] ?? `arg${index + 1}`,
      value,
    }));
  }

  if (typeof input === "object" && input !== null) {
    return Object.entries(input as Record<string, unknown>).map(([key, value]) => ({
      label: key,
      value,
    }));
  }

  return [
    {
      label: parameterNames[0] ?? "input",
      value: input,
    },
  ];
}

export function ProblemWorkspacePage() {
  const { slug = "" } = useParams();
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [result, setResult] = useState<ExecutionResponse | null>(null);
  const [submissionHistory, setSubmissionHistory] = useState<SubmissionHistoryItem[]>([]);
  const [notesDraft, setNotesDraft] = useState("");
  const [similarQuestionsDraft, setSimilarQuestionsDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [leftTab, setLeftTab] = useState<LeftTab>("question");
  const [bottomTab, setBottomTab] = useState<BottomTab>("testcases");
  const [selectedCaseIndex, setSelectedCaseIndex] = useState(0);
  const [selectedLanguage, setSelectedLanguage] = useState<SupportedLanguage>(() => {
    if (typeof window === "undefined") {
      return "python";
    }

    return normalizeLanguage(window.localStorage.getItem("dsa-practice-language"));
  });

  useEffect(() => {
    async function loadWorkspace() {
      setLoading(true);
      setError(null);

      try {
        const [problemResponse, historyResponse] = await Promise.all([
          fetchProblem(slug),
          fetchProblemSubmissions(slug),
        ]);
        setProblem(problemResponse);
        setSubmissionHistory(historyResponse);
        setNotesDraft(problemResponse.notes);
        setSimilarQuestionsDraft(problemResponse.similar_questions);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load this problem.");
      } finally {
        setLoading(false);
      }
    }

    void loadWorkspace();
  }, [slug]);

  useEffect(() => {
    window.localStorage.setItem("dsa-practice-language", selectedLanguage);
  }, [selectedLanguage]);

  const starterCodeForLanguage = useMemo(() => {
    if (!problem) {
      return "";
    }

    return problem.starter_codes[selectedLanguage] ?? problem.starter_code;
  }, [problem, selectedLanguage]);

  const availableLanguageOptions = useMemo(() => {
    if (!problem) {
      return LANGUAGE_OPTIONS;
    }

    return LANGUAGE_OPTIONS.filter((option) => supportsLanguageForRuntimeShape(option.value, problem.runtime_shape));
  }, [problem]);

  useEffect(() => {
    if (!problem) {
      return;
    }

    if (!supportsLanguageForRuntimeShape(selectedLanguage, problem.runtime_shape)) {
      setSelectedLanguage("python");
    }
  }, [problem, selectedLanguage]);

  const draftKey = useMemo(() => `dsa-practice-draft:${slug}:${selectedLanguage}`, [selectedLanguage, slug]);
  const { value: code, setValue: setCode, reset } = useLocalDraft(draftKey, starterCodeForLanguage);
  const parameterNames = useMemo(
    () => getParameterNamesForProblem(problem, starterCodeForLanguage, selectedLanguage),
    [problem, selectedLanguage, starterCodeForLanguage],
  );

  const visibleCases = problem?.visible_test_cases ?? [];
  const outputCases = result?.results ?? [];
  const activeVisibleCase = visibleCases[Math.min(selectedCaseIndex, Math.max(visibleCases.length - 1, 0))] ?? null;
  const activeOutputCase = outputCases[Math.min(selectedCaseIndex, Math.max(outputCases.length - 1, 0))] ?? null;

  async function execute(mode: "run" | "submit") {
    if (!problem) {
      return;
    }

    setIsRunning(true);
    setError(null);

    try {
      const response =
        mode === "run"
          ? await runProblem(problem.slug, code, selectedLanguage)
          : await submitProblem(problem.slug, code, selectedLanguage);
      setResult(response);
      setBottomTab("output");
      setSelectedCaseIndex(0);

      if (mode === "submit") {
        const [refreshedProblem, refreshedHistory] = await Promise.all([
          fetchProblem(problem.slug),
          fetchProblemSubmissions(problem.slug),
        ]);
        setProblem(refreshedProblem);
        setSubmissionHistory(refreshedHistory);
      }
    } catch (executionError) {
      setError(executionError instanceof Error ? executionError.message : "Execution failed.");
    } finally {
      setIsRunning(false);
    }
  }

  async function handleSaveNotes() {
    if (!problem) {
      return;
    }

    setIsSavingNotes(true);
    setError(null);

    try {
      const updatedProblem = await updateProblemWorkspace(problem.slug, {
        notes: notesDraft,
        similar_questions: similarQuestionsDraft,
      });
      setProblem(updatedProblem);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save notes.");
    } finally {
      setIsSavingNotes(false);
    }
  }

  function loadSubmission(item: SubmissionHistoryItem) {
    const nextDraftKey = `dsa-practice-draft:${slug}:${item.language}`;
    window.localStorage.setItem(
      nextDraftKey,
      JSON.stringify({
        value: item.code_snapshot,
      }),
    );
    setSelectedLanguage(item.language);
    if (item.language === selectedLanguage) {
      setCode(item.code_snapshot);
    }
  }

  function renderInputFields(input: unknown) {
    const fields = getDisplayFields(input, parameterNames);

    return (
      <div className="nc-arg-stack">
        {fields.map((field, index) => (
          <div key={`${field.label}-${index}`} className="nc-arg-row">
            <label className="nc-arg-label">{field.label} =</label>
            <div className="nc-arg-field">{formatInlineValue(field.value)}</div>
          </div>
        ))}
      </div>
    );
  }

  function renderQuestionPane(currentProblem: ProblemDetail) {
    const languageLabel = LANGUAGE_OPTIONS.find((option) => option.value === selectedLanguage)?.label ?? selectedLanguage;

    return (
      <div className="nc-scroll">
        <div className="nc-question-head">
          <h1>{currentProblem.title}</h1>
          <span className={`difficulty-pill difficulty-${currentProblem.difficulty}`}>{currentProblem.difficulty}</span>
        </div>
        <div className="nc-question-tags">
          <span className="meta-pill">{currentProblem.topic}</span>
          <StatusBadge status={currentProblem.status} />
          <span className="meta-pill">{languageLabel}</span>
        </div>
        <div className="nc-question-body">{currentProblem.description}</div>
      </div>
    );
  }

  function renderNotesPane() {
    return (
      <div className="nc-scroll">
        <div className="nc-subpanel-title">Notes</div>
        <textarea
          className="simple-textarea"
          rows={8}
          value={notesDraft}
          onChange={(event) => setNotesDraft(event.target.value)}
          placeholder="Write your approach, edge cases, or reminders."
        />
        <div className="nc-subpanel-title top-gap">Similar questions</div>
        <textarea
          className="simple-textarea"
          rows={8}
          value={similarQuestionsDraft}
          onChange={(event) => setSimilarQuestionsDraft(event.target.value)}
          placeholder="Paste related prompts or variants."
        />
        <div className="inline-actions">
          <button className="primary-button" type="button" onClick={handleSaveNotes} disabled={isSavingNotes}>
            {isSavingNotes ? "Saving..." : "Save Notes"}
          </button>
        </div>
      </div>
    );
  }

  function renderSubmissionsPane() {
    return (
      <div className="nc-scroll">
        {submissionHistory.length === 0 ? <div className="simple-empty">No submissions yet.</div> : null}
        <div className="history-list">
          {submissionHistory.map((item) => (
            <article key={item.id} className="history-row">
              <div>
                <strong>{new Date(item.created_at).toLocaleString()}</strong>
                <div className="row-subtext">
                  <span>{item.passed_count}/{item.total_count} passed</span>
                  <span>•</span>
                  <span>{item.all_passed ? "Accepted" : "Needs work"}</span>
                  <span>•</span>
                  <span>{LANGUAGE_OPTIONS.find((option) => option.value === item.language)?.label ?? item.language}</span>
                </div>
              </div>
              <button className="ghost-button" type="button" onClick={() => loadSubmission(item)}>
                Load code
              </button>
            </article>
          ))}
        </div>
      </div>
    );
  }

  function renderTestCaseView(testCase: TestCase | null) {
    if (!testCase) {
      return <div className="simple-empty">No visible test cases available.</div>;
    }

    return (
      <div className="nc-case-panel">
        <div className="nc-case-tabs">
          {visibleCases.map((_, index) => (
            <button
              key={index}
              type="button"
              className={`nc-case-tab ${selectedCaseIndex === index ? "active" : ""}`}
              onClick={() => setSelectedCaseIndex(index)}
            >
              Case {index + 1}
            </button>
          ))}
        </div>
        <div className="nc-io-stack">
          <div className="nc-io-block">
            <span>Input</span>
            {renderInputFields(testCase.input)}
          </div>
          <div className="nc-io-block">
            <span>Expected</span>
            <div className="nc-arg-field nc-value-field">{formatInlineValue(testCase.expected_output)}</div>
          </div>
          {testCase.explanation ? <p className="helper-copy">{testCase.explanation}</p> : null}
        </div>
      </div>
    );
  }

  function renderOutputView() {
    if (isRunning) {
      return <div className="simple-empty">Running code...</div>;
    }

    if (!result) {
      return <div className="simple-empty">Run your code to see output here.</div>;
    }

    const summary = (
      <div className="nc-bottom-summary">
        <span className={`result-pill ${result.all_passed ? "success" : "warning"}`}>
          {result.passed_count}/{result.total_count} passed
        </span>
        <span className="row-subtext">{result.mode === "submit" ? "Latest submit result" : "Latest run result"}</span>
      </div>
    );

    if (!activeOutputCase) {
      return (
        <div className="nc-case-panel">
          {summary}
          <div className="nc-output-card fail">
            {result.error ? (
              <div className="simple-error">{result.error}</div>
            ) : (
              <div className="simple-empty">No case results were returned.</div>
            )}
          </div>
        </div>
      );
    }

    return (
      <div className="nc-case-panel">
        {summary}
        <div className="nc-case-tabs">
          {outputCases.map((item, index) => (
            <button
              key={index}
              type="button"
              className={`nc-case-tab ${selectedCaseIndex === index ? "active" : ""}`}
              onClick={() => setSelectedCaseIndex(index)}
            >
              Case {index + 1} {item.passed ? "✓" : "×"}
            </button>
          ))}
        </div>
        <div className={`nc-output-card ${activeOutputCase.passed ? "pass" : "fail"}`}>
          <div className="nc-output-header">
            <strong>Case {selectedCaseIndex + 1}</strong>
            <span>{activeOutputCase.passed ? "Passed" : "Failed"}</span>
          </div>
          <div className="nc-io-block">
            <span>Input</span>
            {renderInputFields(activeOutputCase.input)}
          </div>
          <div className="nc-io-grid">
            <div className="nc-io-block">
              <span>Expected</span>
              <div className="nc-arg-field nc-value-field">{formatInlineValue(activeOutputCase.expected_output)}</div>
            </div>
            <div className="nc-io-block">
              <span>Actual</span>
              <div className="nc-arg-field nc-value-field">{formatInlineValue(activeOutputCase.actual_output)}</div>
            </div>
          </div>
          {activeOutputCase.stdout ? (
            <div className="nc-io-block">
              <span>Stdout</span>
              <pre>{activeOutputCase.stdout}</pre>
            </div>
          ) : null}
          {activeOutputCase.error ? <div className="simple-error">{activeOutputCase.error}</div> : null}
          {result.error ? <div className="simple-error">{result.error}</div> : null}
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="simple-page"><div className="simple-empty">Loading workspace...</div></div>;
  }

  if (!problem) {
    return (
      <div className="simple-page">
        <div className="simple-error">{error ?? "Problem not found."}</div>
        <Link to="/" className="ghost-button">
          Back Home
        </Link>
      </div>
    );
  }

  return (
    <div className="nc-page">
      <header className="nc-topbar">
        <div className="nc-topbar-left">
          <Link to="/" className="nc-top-link brand-home-link">
            <span className="brand-mark small">P</span>
            <span>PrayCode</span>
          </Link>
          <div className="nc-topbar-copy">
            <div className="nc-topbar-title">{problem.title}</div>
            <div className="nc-topbar-subtitle">In DSA we trust. In edge cases we lock in.</div>
          </div>
        </div>
        <div className="nc-topbar-actions">
          <button className="ghost-button" type="button" onClick={reset}>
            Reset Draft
          </button>
          <button className="ghost-button" type="button" onClick={() => execute("run")} disabled={isRunning}>
            {isRunning ? "Running..." : "Run"}
          </button>
          <button className="primary-button" type="button" onClick={() => execute("submit")} disabled={isRunning}>
            {isRunning ? "Submitting..." : "Submit"}
          </button>
        </div>
      </header>

      {error ? <div className="simple-error">{error}</div> : null}

      <div className="nc-workspace">
        <aside className="nc-sidebar">
          <div className="nc-panel-tabs">
            <button
              type="button"
              className={`nc-panel-tab ${leftTab === "question" ? "active" : ""}`}
              onClick={() => setLeftTab("question")}
            >
              Question
            </button>
            <button
              type="button"
              className={`nc-panel-tab ${leftTab === "notes" ? "active" : ""}`}
              onClick={() => setLeftTab("notes")}
            >
              Notes
            </button>
            <button
              type="button"
              className={`nc-panel-tab ${leftTab === "submissions" ? "active" : ""}`}
              onClick={() => setLeftTab("submissions")}
            >
              Submissions
            </button>
          </div>
          <div className="nc-sidebar-body">
            {leftTab === "question" ? renderQuestionPane(problem) : null}
            {leftTab === "notes" ? renderNotesPane() : null}
            {leftTab === "submissions" ? renderSubmissionsPane() : null}
          </div>
        </aside>

        <section className="nc-main">
          <div className="nc-editor-wrap">
            <div className="nc-editor-toolbar">
              <label className="nc-language-picker">
                <select
                  className="nc-language-select"
                  value={selectedLanguage}
                  onChange={(event) => setSelectedLanguage(event.target.value as SupportedLanguage)}
                >
                  {availableLanguageOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <span className="meta-pill">Function: {problem.function_name}</span>
            </div>
            {problem.runtime_shape === "random_pointer_linked_list" ? (
              <p className="helper-copy">This problem shape currently runs in Python only.</p>
            ) : null}
            <CodeEditor value={code} onChange={setCode} language={selectedLanguage} showHeader={false} />
          </div>

          <div className="nc-bottom-panel">
            <div className="nc-panel-tabs">
              <button
                type="button"
                className={`nc-panel-tab ${bottomTab === "testcases" ? "active" : ""}`}
                onClick={() => {
                  setBottomTab("testcases");
                  setSelectedCaseIndex(0);
                }}
              >
                Test Cases
              </button>
              <button
                type="button"
                className={`nc-panel-tab ${bottomTab === "output" ? "active" : ""}`}
                onClick={() => {
                  setBottomTab("output");
                  setSelectedCaseIndex(0);
                }}
              >
                Output
              </button>
            </div>
            <div className="nc-bottom-body">
              {bottomTab === "testcases" ? renderTestCaseView(activeVisibleCase) : renderOutputView()}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
