import type {
  ExecutionResponse,
  ProblemDetail,
  ProblemGenerationResponse,
  ProblemListResponse,
  ProblemPayload,
  ProblemStatus,
  SubmissionHistoryItem,
  SupportedLanguage,
} from "../types/problem";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchProblems(params?: {
  search?: string;
  topic?: string;
  difficulty?: string;
  status?: string;
}): Promise<ProblemListResponse> {
  const query = new URLSearchParams();

  if (params?.search) query.set("search", params.search);
  if (params?.topic) query.set("topic", params.topic);
  if (params?.difficulty) query.set("difficulty", params.difficulty);
  if (params?.status) query.set("status", params.status);

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<ProblemListResponse>(`/problems${suffix}`);
}

export async function fetchProblem(slug: string): Promise<ProblemDetail> {
  return request<ProblemDetail>(`/problems/${slug}`);
}

export async function createProblem(payload: ProblemPayload): Promise<ProblemDetail> {
  return request<ProblemDetail>("/problems", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function generateProblemDraft(problemStatement: string): Promise<ProblemGenerationResponse> {
  return request<ProblemGenerationResponse>("/problems/generate", {
    method: "POST",
    body: JSON.stringify({ problem_statement: problemStatement }),
  });
}

export async function runProblem(
  slug: string,
  code: string,
  language: SupportedLanguage,
): Promise<ExecutionResponse> {
  return request<ExecutionResponse>(`/problems/${slug}/run`, {
    method: "POST",
    body: JSON.stringify({ code, language }),
  });
}

export async function submitProblem(
  slug: string,
  code: string,
  language: SupportedLanguage,
): Promise<ExecutionResponse> {
  return request<ExecutionResponse>(`/problems/${slug}/submit`, {
    method: "POST",
    body: JSON.stringify({ code, language }),
  });
}

export async function updateProblemStatus(slug: string, status: ProblemStatus) {
  return request(`/problems/${slug}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function updateProblemWorkspace(
  slug: string,
  payload: { notes: string; similar_questions: string },
): Promise<ProblemDetail> {
  return request<ProblemDetail>(`/problems/${slug}/workspace`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function fetchProblemSubmissions(slug: string): Promise<SubmissionHistoryItem[]> {
  return request<SubmissionHistoryItem[]>(`/problems/${slug}/submissions`);
}
