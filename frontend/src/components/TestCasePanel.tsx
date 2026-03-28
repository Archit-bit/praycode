import type { TestCase } from "../types/problem";

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export function TestCasePanel({ testCases }: { testCases: TestCase[] }) {
  return (
    <section className="panel side-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Test Cases</p>
          <h3>Visible Checks</h3>
        </div>
      </div>

      <div className="card-stack">
        {testCases.map((testCase, index) => (
          <article key={index} className="test-card">
            <div className="test-card-title">Case {index + 1}</div>
            <div className="json-block">
              <span>Input</span>
              <pre>{formatJson(testCase.input)}</pre>
            </div>
            <div className="json-block">
              <span>Expected</span>
              <pre>{formatJson(testCase.expected_output)}</pre>
            </div>
            {testCase.explanation ? <p className="test-note">{testCase.explanation}</p> : null}
          </article>
        ))}
      </div>
    </section>
  );
}
