import { Fragment, useEffect, useState } from 'react';
import { Download, ArrowRight } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import SummaryCard from '../components/SummaryCard';
import { BaselineMetrics, fetchBaselineMetrics } from '../api/baselineMetrics';
import { fetchFindings } from '../api/findings';
import { fetchSummaryMetrics } from '../api/findings';
import { maskCommit, maskSecret } from '../utils/displaySafety';

type Finding = {
  id: string;
  secret_type: string;
  file_path: string;
  line_number: number;
  commit_sha: string;
  criticality: string;
  classification: string;
  ml_verdict: string;
  confidence: number | null;
  detected: string;
  matched_line: string;
  validation_status: string;
  is_current: boolean;
  is_historical: boolean;
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
  const confidence = finding.confidence === null || finding.confidence === undefined ? null : Number(finding.confidence);
  return {
    id: String(finding.id),
    secret_type: finding.secret_type,
    file_path: finding.file_path,
    line_number: finding.line_number,
    commit_sha: finding.commit_sha ?? '',
    criticality: finding.criticality ?? 'UNKNOWN',
    classification: finding.classification ?? 'UNKNOWN',
    ml_verdict: finding.ml_verdict ?? 'NOT_AVAILABLE',
    confidence: confidence === null ? null : Math.round(confidence * 100),
    detected: finding.detector_name ?? 'gitleaks',
    matched_line: maskSecret(finding.masked_match ?? finding.masked_preview),
    rule_id: finding.rule_id ?? finding.detector,
    validation_status: finding.validation_status ?? 'NOT_CHECKED',
    is_current: Boolean(finding.is_current),
    is_historical: Boolean(finding.is_historical),
    features: finding.features ?? {},
  };
}

function formatMetric(value: number) {
  if (!Number.isFinite(value)) return 'Run `evaluate.py` to populate';
  return value.toFixed(value >= 1 ? 0 : 3).replace(/\.0+$/, '');
}

