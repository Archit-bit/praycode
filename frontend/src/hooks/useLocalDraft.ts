import { useEffect, useState } from "react";

type StoredDraft = {
  value: string;
};

function parseStoredDraft(rawValue: string | null, initialValue: string): string | null {
  if (rawValue === null) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as StoredDraft;
    if (typeof parsed?.value === "string") {
      return parsed.value;
    }
  } catch {
    // Legacy drafts were stored as plain strings.
  }

  // Ignore legacy blank drafts if the problem now has starter code.
  if (rawValue === "" && initialValue.trim().length > 0) {
    return null;
  }

  return rawValue;
}

export function useLocalDraft(key: string, initialValue: string) {
  const [value, setValueState] = useState(initialValue);
  const [draftLoaded, setDraftLoaded] = useState(false);
  const [hasStoredDraft, setHasStoredDraft] = useState(false);
  const [hasUserEdited, setHasUserEdited] = useState(false);

  useEffect(() => {
    const storedValue = parseStoredDraft(window.localStorage.getItem(key), initialValue);
    setHasStoredDraft(storedValue !== null);
    setValueState(storedValue ?? initialValue);
    setHasUserEdited(false);
    setDraftLoaded(true);
  }, [initialValue, key]);

  useEffect(() => {
    if (!draftLoaded) {
      return;
    }

    if (!hasStoredDraft && !hasUserEdited) {
      setValueState(initialValue);
    }
  }, [draftLoaded, hasStoredDraft, hasUserEdited, initialValue]);

  useEffect(() => {
    if (!draftLoaded || !hasUserEdited) {
      return;
    }

    window.localStorage.setItem(
      key,
      JSON.stringify({
        value,
      } satisfies StoredDraft),
    );
  }, [draftLoaded, hasUserEdited, key, value]);

  const setValue = (next: string) => {
    setHasUserEdited(true);
    setValueState(next);
  };

  const reset = () => {
    setHasStoredDraft(false);
    setHasUserEdited(false);
    setValueState(initialValue);
    window.localStorage.removeItem(key);
  };

  return { value, setValue, reset };
}
