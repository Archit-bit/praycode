import Editor from "@monaco-editor/react";

import type { SupportedLanguage } from "../types/problem";

export function CodeEditor({
  value,
  onChange,
  language,
  showHeader = true,
}: {
  value: string;
  onChange: (next: string) => void;
  language: SupportedLanguage;
  showHeader?: boolean;
}) {
  return (
    <div className="panel editor-panel">
      {showHeader ? (
        <div className="panel-header">
          <div>
            <p className="eyebrow">Editor</p>
            <h3>{language[0].toUpperCase() + language.slice(1)} Workspace</h3>
          </div>
        </div>
      ) : null}
      <div className="editor-shell">
        <Editor
          height="100%"
          defaultLanguage={language}
          language={language}
          theme="vs-dark"
          value={value}
          onChange={(next) => onChange(next ?? "")}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 16 },
          }}
        />
      </div>
    </div>
  );
}
