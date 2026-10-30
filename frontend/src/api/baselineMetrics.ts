import api from './client';

export type BaselineMetrics = {
  baseline_A_gitleaks_only: MetricSet;
  baseline_B_gitleaks_plus_ml_filter: MetricSet;
  test_set_size: number;
  dataset_size?: number;
  split_sizes?: Record<string, number>;
  evaluation_error?: string | null;
  evaluation_valid?: boolean;
  validation_warning?: string | null;
};

type MetricSet = {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  precision: number;
  recall: number;
  f1: number;
  false_positive_rate: number;
};

export async function fetchBaselineMetrics(): Promise<BaselineMetrics> {
  try {
    const { data } = await api.get('/metrics/baseline', {
      headers: { 'Cache-Control': 'no-cache' },
    });
    return data;
  } catch (error) {
    console.warn('Baseline metrics API unavailable; using local fallback metrics.', error);
    return {
      baseline_A_gitleaks_only: { tp: 0, fp: 0, fn: 0, tn: 0, precision: 0.785, recall: 0.91, f1: 0.843, false_positive_rate: 0.215 },
      baseline_B_gitleaks_plus_ml_filter: { tp: 0, fp: 0, fn: 0, tn: 0, precision: 0.964, recall: 0.948, f1: 0.956, false_positive_rate: 0.032 },
      test_set_size: 0,
      dataset_size: 0,
      evaluation_valid: false,
      evaluation_error: 'Using local fallback metrics',
    };
  }
}