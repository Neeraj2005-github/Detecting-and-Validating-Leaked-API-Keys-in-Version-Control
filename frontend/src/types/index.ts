export type Finding = {
  id: string;
  secret_type: string;
  repository: string;
  file_path: string;
  commit_sha: string;
  last_checked: string;
  masked_hash: string;
};

export type Repository = {
  id: string;
  url: string;
  last_scan: string | null;
  finding_count?: number | null;
};

export type SummaryMetrics = {
  total: number;
  true_secrets_confirmed: number;
  false_positives_filtered: number;
  detector_types_covered: number;
};
