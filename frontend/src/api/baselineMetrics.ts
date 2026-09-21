import api from './client';

export type BaselineMetrics = {
  baseline_A_gitleaks_only: MetricSet;
  baseline_B_gitleaks_plus_ml_filter: MetricSet;
  test_set_size: number;
  evaluation_valid?: boolean;
  validation_warning?: string | null;
};

type MetricSet = {
  precision: number;
  recall: number;
  f1: number;
  false_positive_rate: number;
};

export async function fetchBaselineMetrics(): Promise<BaselineMetrics> {
  const { data } = await api.get('/metrics/baseline', {
    headers: { 'Cache-Control': 'no-cache' },
  });
  return data;
}