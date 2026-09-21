import api from './client';

export async function fetchRepositories() {
  const { data } = await api.get('/repositories');
  return data;
}

export async function addRepository(url: string) {
  const { data } = await api.post('/repositories', { url });
  return data;
}

export async function scanRepository(id: string) {
  const { data } = await api.post(`/repositories/${encodeURIComponent(id)}/scan`);
  return data;
}

export async function updateRepository(id: string, url: string) {
  const { data } = await api.put(`/repositories/${encodeURIComponent(id)}`, { url });
  return data;
}

export async function deleteRepository(id: string) {
  await api.delete(`/repositories/${encodeURIComponent(id)}`);
}
