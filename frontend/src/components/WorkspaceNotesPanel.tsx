export function WorkspaceNotesPanel({
  notes,
  similarQuestions,
  onNotesChange,
  onSimilarQuestionsChange,
  onSave,
  isSaving,
}: {
  notes: string;
  similarQuestions: string;
  onNotesChange: (value: string) => void;
  onSimilarQuestionsChange: (value: string) => void;
  onSave: () => void;
  isSaving: boolean;
}) {
  return (
    <section className="panel notes-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Workspace Notes</p>
          <h3>Scratchpad And Similar Prompts</h3>
        </div>
        <button className="primary-button" type="button" onClick={onSave} disabled={isSaving}>
          {isSaving ? "Saving..." : "Save Notes"}
        </button>
      </div>

      <div className="notes-grid">
        <label>
          Notes
          <textarea
            className="text-area"
            rows={7}
            value={notes}
            onChange={(event) => onNotesChange(event.target.value)}
            placeholder="Write down edge cases, hints, or the approach you want to remember."
          />
        </label>
        <label>
          Similar Questions
          <textarea
            className="text-area"
            rows={7}
            value={similarQuestions}
            onChange={(event) => onSimilarQuestionsChange(event.target.value)}
            placeholder="Paste related prompts or follow-up questions here."
          />
        </label>
      </div>
    </section>
  );
}
