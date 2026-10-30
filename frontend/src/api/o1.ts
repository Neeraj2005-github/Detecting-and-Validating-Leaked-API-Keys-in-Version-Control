import api from './client';

export type O1Evidence = {
  reproduction: {
    status: string;
    timeline: { sha: string; message: string; files_changed: string[] }[];
    rev_list: string[];
    verification: Record<string, boolean | string>;
    diff_output: string;
  };
  contract: {
    contract_version: string;
    status: string;
    functional_requirements: { id: string; name: string; specification: string }[];
    non_functional_requirements: { id: string; name: string; specification: string }[];
    acceptance_plan: {
      criteria: { id: string; definition: string; pass_threshold: string }[];
      kpis: { name: string; target: string }[];
    };
  };
  dependencies: Record<string, { available: boolean; version?: string | null }>;
  oracle: {
    version: string;
    entry_count: number;
    entries: { id: string; is_secret: boolean; expected_lifecycle: string }[];
  };
};

export async function fetchO1Evidence(): Promise<O1Evidence> {
  const { data } = await api.get<O1Evidence>('/o1/evidence');
  return data;
}
