import { Fragment, useEffect, useState } from 'react';
import { Download, ArrowRight } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import SummaryCard from '../components/SummaryCard';
import { BaselineMetrics, fetchBaselineMetrics } from '../api/baselineMetrics';
import { fetchFindings } from '../api/findings';

type Finding = {
  id: string;
  secret_type: string;
  file_path: string;
  line_number: number;
  commit_sha: string;
  criticality: string;
  ml_verdict: string;
  confidence: number;
  detected: string;
  matched_line: string;
  rule_id: string;
  features: {
    entropy: number;
    length: number;
    char_class_count: number;
    digit_ratio: number;
    is_test_path: number;
    has_example_keyword: number;
    repeated_char_ratio: number;
  };
};

function mapFinding(finding: any): Finding {
  const confidence = Number(finding.confidence);
  return {
    id: String(finding.id),
    secret_type: finding.secret_type,
    file_path: finding.file_path,
    line_number: finding.line_number,
    commit_sha: finding.commit_sha ?? '',
    criticality: finding.criticality ?? 'Unknown',
    ml_verdict: confidence >= 0.5 ? 'True secret' : 'False positive',
    confidence: Math.round(confidence * 100),
    detected: finding.detector,
    matched_line: finding.masked_preview,
    rule_id: finding.detector,
    features: { entropy: 0, length: 0, char_class_count: 0, digit_ratio: 0, is_test_path: 0, has_example_keyword: 0, repeated_char_ratio: 0 },
  };
}

function formatMetric(value: number) {
  if (!Number.isFinite(value)) return 'Run `evaluate.py` to populate';
  return value.toFixed(value >= 1 ? 0 : 3).replace(/\.0+$/, '');
}

function maskCommit(commitSha: string) {
  return `****${commitSha.slice(-4)}`;
}

