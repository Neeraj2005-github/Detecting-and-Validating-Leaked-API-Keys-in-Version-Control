import scanArtifact from '../../../artifacts/cp1_latest_scan.json';

const fallbackRows = scanArtifact.findings?.length ? scanArtifact.findings : scanArtifact.resolved_findings ?? [];

export const localFindings = fallbackRows.map((finding, index) => ({
  ...finding,
  id: finding.id ?? finding.fingerprint ?? `local-fallback-${index}`,
  repository: finding.repository ?? 'Local demo repository',
  last_checked: finding.last_checked ?? 'Local artifact',
  masked_hash: finding.masked_hash ?? finding.masked_match,
}));

export const localSummaryMetrics = {
  total_findings: scanArtifact.summary?.total ?? localFindings.length,
  current_findings: scanArtifact.summary?.active_head ?? 0,
  historical_findings: scanArtifact.summary?.historical ?? 0,
  high_findings: localFindings.filter((finding) => Number(finding.risk_score ?? 0) >= 70).length,
  medium_findings: localFindings.filter((finding) => Number(finding.risk_score ?? 0) >= 40 && Number(finding.risk_score ?? 0) < 70).length,
  low_findings: localFindings.filter((finding) => Number(finding.risk_score ?? 0) < 40).length,
};
