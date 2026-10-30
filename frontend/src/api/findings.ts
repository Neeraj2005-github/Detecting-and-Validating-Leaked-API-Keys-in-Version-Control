import api from './client';
import { localFindings, localSummaryMetrics } from './fallback';

export async function fetchFindings(repoId?: string) {
  const params = repoId
    ? { repo_id: repoId, sort: 'risk_score', order: 'desc', page: 1 }
    : { sort: 'risk_score', order: 'desc', page: 1 };
  try {
    const { data } = await api.get('/findings', { params });
    return data.items ?? data;
  } catch (error) {
    console.warn('Findings API unavailable; using local fallback artifact.', error);
    return localFindings;
  }
}

export async function fetchFindingById(id: string) {
  try {
    const { data } = await api.get(`/findings/${id}`);
    return data;
  } catch (error) {
    console.warn('Finding API unavailable; using local fallback artifact.', error);
    return localFindings.find((finding) => String(finding.id) === id) ?? null;
  }
}

export async function fetchSummaryMetrics(repoId?: string) {
  try {
    const { data } = await api.get('/metrics/summary', { params: repoId ? { repo_id: repoId } : undefined });
    return data;
  } catch (error) {
    console.warn('Summary API unavailable; using local fallback artifact.', error);
    return localSummaryMetrics;
  }
}
