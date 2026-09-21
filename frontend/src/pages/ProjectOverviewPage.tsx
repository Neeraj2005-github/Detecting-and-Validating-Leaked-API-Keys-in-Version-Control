import { ArrowRight, ShieldCheck, Target, TriangleAlert } from 'lucide-react';
import { Link } from 'react-router-dom';

const objectives = [
  {
    objective: 'O1',
    delivers: 'Problem charter, threat model, trust boundary',
    status: 'Complete',
    tone: 'done',
  },
  {
    objective: 'O2',
    delivers: 'Detection baseline (Gitleaks) + ML false-positive filter',
    status: 'Complete',
    tone: 'done',
  },
  {
    objective: 'O3',
    delivers: 'Live credential verification + explainable risk scoring',
    status: 'Planned',
    tone: 'planned',
  },
  {
    objective: 'O4',
    delivers: 'Rotation tracking + dashboard integration',
    status: 'Planned',
    tone: 'planned',
  },
  {
    objective: 'O5',
    delivers: 'Independent acceptance testing',
    status: 'Planned',
    tone: 'planned',
  },
];

export default function ProjectOverviewPage() {
  return (
    <div className="overview-shell">
      <section className="panel-card overview-panel overview-panel--primary">
        <div className="overview-summary">
          <h1>2 of 5 objectives complete</h1>
          <div className="overview-progress" aria-label="Project completion progress">
            <span className="overview-progress__fill" />
          </div>
          <p className="overview-intro">
            Detects leaked credentials in Git history and filters false positives using a trained classifier.
          </p>
        </div>

        <div className="overview-divider" />

        <div className="panel-header panel-header--simple panel-header--objective">
          <div className="panel-heading-group">
            <div className="panel-icon-wrap">
              <Target size={16} />
            </div>
            <h2>Objectives</h2>
          </div>
        </div>

        <div className="table-wrap">
          <table className="objective-table">
            <thead>
              <tr>
                <th>Objective</th>
                <th>What it delivers</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {objectives.map((row) => (
                <tr key={row.objective} className={row.tone}>
                  <td>{row.objective}</td>
                  <td>{row.delivers}</td>
                  <td>
                    <span className={`objective-status ${row.tone}`}>{row.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Link to="/dashboard" className="primary-button primary-button--inline overview-objectives-cta">
          View live O2 results <ArrowRight size={16} />
        </Link>
      </section>

      <section className="panel-card overview-panel">
        <div className="panel-header panel-header--simple">
          <div className="panel-heading-group">
            <div className="panel-icon-wrap">
              <ShieldCheck size={16} />
            </div>
            <h2>Scope &amp; trust boundary</h2>
          </div>
        </div>

        <ul className="overview-bullets">
          <li>Testing runs only against a seeded synthetic repository with planted, non-real secrets.</li>
          <li>No live provider verification occurs yet; that remains in O3.</li>
          <li>Evidence and evaluation are limited to the O1/O2 scope: charter, baseline detection, and ML false-positive filtering.</li>
        </ul>
      </section>

      <section className="panel-card overview-panel overview-panel--cta">
        <div className="cta-copy">
          <div className="cta-icon">
            <TriangleAlert size={16} />
          </div>
          <div>
            <strong>Current scope:</strong> O1 problem charter and O2 detection baseline with ML filtering.
          </div>
        </div>
        <a href="/dashboard" className="primary-button primary-button--inline">
          Open O2 dashboard
          <ArrowRight size={16} />
        </a>
      </section>
    </div>
  );
}
