export type Finding = {
  id: string;
  secret_type: string;
  repository: string;
  file_path: string;
  commit_sha: string;
  last_checked: string;
  masked_hash: string;
  masked_preview?: string;
  detector?: string;
  detector_name?: string;
  rule_id?: string;
  line_number?: number;
  confidence?: number | null;
  classification?: 'TRUE_SECRET' | 'FALSE_POSITIVE' | 'TEST_FIXTURE' | 'EXAMPLE_DOCUMENTATION' | 'UNKNOWN' | string;
  validation_status?: string;
  criticality?: string;
  features?: Record<string, number>;
  ml_verdict?: string;
  detected?: boolean;
  is_current?: boolean;
  is_historical?: boolean;
  commit?: string;
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
  total_findings: number;
  true_secrets: number;
  false_positives: number;
  test_fixtures: number;
  unknown_findings: number;
};
