import { BarChart3, FileWarning, GitCommitHorizontal, ShieldCheck } from "lucide-react";

function Metric({ label, value }) {
  return <div className="metric-card"><span>{label}</span><strong>{value ?? "Unknown"}</strong></div>;
}

export function DashboardPanel({ metrics, scanHistory }) {
  return <section className="dashboard-panel">
    <div className="panel-kicker"><BarChart3 size={15} /> ANALYSIS DASHBOARD</div>
    <div className="metric-grid">
      <Metric label="Repositories" value={metrics?.repositories} />
      <Metric label="Scans" value={metrics?.scans} />
      <Metric label="Commits analyzed" value={metrics?.commits_analyzed} />
      <Metric label="Files scanned" value={metrics?.files_scanned} />
      <Metric label="Secrets detected" value={metrics?.secrets_detected} />
      <Metric label="High confidence" value={metrics?.high_confidence_findings} />
      <Metric label="Recovered history files" value={metrics?.historical_files_recovered} />
      <Metric label="Historical secrets" value={metrics?.historical_secrets} />
    </div>
    <p className="data-note">Latest scan: {scanHistory?.[0]?.status || "No scan recorded"}. Historical secret counts remain unknown until lifecycle analysis is implemented.</p>
  </section>;
}

export function FindingsPanel({ findings }) {
  return <section className="findings-panel"><div className="panel-kicker"><FileWarning size={15} /> CURRENT-SOURCE FINDINGS</div><div className="findings-summary"><strong>{findings.length}</strong><span>redacted findings in this scan</span></div>{findings.length > 0 ? <div className="findings-table"><div className="findings-row findings-header"><span>Type</span><span>File</span><span>Line</span><span>Confidence</span><span>Preview</span><span>Status</span></div>{findings.map((finding) => <div className="findings-row" key={finding.finding_id}><strong>{finding.secret_type}</strong><span>{finding.file_path}</span><span>{finding.line_number}</span><span>{Math.round(finding.confidence * 100)}%</span><code>{finding.masked_preview}</code><span className="finding-status">{finding.status}</span></div>)}</div> : <p className="empty-state">No secrets detected in the current working tree.</p>}</section>;
}

export function CommitDetailsPanel({ details, deleted }) {
  return <section className="detail-panel"><div className="panel-kicker"><GitCommitHorizontal size={15} /> COMMIT DETAILS</div><div className="detail-heading"><strong>{details.commit_hash.slice(0, 8)}</strong><span>{details.message}</span></div><div className="detail-meta"><span>Author: {details.author}</span><span>Parent: {details.parent_hash?.slice(0, 8) || "root commit"}</span><span>{new Date(details.commit_timestamp).toLocaleString()}</span></div><div className="lifecycle-strip"><span>HISTORY RECORD</span><strong>{deleted ? "REMOVED FROM CURRENT SOURCE" : "PRESENT IN COMMIT"}</strong><small>Deletion is not credential revocation.</small></div><div className="changed-files">{details.changed_files.map((file) => <div key={file.path}><code>{file.path}</code><span>+{file.insertions} / -{file.deletions}</span></div>)}</div></section>;
}

export function DataListPanel({ title, items, empty }) {
  return <section className="data-list-panel"><div className="panel-kicker"><ShieldCheck size={15} /> {title.toUpperCase()}</div>{items.length ? items.map((item) => <div className="data-list-item" key={item}>{item}</div>) : <p className="empty-state">{empty}</p>}</section>;
}

export function ScanHistoryPanel({ scans }) {
  return <section className="data-list-panel"><div className="panel-kicker"><BarChart3 size={15} /> SCAN HISTORY</div>{scans.length ? scans.map((scan) => <div className="scan-history-row" key={scan.id}><strong>#{scan.id} · {scan.repository_id}</strong><span>{scan.status} · {scan.files_scanned} files · {scan.findings_count} findings · {scan.duration_ms} ms</span></div>) : <p className="empty-state">No scans have been recorded.</p>}</section>;
}
