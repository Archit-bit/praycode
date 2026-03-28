export type Difficulty = "easy" | "medium" | "hard";
export type ProblemStatus = "not_started" | "attempted" | "solved";
export type SupportedLanguage = "python" | "javascript" | "java" | "cpp";
export type RuntimeShape = "plain" | "linked_list" | "random_pointer_linked_list";

export interface TestCase {
  input: unknown;
  expected_output: unknown;
  explanation: string;
}

export interface ProblemSummary {
  id: number;
  title: string;
  slug: string;
  topic: string;
  difficulty: Difficulty;
  runtime_shape: RuntimeShape;
  status: ProblemStatus;
  updated_at: string;
}

export interface ProblemDetail extends ProblemSummary {
  description: string;
  starter_code: string;
  starter_codes: Record<SupportedLanguage, string>;
  function_name: string;
  visible_test_cases: TestCase[];
  hidden_test_cases: TestCase[];
  notes: string;
  similar_questions: string;
  created_at: string;
}

export interface ProblemListResponse {
  items: ProblemSummary[];
  total: number;
}

export interface ExecutionCaseResult {
  input: unknown;
  expected_output: unknown;
  actual_output: unknown | null;
  passed: boolean;
  stdout: string;
  error: string | null;
  explanation: string;
}

export interface ExecutionResponse {
  status: "success" | "error" | "timeout";
  mode: "run" | "submit";
  language: SupportedLanguage;
  passed_count: number;
  total_count: number;
  all_passed: boolean;
  results: ExecutionCaseResult[];
  error: string | null;
}

export interface SubmissionHistoryItem {
  id: number;
  mode: string;
  language: SupportedLanguage;
  code_snapshot: string;
  results: ExecutionCaseResult[];
  passed_count: number;
  total_count: number;
  all_passed: boolean;
  error: string | null;
  created_at: string;
}

export interface ProblemPayload {
  title: string;
  slug: string;
  topic: string;
  difficulty: Difficulty;
  description: string;
  runtime_shape: RuntimeShape;
  starter_code: string;
  function_name: string;
  visible_test_cases: TestCase[];
  hidden_test_cases: TestCase[];
  notes: string;
  similar_questions: string;
}

export interface ProblemGenerationResponse {
  title: string;
  slug: string;
  topic: string;
  difficulty: Difficulty;
  description: string;
  runtime_shape: RuntimeShape;
  starter_code: string;
  starter_codes: Record<SupportedLanguage, string>;
  function_name: string;
  visible_test_cases: TestCase[];
  hidden_test_cases: TestCase[];
  generation_warnings: string[];
}