export default function DashboardPage() {
  const [searchParams] = useSearchParams();
  const [baselineMetrics, setBaselineMetrics] = useState<BaselineMetrics | null>(null);
  const [repositoryFindings, setRepositoryFindings] = useState<Finding[]>([]);
  const [findingsLoading, setFindingsLoading] = useState(true);
  const [expandedFindingId, setExpandedFindingId] = useState<string | null>(null);

  useEffect(() => {
    fetchBaselineMetrics().then(setBaselineMetrics).catch(() => setBaselineMetrics(null));
  }, []);

  const baselineA = baselineMetrics?.baseline_A_gitleaks_only;
  const baselineB = baselineMetrics?.baseline_B_gitleaks_plus_ml_filter;
  const testSetLabel = baselineMetrics ? `n=${baselineMetrics.test_set_size} test examples` : 'report unavailable';
  const baselineBValid = Boolean(baselineMetrics?.evaluation_valid ?? true);
  const repoFilter = searchParams.get('repo');
  useEffect(() => {
    setFindingsLoading(true);
    fetchFindings(repoFilter ?? undefined)
      .then((findings) => setRepositoryFindings(findings.map(mapFinding)))
      .catch(() => setRepositoryFindings([]))
      .finally(() => setFindingsLoading(false));
  }, [repoFilter]);

  const visibleFindings = repositoryFindings;
  const confirmedFindings = visibleFindings.filter((finding) => finding.confidence >= 50);
  const secretTypes = [...new Set(visibleFindings.map((finding) => finding.secret_type))];
  const metrics = {
    total_findings: visibleFindings.length,
    true_secrets_confirmed: confirmedFindings.length,
    false_positives_filtered: visibleFindings.length - confirmedFindings.length,
    detector_types_covered: secretTypes.length,
  };

  function exportReport() {
    const generatedAt = new Date();
    const document = new jsPDF();
    document.setFontSize(18);
    document.text('Detecting Secrets in Version Control report', 14, 18);
    document.setFontSize(10);
    document.text(`Generated ${generatedAt.toLocaleString()}`, 14, 25);

    autoTable(document, {
      startY: 32,
      head: [['Summary metric', 'Value']],
      body: [
        ['Total Findings', String(metrics.total_findings)],
        ['True Secrets Confirmed', String(metrics.true_secrets_confirmed)],
        ['False Positives Filtered', String(metrics.false_positives_filtered)],
        ['Detector Types Covered', String(metrics.detector_types_covered)],
      ],
    });

    const comparisonStart = (document as jsPDF & { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? 40;
    autoTable(document, {
      startY: comparisonStart + 8,
      head: [['Metric', 'Baseline A - Gitleaks only', 'Baseline B - Gitleaks + ML filter']],
      body: ['Precision', 'Recall', 'F1 score', 'False-Positive Rate'].map((label) => {
        const key = label === 'F1 score' ? 'f1' : label === 'False-Positive Rate' ? 'false_positive_rate' : label.toLowerCase();
        return [label, formatMetric(baselineA?.[key as keyof typeof baselineA] as number ?? Number.NaN), baselineBValid ? formatMetric(baselineB?.[key as keyof typeof baselineB] as number ?? Number.NaN) : 'Evaluation blocked'];
      }),
    });

    const findingsStart = (document as jsPDF & { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? comparisonStart + 50;
    autoTable(document, {
      startY: findingsStart + 8,
      head: [['Secret Type', 'File & Line', 'Criticality', 'ML Verdict', 'Detected']],
      body: visibleFindings.map((finding) => [
        finding.secret_type,
        `${finding.file_path}:${finding.line_number} (${maskCommit(finding.commit_sha)})`,
        finding.criticality,
        `${finding.ml_verdict} (${finding.confidence}%)`,
        finding.detected,
      ]),
    });

    document.save(`secretguard-report-${generatedAt.toISOString().slice(0, 10)}.pdf`);
  }

  return (
    <div className="dashboard-shell">
      <div className="panel-header panel-header--tight">
        <h1>Dashboard</h1>
        <button type="button" className="primary-button primary-button--inline" onClick={exportReport}>
          <Download size={15} /> Export report (PDF)
        </button>
      </div>
      <div className="summary-grid">
        <SummaryCard label="Total Findings" value={metrics.total_findings} secondary={`Across ${repoFilter ? 'this repository' : 'all repositories'}`} />
        <SummaryCard label="True Secrets Confirmed" value={metrics.true_secrets_confirmed} secondary="After ML filtering" tone="success" />
        <SummaryCard label="False Positives Filtered" value={metrics.false_positives_filtered} secondary="Removed from final result" tone="default" />
        <SummaryCard label="Detector Types Covered" value={metrics.detector_types_covered} secondary={secretTypes.join(', ') || 'None'} />
      </div>

      <section className="panel-card comparison-panel">
        <div className="panel-head">
          <h2>Baseline Metrics Comparison</h2>
          <span>O2 proof of contribution</span>
        </div>

        <div className="baseline-grid">
          <div className="baseline-card">
            <h3>Baseline A</h3>
            <p>Gitleaks only</p>
            <dl className="metric-list">
              <div><dt>Precision</dt><dd>{formatMetric(baselineA?.precision ?? Number.NaN)}</dd></div>
              <div><dt>Recall</dt><dd>{formatMetric(baselineA?.recall ?? Number.NaN)}</dd></div>
              <div><dt>F1 score <small>— {testSetLabel}</small></dt><dd>{formatMetric(baselineA?.f1 ?? Number.NaN)}</dd></div>
              <div><dt>False-Positive Rate</dt><dd>{formatMetric(baselineA?.false_positive_rate ?? Number.NaN)}</dd></div>
            </dl>
          </div>

          <div className="baseline-card baseline-card--primary">
            <h3>Baseline B</h3>
            <p>Gitleaks + ML filter</p>
            <dl className="metric-list">
              <div><dt>Precision</dt><dd>{baselineBValid ? formatMetric(baselineB?.precision ?? Number.NaN) : 'Evaluation blocked'}</dd></div>
              <div><dt>Recall</dt><dd>{baselineBValid ? formatMetric(baselineB?.recall ?? Number.NaN) : 'Evaluation blocked'}</dd></div>
              <div><dt>F1 score <small>— {testSetLabel}</small></dt><dd>{baselineBValid ? formatMetric(baselineB?.f1 ?? Number.NaN) : 'Evaluation blocked'}</dd></div>
              <div><dt>False-Positive Rate</dt><dd>{baselineBValid ? formatMetric(baselineB?.false_positive_rate ?? Number.NaN) : 'Evaluation blocked'}</dd></div>
            </dl>
          </div>
        </div>
      </section>

      <section className="panel-card worklist-panel">
        <div className="panel-head">
          <h2>Findings</h2>
          <span>O2 detection output</span>
        </div>

        {findingsLoading ? (
          <div className="empty-state">
            <h3>Loading findings...</h3>
          </div>
        ) : visibleFindings.length === 0 ? (
          <div className="empty-state">
            <h3>No scans yet - add a repository to get started</h3>
            <Link to="/repositories" className="primary-button primary-button--inline">
              Add a repository <ArrowRight size={16} />
            </Link>
          </div>
        ) : <div className="table-wrap">
          <table className="findings-table">
            <thead>
              <tr>
                <th>Secret Type</th>
                <th>File &amp; Line</th>
                <th>Commit</th>
                <th>Criticality</th>
                <th>ML Verdict</th>
                <th>Detected</th>
              </tr>
            </thead>
            <tbody>
              {visibleFindings.map((finding) => {
                const isExpanded = expandedFindingId === finding.id;
                return (
                  <Fragment key={finding.id}>
                    <tr
                      key={finding.id}
                      className={`finding-row ${isExpanded ? 'finding-row--expanded' : ''}`}
                      onClick={() => setExpandedFindingId(isExpanded ? null : finding.id)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          setExpandedFindingId(isExpanded ? null : finding.id);
                        }
                      }}
                      tabIndex={0}
                      aria-expanded={isExpanded}
                    >
                      <td>{finding.secret_type}</td>
                      <td>{`${finding.file_path}:${finding.line_number}`}</td>
                      <td className="mono-cell">{finding.commit_sha}</td>
                      <td><span className={`criticality-pill ${finding.criticality.toLowerCase()}`}>{finding.criticality}</span></td>
                      <td>
                        <div className="ml-verdict">
                          <span className={finding.ml_verdict === 'True secret' ? 'ml-verdict--positive' : 'ml-verdict--negative'}>{finding.ml_verdict}</span>
                          <small>{finding.confidence}%</small>
                        </div>
                      </td>
                      <td>{finding.detected}</td>
                    </tr>
                    {isExpanded && (
                      <tr className="finding-detail-row">
                        <td colSpan={6}>
                          <div className="finding-detail">
                            <div className="finding-detail__evidence">
                              <div className="finding-detail__field">
                                <span className="finding-detail__label">Matched line</span>
                                <code>{finding.matched_line}</code>
                              </div>
                              <div className="finding-detail__field">
                                <span className="finding-detail__label">Gitleaks rule ID</span>
                                <code>{finding.rule_id}</code>
                              </div>
                            </div>
                            <div className="finding-detail__heading">
                              <span>ML feature evidence</span>
                              <strong>Confidence {finding.confidence}%</strong>
                            </div>
                            <table className="finding-features-table">
                              <tbody>
                                {Object.entries(finding.features).map(([name, value]) => (
                                  <tr key={name}>
                                    <th>{name}</th>
                                    <td>{value}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>}
      </section>
    </div>
  );
}
