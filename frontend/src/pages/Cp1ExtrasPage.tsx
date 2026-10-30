import { useEffect, useState } from 'react';
import { fetchCp1Extras } from '../api/cp1Extras';

export default function Cp1ExtrasPage() {
  const [payload, setPayload] = useState<Record<string, any> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCp1Extras().then(setPayload).catch(() => setError('Advanced metrics are unavailable.'));
  }, []);

  return (
    <section className="panel-card">
      <h1>Advanced Metrics</h1>
      {error && <p>{error}</p>}
      {!payload && !error && <p>Loading live experiment metrics...</p>}
      {payload && <pre style={{ whiteSpace: 'pre-wrap', overflowX: 'auto' }}>{JSON.stringify(payload, null, 2)}</pre>}
    </section>
  );
}
