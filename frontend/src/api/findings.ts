import api from './client';

export async function fetchFindings(repoId?: string) {
  const params = repoId
    ? { repo_id: repoId, sort: 'risk_score', order: 'desc', page: 1 }
    : { sort: 'risk_score', order: 'desc', page: 1 };
  const { data } = await api.get('/findings', { params });
  return data.items ?? data;
}

export async function fetchFindingById(id: string) {
  const { data } = await api.get(`/findings/${id}`);
  return data;
}

export async function fetchSummaryMetrics() {
  const { data } = await api.get('/metrics/summary');
  return data;
}
