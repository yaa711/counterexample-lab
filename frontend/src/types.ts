export type Case = { numbers: number[]; target?: number };
export type Status =
  | "passed"
  | "wrong_answer"
  | "exception"
  | "timeout"
  | "invalid_output"
  | "infrastructure_error"
  | "incomplete";
export type Source = {
  mode: "demo" | "custom";
  variant: string | null;
  code: string;
  sha256: string;
  provenance: string;
};
export type Task = {
  id: string;
  name: string;
  tag: string;
  level: string;
  description: string;
  signature: string;
  bug: string;
  buggy: string;
  correct: string;
  provenance: string;
};
export type Health = {
  runner: { available: boolean; reason: string };
  version: string;
};
export type Failure = {
  input: Case;
  expected: number | number[];
  actual: unknown;
  status: Status;
  message?: string;
};
export type Step = Failure & { reason: string; call: number };
export type Shrink = {
  stable: boolean;
  steps: Step[];
  calls: number;
  budget: number;
  stop_reason: string;
  reduced: Failure;
  claim: string;
  evaluated_inputs: Case[];
};
export type Report = {
  schema_version: string;
  run_id: string;
  task: string;
  seed: number;
  requested: number;
  tested: number;
  status: Status;
  failure: Failure | null;
  shrink: Shrink | null;
  elapsed_ms: number;
  source: Source;
  prompts: Record<string, string>;
  tested_inputs: Case[];
  created_at: string;
};
export type Verification = {
  run_id: string;
  status: Status;
  seed: number;
  requested: number;
  tested: number;
  passed: number;
  overlap_count: number;
  excluded_count: number;
  elapsed_ms: number;
  failures: Failure[];
  source: Source;
  claim: string;
};
