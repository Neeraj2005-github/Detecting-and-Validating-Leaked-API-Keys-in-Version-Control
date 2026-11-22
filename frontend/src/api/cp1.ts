import api from './client';
import { shouldStopScanning } from '../utils/scanState';

export const fetchCp1Overview = async () => (await api.get('/api/cp1/overview', { timeout: 30000 })).data;
export const startCp1Scan = async (payload: { repo_url?: string; synthetic_fixture: boolean; use_ai_filter: boolean; fast_scan?: boolean }) =>
  (await api.post('/api/cp1/scan', payload, { timeout: 30000 })).data;
export const fetchCp1ScanJob = async (jobId: string) =>
  (await api.get(`/api/cp1/jobs/${encodeURIComponent(jobId)}`, { timeout: 30000 })).data;
export const scanCp1 = async (payload: { repo_url?: string; synthetic_fixture: boolean; use_ai_filter: boolean; fast_scan?: boolean }, onProgress?: (job: any) => void) => {
  const started = await startCp1Scan(payload);
  const jobId = started.job_id;
  onProgress?.(started);
  const deadline = Date.now() + 300000;
  while (Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 500));
    const job = await fetchCp1ScanJob(jobId);
    onProgress?.(job);
    if (job.status === 'done') return job.result;
    if (job.status === 'timed_out' && job.result) return job.result;
    if (shouldStopScanning(job.status)) {
      throw new Error(`${job.error?.stage ?? 'Scan'}: ${job.error?.reason ?? 'The scan did not complete.'}`);
    }
  }
  throw new Error('Scan: The overall scan time limit was reached.');
};
export const reproduceO1 = async () => (await api.post('/api/cp1/reproduce-o1', {}, { timeout: 120000 })).data;
export const runCp1Benchmark = async () => (await api.post('/api/cp1/benchmark/run', {}, { timeout: 120000 })).data;
export const rotateCp1 = async (findingId: string) =>
  (await api.post(`/api/cp1/rotate/${encodeURIComponent(findingId)}`, {}, { timeout: 30000 })).data;