export default function DashboardPage() {
  const [searchParams] = useSearchParams();
  const [baselineMetrics, setBaselineMetrics] = useState<BaselineMetrics | null>(null);
  const [repositoryFindings, setRepositoryFindings] = useState<Finding[]>([]);
  const [summaryMetrics, setSummaryMetrics] = useState<any>(null);
  const [findingsLoading, setFindingsLoading] = useState(true);
  const [expandedFindingId, setExpandedFindingId] = useState<string | null>(null);

  useEffect(() => {
    fetchBaselineMetrics().then(setBaselineMetrics).catch(() => setBaselineMetrics(null));
  }, []);

  const baselineA = baselineMetrics?.baseline_A_gitleaks_only;
  const baselineB = baselineMetrics?.baseline_B_gitleaks_plus_ml_filter;
  const testSetLabel = baselineMetrics ? `n=${baselineMetrics.test_set_size} test examples` : 'report unavailable';
  const baselineBValid = Boolean(baselineMetrics?.evaluation_valid);
  const repoFilter = searchParams.get('repo');
  useEffect(() => {
    fetchSummaryMetrics(repoFilter ?? undefined).then(setSummaryMetrics).catch(() => setSummaryMetrics(null));
  }, [repoFilter]);
  useEffect(() => {
    setFindingsLoading(true);
    fetchFindings(repoFilter ?? undefined)
      .then((findings) => setRepositoryFindings(findings.map(mapFinding)))
      .catch(() => setRepositoryFindings([]))
      .finally(() => setFindingsLoading(false));
  }, [repoFilter]);

  const visibleFindings = repositoryFindings;
  const secretTypes = [...new Set(visibleFindings.map((finding) => finding.secret_type))];
  const metrics = {
    total_findings: summaryMetrics?.total_findings ?? visibleFindings.length,
    current_findings: summaryMetrics?.current_findings ?? visibleFindings.filter((finding) => finding.is_current).length,
    historical_findings: summaryMetrics?.historical_findings ?? 0,
    high_findings: summaryMetrics?.high_findings ?? 0,
    medium_findings: summaryMetrics?.medium_findings ?? 0,
    low_findings: summaryMetrics?.low_findings ?? 0,
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
        ['Current Findings', String(metrics.current_findings)],
        ['Historical Findings', String(metrics.historical_findings)],
        ['High', String(metrics.high_findings)],
        ['Medium', String(metrics.medium_findings)],
        ['Low', String(metrics.low_findings)],
        ['Detector Types Covered', String(metrics.detector_types_covered)],
      ],
    });

    const comparisonStart = (document as jsPDF & { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? 40;
    autoTable(document, {
      startY: comparisonStart + 8,
      head: [['Metric', 'Baseline A - Gitleaks only', 'Baseline B - Gitleaks + ML filter']],
      body: ['Precision', 'Recall', 'F1 score', 'False-Positive Rate'].map((label) => {
        const key = label === 'F1 score' ? 'f1' : label === 'False-Positive Rate' ? 'false_positive_rate' : label.toLowerCase();
        return [label, formatMetric(baselineA?.[key as keyof typeof baselineA] as number ?? Number.NaN), baselineBValid ? formatMetric(baselineB?.[key as keyof typeof baselineB] as number ?? Number.NaN) : 'NOT_AVAILABLE'];
      }),
    });

    const findingsStart = (document as jsPDF & { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? comparisonStart + 50;
    autoTable(document, {
      startY: findingsStart + 8,
      head: [['Secret Type', 'File & Line', 'Classification', 'Criticality', 'ML Verdict', 'Validation']],
      body: visibleFindings.map((finding) => [
        finding.secret_type,
        `${finding.file_path}:${finding.line_number} (${maskCommit(finding.commit_sha)})`,
        finding.classification,
        finding.criticality,
        `${finding.ml_verdict} (${finding.confidence === null ? 'NOT_AVAILABLE' : `${finding.confidence}%`})`,
        finding.validation_status,
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
        <SummaryCard label="Current Findings" value={metrics.current_findings} secondary="Present in current source" tone="default" />
        <SummaryCard label="Historical Findings" value={metrics.historical_findings} secondary="Found in Git history" tone="default" />
        <SummaryCard label="High / Medium / Low" value={`${metrics.high_findings} / ${metrics.medium_findings} / ${metrics.low_findings}`} secondary="Risk classification" tone="default" />
        <SummaryCard label="Detector Types Covered" value={metrics.detector_types_covered} secondary={secretTypes.join(', ') || 'None'} />
      </div>

      <section className="panel-card comparison-panel">
        <div className="panel-head">
          <h2>Baseline Metrics Comparison</h2>
          <span>Evaluation dataset: n={baselineMetrics?.dataset_size ?? 'NOT_AVAILABLE'} labeled examples</span>
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
              <div><dt>Precision</dt><dd>{baselineBValid ? formatMetric(baselineB?.precision ?? Number.NaN) : 'NOT_AVAILABLE'}</dd></div>
              <div><dt>Recall</dt><dd>{baselineBValid ? formatMetric(baselineB?.recall ?? Number.NaN) : 'NOT_AVAILABLE'}</dd></div>
              <div><dt>F1 score <small>— {testSetLabel}</small></dt><dd>{baselineBValid ? formatMetric(baselineB?.f1 ?? Number.NaN) : 'NOT_AVAILABLE'}</dd></div>
              <div><dt>False-Positive Rate</dt><dd>{baselineBValid ? formatMetric(baselineB?.false_positive_rate ?? Number.NaN) : 'NOT_AVAILABLE'}</dd></div>
            </dl>
          </div>
        </div>
      </section>

      <section className="panel-card worklist-panel">
        <div className="panel-head">
          <h2>Findings</h2>
          <span>AI detection output</span>
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
                <th>Classification</th>
                <th>Criticality</th>
                <th>ML Verdict</th>
                <th>Validation</th>
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
                      <td className="mono-cell">{maskCommit(finding.commit_sha)}</td>
                      <td>{finding.classification}</td>
                      <td><span className={`criticality-pill ${finding.criticality.toLowerCase()}`}>{finding.criticality}</span></td>
                      <td>
                        <div className="ml-verdict">
                          <span className={finding.ml_verdict === 'Likely real secret' ? 'ml-verdict--positive' : 'ml-verdict--negative'}>{finding.ml_verdict}</span>
                          <small>{finding.confidence === null ? 'NOT_AVAILABLE' : `${finding.confidence}%`}</small>
                        </div>
                      </td>
                      <td>{finding.validation_status}</td>
                    </tr>
                    {isExpanded && (
                      <tr className="finding-detail-row">
                        <td colSpan={7}>
                          <div className="finding-detail">
                            <div className="finding-detail__evidence">
                              <div className="finding-detail__field">
                                <span className="finding-detail__label">Matched line</span>
                                <code>{maskSecret(finding.matched_line)}</code>
                              </div>
                              <div className="finding-detail__field">
                                <span className="finding-detail__label">Gitleaks rule ID</span>
                                <code>{finding.rule_id}</code>
                              </div>
                              <div className="finding-detail__field">
                                <span className="finding-detail__label">Detection / validation</span>
                                <code>{finding.detected} / {finding.validation_status}</code>
                              </div>
                            </div>
                            <div className="finding-detail__heading">
                              <span>ML feature evidence</span>
                              <strong>Confidence {finding.confidence === null ? 'NOT_AVAILABLE' : `${finding.confidence}%`}</strong>
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
