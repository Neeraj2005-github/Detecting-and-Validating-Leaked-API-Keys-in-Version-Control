import { Link, useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, FileText, GitBranch, ShieldCheck } from 'lucide-react';
import { fetchFindingById } from '../api/findings';
import RiskScoreBreakdown from '../components/RiskScoreBreakdown';
import StateTimeline from '../components/StateTimeline';
import LoadingSkeleton from '../components/LoadingSkeleton';
import EmptyState from '../components/EmptyState';
import type { Finding } from '../types';

export default function FindingDetailPage() {
  const { id } = useParams();
  const [finding, setFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const data = await fetchFindingById(id ?? '');
        if (mounted) setFinding(data);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, [id]);

  if (loading) return <LoadingSkeleton rows={6} />;
  if (!finding) {
    return (
      <EmptyState
        icon={<AlertTriangle size={18} />}
        title="Finding not found"
        description="This finding may have been removed or the ID is invalid."
        action={<Link to="/" className="button-link">Return to dashboard</Link>}
      />
    );
  }

  return (
    <div className="page-shell detail-page">
      <div className="detail-nav">
        <Link to="/" className="button-link">
          <ArrowLeft size={14} /> Back to dashboard
        </Link>
      </div>

      <section className="panel-card detail-panel-header">
        <div>
          <div className="eyebrow">Secret exposure</div>
          <h2>{finding.secret_type}</h2>
        </div>
        <div className="affinity-block">
          <span>{finding.repository}</span>
          <span>{finding.file_path}</span>
          <span>{finding.commit_sha.slice(0, 8)}</span>
        </div>
      </section>

      <div className="detail-grid">
        <section className="panel-card">
          <div className="panel-header">
            <h3>Risk score breakdown</h3>
            <span className="risk-total">{finding.risk_score}/100</span>
          </div>
          <RiskScoreBreakdown breakdown={finding.risk_breakdown ?? { validity: 40, blastRadius: 25, exposure: 20, criticality: 15 }} />
        </section>

        <section className="panel-card">
          <div className="panel-header">
            <h3>State timeline</h3>
          </div>
          <StateTimeline transitions={finding.state_transitions ?? [{ state: 'LEAKED_VALID', timestamp: finding.last_checked }]} />
        </section>
      </div>

      <section className="panel-card metadata-panel">
        <div className="metadata-row">
          <div className="meta-item">
            <FileText size={14} />
            <span>Path</span>
            <strong>{finding.file_path}</strong>
          </div>
          <div className="meta-item">
            <GitBranch size={14} />
            <span>Commit</span>
            <strong>{finding.commit_sha.slice(0, 12)}</strong>
          </div>
          <div className="meta-item">
            <ShieldCheck size={14} />
            <span>Masked hash</span>
            <strong>{finding.masked_hash || '****a91f'}</strong>
          </div>
        </div>
      </section>
    </div>
  );
}
