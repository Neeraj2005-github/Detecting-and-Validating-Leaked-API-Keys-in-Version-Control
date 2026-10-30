import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { fetchO1Evidence, O1Evidence } from '../api/o1';

export default function O1EvidencePage() {
  const [evidence, setEvidence] = useState<O1Evidence | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchO1Evidence().then(setEvidence).catch(() => setError('O1 evidence is unavailable. Run the reproduction CLI first.'));
  }, []);

  function exportPdf() {
    if (!evidence) return;
    const document = new jsPDF();
    document.setFontSize(18);
    document.text('VaultGuard Security Contract', 14, 18);
    document.setFontSize(10);
    document.text(`Status: ${evidence.contract.status} | Reproduction: ${evidence.reproduction.status}`, 14, 26);
    autoTable(document, {
      startY: 34,
      head: [['Requirement', 'Name', 'Specification']],
      body: evidence.contract.functional_requirements.map((item) => [item.id, item.name, item.specification]),
    });
    const nextY = (document as jsPDF & { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? 45;
    autoTable(document, {
      startY: nextY + 8,
      head: [['Commit', 'Message', 'Files']],
      body: evidence.reproduction.timeline.map((item) => [item.sha.slice(0, 12), item.message, item.files_changed.join(', ')]),
    });
    document.save('secretguard-o1-evidence.pdf');
  }

  if (error) return <section className="panel-card"><h1>O1 Evidence</h1><p>{error}</p></section>;
  if (!evidence) return <section className="panel-card"><h1>O1 Evidence</h1><p>Loading evidence...</p></section>;

  const verification = evidence.reproduction.verification;
  return (
    <div className="dashboard-shell">
      <div className="panel-header panel-header--tight">
        <div><h1>Security Contract</h1><p>Reproducible Git history proof and engineering guarantees.</p></div>
        <button type="button" className="primary-button primary-button--inline" onClick={exportPdf}><Download size={15} /> Export O1 PDF</button>
      </div>
      <section className="panel-card">
        <h2>Git history reproduction</h2>
        <p><strong>{evidence.reproduction.status}</strong> — secret in history: {String(verification.secret_in_history)}; secret in HEAD: {String(verification.secret_in_working_tree)}; recoverable: {String(verification.secret_recoverable)}</p>
        <table className="data-table"><thead><tr><th>Commit</th><th>Message</th><th>Files</th></tr></thead><tbody>
          {evidence.reproduction.timeline.map((item) => <tr key={item.sha}><td>{item.sha.slice(0, 12)}</td><td>{item.message}</td><td>{item.files_changed.join(', ')}</td></tr>)}
        </tbody></table>
      </section>
      <section className="panel-card">
        <h2>Frozen requirements</h2>
        <table className="data-table"><thead><tr><th>ID</th><th>Name</th><th>Specification</th></tr></thead><tbody>
          {evidence.contract.functional_requirements.map((item) => <tr key={item.id}><td>{item.id}</td><td>{item.name}</td><td>{item.specification}</td></tr>)}
        </tbody></table>
      </section>
      <section className="panel-card">
        <h2>Readiness and oracle</h2>
        <p>{evidence.oracle.entry_count} versioned oracle entries ({evidence.oracle.entries.filter((entry) => entry.is_secret).length} planted secrets, plaintext withheld).</p>
        <ul>{Object.entries(evidence.dependencies).map(([name, status]) => <li key={name}>{name}: {status.available ? 'available' : 'unavailable'}</li>)}</ul>
      </section>
    </div>
  );
}
