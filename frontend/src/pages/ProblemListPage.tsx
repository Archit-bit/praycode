import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { createProblem, fetchProblems, generateProblemDraft } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import type { ProblemGenerationResponse, ProblemSummary } from "../types/problem";

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export function ProblemListPage() {
  const navigate = useNavigate();
  const [problemStatement, setProblemStatement] = useState("");
  const [generatedDraft, setGeneratedDraft] = useState<ProblemGenerationResponse | null>(null);
  const [items, setItems] = useState<ProblemSummary[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const generationRequestId = useRef(0);
  const lastGeneratedInput = useRef("");

  useEffect(() => {
    async function loadProblems() {
      try {
        const response = await fetchProblems();
        setItems(response.items);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load problems.");
      } finally {
        setLoading(false);
      }
    }

    void loadProblems();
  }, []);

  useEffect(() => {
    const trimmed = problemStatement.trim();

    if (!trimmed) {
      setGeneratedDraft(null);
      setIsGenerating(false);
      setError(null);
      lastGeneratedInput.current = "";
      return;
    }

    if (trimmed.length < 20) {
      setGeneratedDraft(null);
      setIsGenerating(false);
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      if (lastGeneratedInput.current === trimmed) {
        return;
      }

      const requestId = generationRequestId.current + 1;
      generationRequestId.current = requestId;
      setIsGenerating(true);
      setError(null);

      try {
        const response = await generateProblemDraft(trimmed);
        if (generationRequestId.current !== requestId) {
          return;
        }

        lastGeneratedInput.current = trimmed;
        setGeneratedDraft(response);
      } catch (generationError) {
        if (generationRequestId.current !== requestId) {
          return;
        }

        setGeneratedDraft(null);
        setError(generationError instanceof Error ? generationError.message : "Codex could not generate a draft.");
      } finally {
        if (generationRequestId.current === requestId) {
          setIsGenerating(false);
        }
      }
    }, 900);

    return () => window.clearTimeout(timeoutId);
  }, [problemStatement]);

  const filteredItems = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) {
      return items;
    }

    return items.filter((item) => item.title.toLowerCase().includes(term) || item.topic.toLowerCase().includes(term));
  }, [items, search]);

  async function handleSaveAndOpen() {
    if (!generatedDraft) {
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const { generation_warnings: _warnings, ...problemDraft } = generatedDraft;
      let slug = generatedDraft.slug;
      let created = null;

      try {
        created = await createProblem({
          ...problemDraft,
          slug,
          notes: "",
          similar_questions: "",
        });
      } catch (createError) {
        const message = createError instanceof Error ? createError.message : "";
        if (!message.includes("already exists") && !message.includes("409")) {
          throw createError;
        }

        slug = `${generatedDraft.slug}-${Date.now().toString().slice(-4)}`;
        created = await createProblem({
          ...problemDraft,
          slug,
          notes: "",
          similar_questions: "",
        });
      }

      navigate(`/problems/${created.slug}`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save the generated problem.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="simple-page">
      <header className="simple-topbar brand-hero">
        <div className="brand-copy">
          <div className="brand-kicker-row">
            <span className="brand-mark">P</span>
            <p className="muted-label">PrayCode</p>
          </div>
          <h1>Cooked problem. Calm hands.</h1>
          <p className="brand-subtitle">
            In DSA we trust. Codex handles the setup, you lock in and beat the test cases.
          </p>
          <div className="brand-stats">
            <span className="brand-chip">Zero boilerplate vibes</span>
            <span className="brand-chip">Python, JS, Java, C++</span>
            <span className="brand-chip">{items.length} locked-in drills</span>
          </div>
        </div>
      </header>

      {error ? <div className="simple-error">{error}</div> : null}

      <div className="home-grid">
        <section className="simple-card composer-card">
          <div className="section-head">
            <div>
              <p className="muted-label">Step 1</p>
              <h2>Add problem statement</h2>
            </div>
          </div>

          <textarea
            className="simple-textarea problem-input"
            rows={18}
            value={problemStatement}
            onChange={(event) => {
              setProblemStatement(event.target.value);
              setGeneratedDraft(null);
              setError(null);
            }}
            placeholder="Paste a full DSA problem here from ChatGPT. Codex will infer the function signature and generate test cases."
          />

          <div className="status-line">
            {!problemStatement.trim() ? (
              <span>Paste a problem statement and PrayCode will start cooking the runner.</span>
            ) : problemStatement.trim().length < 20 ? (
              <span>Add a bit more detail and Codex will auto-spin the test cases.</span>
            ) : isGenerating ? (
              <span>Generating starter code, function signature, and test cases...</span>
            ) : generatedDraft ? (
              <span>Draft ready. Sanity check it below and open the arena when it looks clean.</span>
            ) : (
              <span>Waiting for Codex generation...</span>
            )}
          </div>

          <div className="inline-actions">
            <button
              className="ghost-button"
              type="button"
              onClick={() => {
                setProblemStatement("");
                setGeneratedDraft(null);
                setError(null);
                setIsGenerating(false);
                lastGeneratedInput.current = "";
              }}
            >
              Clear
            </button>
          </div>

          {generatedDraft ? (
            <div className="draft-preview">
              <div className="section-head">
                <div>
                  <p className="muted-label">Step 2</p>
                  <h2>{generatedDraft.title}</h2>
                </div>
                <button className="primary-button" type="button" onClick={handleSaveAndOpen} disabled={isSaving}>
                  {isSaving ? "Saving..." : "Save And Open"}
                </button>
              </div>

              <div className="meta-row">
                <span className="meta-pill">{generatedDraft.topic}</span>
                <span className={`difficulty-pill difficulty-${generatedDraft.difficulty}`}>{generatedDraft.difficulty}</span>
                <span className="meta-pill">Function: {generatedDraft.function_name}</span>
              </div>

              <p className="helper-copy">
                Codex generated these visible cases. Save it and the workspace opens with the editor, runner, and starter code ready.
              </p>

              {generatedDraft.generation_warnings.length > 0 ? (
                <div className="simple-details generation-warning-box">
                  <strong>Auto-corrections</strong>
                  {generatedDraft.generation_warnings.map((warning, index) => (
                    <p key={index} className="helper-copy">
                      {warning}
                    </p>
                  ))}
                </div>
              ) : null}

              <div className="case-list">
                {generatedDraft.visible_test_cases.map((testCase, index) => (
                  <article key={index} className="case-item">
                    <strong>Case {index + 1}</strong>
                    <pre>{formatJson(testCase.input)}</pre>
                    <pre>{formatJson(testCase.expected_output)}</pre>
                    {testCase.explanation ? <p>{testCase.explanation}</p> : null}
                  </article>
                ))}
              </div>
            </div>
          ) : null}
        </section>

        <section className="simple-card library-card">
          <div className="section-head">
            <div>
              <p className="muted-label">My Problems</p>
              <h2>Practice Library</h2>
            </div>
            <span className="meta-pill">{items.length}</span>
          </div>

          <input
            className="simple-input"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by title or topic"
          />

          {loading ? <div className="simple-empty">Loading problems...</div> : null}

          {!loading && filteredItems.length === 0 ? <div className="simple-empty">No problems found.</div> : null}

          <div className="problem-list">
            {filteredItems.map((problem) => (
              <Link key={problem.slug} to={`/problems/${problem.slug}`} className="problem-row">
                <div>
                  <strong>{problem.title}</strong>
                  <div className="row-subtext">
                    <span>{problem.topic}</span>
                    <span>•</span>
                    <span>{problem.difficulty}</span>
                  </div>
                </div>
                <StatusBadge status={problem.status} />
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
