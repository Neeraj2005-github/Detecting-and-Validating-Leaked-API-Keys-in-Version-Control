import api from './client';

export const fetchCp1Overview = async () => (await api.get('/api/cp1/overview', { timeout: 30000 })).data;
export const scanCp1 = async (payload: { repo_url?: string; synthetic_fixture: boolean; use_ai_filter: boolean }) =>
  (await api.post('/api/cp1/scan', payload, { timeout: 120000 })).data;
export const reproduceO1 = async () => (await api.post('/api/cp1/reproduce-o1', {}, { timeout: 120000 })).data;
export const runCp1Benchmark = async () => (await api.post('/api/cp1/benchmark/run', {}, { timeout: 120000 })).data;
export const rotateCp1 = async (findingId: string) =>
  (await api.post(`/api/cp1/rotate/${encodeURIComponent(findingId)}`, {}, { timeout: 30000 })).data;
