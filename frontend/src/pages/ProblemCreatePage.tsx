import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createProblem } from "../api/client";
import type { Difficulty, ProblemPayload, RuntimeShape } from "../types/problem";

interface EditableCase {
  input: string;
  expected_output: string;
  explanation: string;
}

function slugify(input: string) {
  return input
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function emptyCase(): EditableCase {
  return { input: "", expected_output: "", explanation: "" };
}

function inferRuntimeShape(topic: string, description: string, starterCode: string): RuntimeShape {
  const normalized = [topic, description, starterCode].join(" ").toLowerCase().replace(/-/g, " ");
  if (normalized.includes("random") && normalized.includes("linked list")) {
    return "random_pointer_linked_list";
  }
  if (normalized.includes("linked list")) {
    return "linked_list";
  }
  return "plain";
}

export function ProblemCreatePage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [topic, setTopic] = useState("Arrays");
  const [difficulty, setDifficulty] = useState<Difficulty>("easy");
  const [description, setDescription] = useState("");
  const [starterCode, setStarterCode] = useState("def solve():\n    pass\n");
  const [functionName, setFunctionName] = useState("solve");
  const [notes, setNotes] = useState("");
  const [similarQuestions, setSimilarQuestions] = useState("");
  const [visibleCases, setVisibleCases] = useState<EditableCase[]>([emptyCase()]);
  const [hiddenCases, setHiddenCases] = useState<EditableCase[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const suggestedSlug = useMemo(() => (slug ? slug : slugify(title)), [slug, title]);

  function updateCase(
    setter: React.Dispatch<React.SetStateAction<EditableCase[]>>,
    index: number,
    field: keyof EditableCase,
    value: string,
  ) {
    setter((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, [field]: value } : item)));
  }

  function parseCases(cases: EditableCase[]) {
    return cases
      .filter((item) => item.input.trim() && item.expected_output.trim())
      .map((item) => ({
        input: JSON.parse(item.input),
        expected_output: JSON.parse(item.expected_output),
        explanation: item.explanation,
      }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSaving(true);

    try {
      const payload: ProblemPayload = {
        title,
        slug: suggestedSlug,
        topic,
        difficulty,
        description,
        runtime_shape: inferRuntimeShape(topic, description, starterCode),
        starter_code: starterCode,
        function_name: functionName,
        visible_test_cases: parseCases(visibleCases),
        hidden_test_cases: parseCases(hiddenCases),
        notes,
        similar_questions: similarQuestions,
      };

      if (payload.visible_test_cases.length === 0) {
        throw new Error("Add at least one visible test case.");
      }

      const problem = await createProblem(payload);
      navigate(`/problems/${problem.slug}`);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Failed to create the problem. Check your JSON test case inputs.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="page-shell">
      <section className="hero-card compact-hero">
        <div>
          <div className="brand-kicker-row">
            <span className="brand-mark">P</span>
            <p className="eyebrow">PrayCode Manual Entry</p>
          </div>
          <h1>Create a new practice problem</h1>
          <p className="hero-copy">
            Paste a prompt-generated problem, define its function signature, and add the test cases you want to run.
          </p>
          <p className="helper-copy">In DSA we trust. In cursed examples we debug.</p>
        </div>
      </section>

      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          Title
          <input className="text-input" value={title} onChange={(event) => setTitle(event.target.value)} required />
        </label>
        <label>
          Slug
          <input className="text-input" value={suggestedSlug} onChange={(event) => setSlug(slugify(event.target.value))} />
        </label>
        <label>
          Topic
          <input className="text-input" value={topic} onChange={(event) => setTopic(event.target.value)} required />
        </label>
        <label>
          Difficulty
          <select
            className="text-input"
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value as Difficulty)}
          >
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </label>
        <label>
          Function Name
          <input
            className="text-input"
            value={functionName}
            onChange={(event) => setFunctionName(event.target.value)}
            required
          />
        </label>
        <label className="full-span">
          Description
          <textarea
            className="text-area"
            rows={16}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Paste the problem statement, examples, and constraints."
            required
          />
        </label>
        <label className="full-span">
          Starter Code
          <textarea
            className="code-area"
            rows={10}
            value={starterCode}
            onChange={(event) => setStarterCode(event.target.value)}
            required
          />
        </label>
        <label className="full-span">
          Notes
          <textarea className="text-area" rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <label className="full-span">
          Similar Questions
          <textarea
            className="text-area"
            rows={4}
            value={similarQuestions}
            onChange={(event) => setSimilarQuestions(event.target.value)}
          />
        </label>

        <section className="full-span testcase-editor">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Visible Test Cases</p>
              <h3>Shown in the workspace</h3>
            </div>
            <button type="button" className="ghost-button" onClick={() => setVisibleCases((current) => [...current, emptyCase()])}>
              Add visible case
            </button>
          </div>
          {visibleCases.map((item, index) => (
            <div className="case-row" key={`visible-${index}`}>
              <textarea
                className="code-area"
                rows={5}
                placeholder='Input JSON, for example [[2,7,11,15], 9]'
                value={item.input}
                onChange={(event) => updateCase(setVisibleCases, index, "input", event.target.value)}
              />
              <textarea
                className="code-area"
                rows={5}
                placeholder='Expected JSON, for example [0, 1]'
                value={item.expected_output}
                onChange={(event) => updateCase(setVisibleCases, index, "expected_output", event.target.value)}
              />
              <input
                className="text-input"
                placeholder="Optional explanation"
                value={item.explanation}
                onChange={(event) => updateCase(setVisibleCases, index, "explanation", event.target.value)}
              />
            </div>
          ))}
        </section>

        <section className="full-span testcase-editor">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Hidden Test Cases</p>
              <h3>Used only on submit</h3>
            </div>
            <button type="button" className="ghost-button" onClick={() => setHiddenCases((current) => [...current, emptyCase()])}>
              Add hidden case
            </button>
          </div>
          {hiddenCases.length === 0 ? <p className="subtle-copy">No hidden cases yet. That is fine for the MVP.</p> : null}
          {hiddenCases.map((item, index) => (
            <div className="case-row" key={`hidden-${index}`}>
              <textarea
                className="code-area"
                rows={5}
                placeholder='Input JSON, for example ["()[]{}"]'
                value={item.input}
                onChange={(event) => updateCase(setHiddenCases, index, "input", event.target.value)}
              />
              <textarea
                className="code-area"
                rows={5}
                placeholder="Expected JSON"
                value={item.expected_output}
                onChange={(event) => updateCase(setHiddenCases, index, "expected_output", event.target.value)}
              />
              <input
                className="text-input"
                placeholder="Optional explanation"
                value={item.explanation}
                onChange={(event) => updateCase(setHiddenCases, index, "explanation", event.target.value)}
              />
            </div>
          ))}
        </section>

        {error ? <div className="error-box full-span">{error}</div> : null}

        <div className="form-actions full-span">
          <button type="submit" className="primary-button" disabled={isSaving}>
            {isSaving ? "Saving..." : "Create Problem"}
          </button>
        </div>
      </form>
    </div>
  );
}
