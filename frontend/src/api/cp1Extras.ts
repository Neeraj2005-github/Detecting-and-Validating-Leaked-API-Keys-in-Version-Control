import api from './client';

export async function fetchCp1Extras(): Promise<Record<string, any>> {
  const { data } = await api.get('/cp1/extras');
  return data;
}
