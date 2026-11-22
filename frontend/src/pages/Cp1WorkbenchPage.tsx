import { useEffect, useState } from 'react';
import {
  ArrowRight, CheckCircle2, ChevronDown, ChevronUp, Copy, Download,
  Moon, Play, RotateCw, ShieldCheck, Sun, Terminal, X,
} from 'lucide-react';
import { fetchCp1Overview, reproduceO1, rotateCp1, runCp1Benchmark, scanCp1 } from '../api/cp1';
import { downloadPdf } from '../utils/pdfExport';
import { maskCommit, maskSecret } from '../utils/displaySafety';
import { ScanEmptyState } from '../components/ScanEmptyState.js';

type ViewName = 'home' | 'scanner' | 'architecture' | 'benchmarks' | 'integration';
type Props = { tab?: string };

const labels: Record<ViewName, string> = {
  home: 'Home',
  scanner: 'Detection & Validation',
  architecture: 'Architecture & Security',
  benchmarks: 'Benchmarks & Accuracy',
  integration: 'CI/CD & Automation',
};

function currentView(tab?: string): ViewName {
  return ['home', 'scanner', 'architecture', 'benchmarks', 'integration'].includes(tab || '') ? tab as ViewName : 'home';
}

function useTheme() {
  const [dark, setDark] = useState(() => localStorage.getItem('detection-theme') === 'dark');
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    localStorage.setItem('detection-theme', dark ? 'dark' : 'light');
  }, [dark]);
  return [dark, () => setDark(value => !value)] as const;
}

function ProductButton({ children, onClick, secondary = false, icon }: { children: React.ReactNode; onClick?: () => void; secondary?: boolean; icon?: React.ReactNode }) {
  return <button className={secondary ? 'vg-button vg-button-secondary' : 'vg-button'} onClick={onClick}>{icon}{children}</button>;
}

function CopySnippet({ value, label = 'Copy Code' }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return <button className="vg-copy" onClick={() => { navigator.clipboard?.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1400); }}><Copy size={14} /> {copied ? 'Copied' : label}</button>;
}

function Accordion({ title, children, open, onToggle }: { title: string; children: React.ReactNode; open: boolean; onToggle: () => void }) {
  return <div className="vg-accordion"><button className="vg-accordion-trigger" onClick={onToggle}><span>{title}</span>{open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}</button>{open && <div className="vg-accordion-body">{children}</div>}</div>;
}

function downloadText(filename: string, contents: string, type: string) {
  const url = URL.createObjectURL(new Blob([contents], { type }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function benchmarkRows(approaches: any[] = []) {
  return approaches.map(item => {
    const metrics = item.metrics ?? {};
    return {
      name: item.name,
      precision: Number.isFinite(metrics.precision) ? metrics.precision * 100 : null,
      recall: Number.isFinite(metrics.recall) ? metrics.recall * 100 : null,
      f1: Number.isFinite(metrics.f1_score) ? metrics.f1_score * 100 : null,
      fpr: Number.isFinite(metrics.false_positive_rate) ? metrics.false_positive_rate * 100 : null,
      time: metrics.scan_wall_clock_ms ?? null,
      memory: metrics.peak_rss_mb ?? null,
      unsafe: metrics.unsafe_outcome_count ?? null,
    };
  });
}

export default function Cp1WorkbenchPage({ tab }: Props) {
  const view = currentView(tab);
  const [dark, toggleTheme] = useTheme();
  const [overview, setOverview] = useState<any>(null);
  const [scan, setScan] = useState<any>(null);
  const [benchmark, setBenchmark] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');
  const [demoDiff, setDemoDiff] = useState(false);

  useEffect(() => {
    fetchCp1Overview().then(payload => {
      setOverview(payload);
      const approaches = payload?.kpis?.approaches;
      if (approaches?.length) setBenchmark(benchmarkRows(approaches));
    }).catch(() => {
      setOverview({
        kpis: { approaches: [] },
        extras: {},
      });
      setNotice('The scan service is unavailable. No scan result or benchmark data is available.');
    });
  }, []);

  const run = async (name: string, operation: () => Promise<any>, callback?: (result: any) => void, onError?: (error: any) => void) => {
    setBusy(name); setNotice('');
    try { const result = await operation(); callback?.(result); setNotice('Updated just now.'); }
    catch (error: any) {
      onError?.(error);
      const message = error?.response?.data?.detail
        ?? error?.message
        ?? 'The scan could not complete.';
      setNotice(String(message));
    }
    finally { setBusy(''); }
  };

  const exportReport = () => downloadPdf(`Detection and Validation ${labels[view]} Report`, [{ heading: 'Summary', body: 'Git secret detection, explainability, and safe credential remediation.' }, { heading: labels[view], body: JSON.stringify(view === 'benchmarks' ? benchmark : scan?.summary ?? 'NOT MEASURED') }]);
  const navigate = (next: ViewName) => { window.history.pushState({}, '', `/vaultguard/${next}`); window.dispatchEvent(new PopStateEvent('popstate')); };

  return <div className="vaultguard-app">
    <header className="vg-navbar">
      <button className="vg-brand" onClick={() => navigate('home')}><span className="vg-brand-icon"><ShieldCheck size={18} /></span><span><b>Detecting Secrets Across Version Control</b><small>Detection and Validation</small></span></button>
      <nav className="vg-nav">{(Object.keys(labels) as ViewName[]).map(item => <button key={item} className={view === item ? 'active' : ''} onClick={() => navigate(item)}>{labels[item]}</button>)}</nav>
      <div className="vg-nav-actions"><button className="vg-icon-button" aria-label="Toggle theme" onClick={toggleTheme}>{dark ? <Sun size={18} /> : <Moon size={18} />}</button><ProductButton secondary icon={<Download size={15} />} onClick={exportReport}>Export PDF Report</ProductButton></div>
    </header>
    {notice && <div className="vg-toast" role="status">{notice}<button onClick={() => setNotice('')}><X size={14} /></button></div>}
    <main>
      {view === 'home' && <HomePage onScan={() => navigate('scanner')} demoDiff={demoDiff} setDemoDiff={setDemoDiff} />}
      {view === 'scanner' && <ScannerPage scan={scan} setScan={setScan} busy={busy} run={run} expanded={expanded} setExpanded={setExpanded} />}
      {view === 'architecture' && <ArchitecturePage overview={overview} expanded={expanded} setExpanded={setExpanded} busy={busy} run={run} />}
      {view === 'benchmarks' && <BenchmarkPage benchmark={benchmark} setBenchmark={setBenchmark} busy={busy} run={run} expanded={expanded} setExpanded={setExpanded} overview={overview} />}
      {view === 'integration' && <IntegrationPage />}
    </main>
  </div>;
}

function HomePage({ onScan, demoDiff, setDemoDiff }: { onScan: () => void; demoDiff: boolean; setDemoDiff: (value: boolean) => void }) {
  const steps = [
    ['Earlier commit', 'A credential is committed', 'A secret can enter a tracked file.'],
    ['Later commit', 'The file is deleted', 'The current tree may now appear clean.'],
    ['Reachable history', 'The earlier blob remains', 'Deleting a file does not erase reachable Git history.'],
  ];
  const features = [
    ['History-aware detection', 'Inspect reachable commits and report which refs and files were covered.'],
    ['Explainable triage', 'Review the masked match, suppression reason, lifecycle evidence, and risk factors.'],
    ['Fail-closed remediation', 'Rotation remains unverified until the local mock service confirms revocation.'],
  ];
  return <div className="vg-page vg-home">
    <section className="vg-hero">
      <div className="vg-hero-copy"><span className="vg-kicker">Version control security</span><h1>Find credentials that survive deletion</h1><p>Scan a repository, inspect masked evidence across Git history, and prioritize safe remediation.</p><div className="vg-hero-actions"><ProductButton onClick={onScan} icon={<ArrowRight size={16} />}>Start a scan</ProductButton><ProductButton secondary onClick={() => document.getElementById('leak-demo')?.scrollIntoView({ behavior: 'smooth' })}>How history exposure works</ProductButton></div></div>
      <div className="vg-hero-art" aria-label="Illustrative Git history showing a deleted file that remains in history"><div className="vg-history-window"><div className="vg-history-header"><span>Illustrative history</span><code>reachable refs</code></div><div className="vg-history-line"><span className="vg-history-node" /><span className="vg-history-node" /><span className="vg-history-node vg-history-node--active" /></div><div className="vg-history-row"><span>Earlier commit</span><span>credential added</span><b>exposed</b></div><div className="vg-history-row"><span>Later commit</span><span>file deleted</span><b>still in history</b></div><div className="vg-history-row vg-history-row--active"><span>Current HEAD</span><span>working tree</span><b>scan refs</b></div></div></div>
    </section>
    <section id="leak-demo" className="vg-section"><SectionHeading eyebrow="The hidden history problem" title="Deleting a file does not erase its earlier versions" /><div className="vg-step-grid">{steps.map(([step, title, body], index) => <div className="vg-step-card" key={step}><span>{index + 1}</span><small>{step}</small><h3>{title}</h3><p>{body}</p>{index < 2 && <ArrowRight className="vg-step-arrow" size={20} />}</div>)}</div><ProductButton secondary onClick={() => setDemoDiff(!demoDiff)} icon={<Terminal size={15} />}>{demoDiff ? 'Hide illustrative history' : 'Show illustrative Git history'}</ProductButton>{demoDiff && <pre className="vg-terminal"><span className="terminal-muted">$ git log -p --all</span>{'\n'}<span className="terminal-danger">+ DB_PASSWORD=[REDACTED]</span>{'\n'}<span className="terminal-muted">The tracked file was deleted in a later commit.</span></pre>}</section>
    <section className="vg-section"><SectionHeading eyebrow="Built for action" title="From detection to evidence-led triage" /><div className="vg-feature-grid">{features.map(([title, body]) => <div className="vg-feature-card" key={title}><ShieldCheck size={22} /><h3>{title}</h3><p>{body}</p></div>)}</div></section>
  </div>;
}

function ScannerPage({ scan, setScan, busy, run, expanded, setExpanded }: any) {
  const [filter, setFilter] = useState('All Findings');
  const [repo, setRepo] = useState('');
  const [ai, setAi] = useState(true);
  const [fastScan, setFastScan] = useState(false);
  const [showLowConfidence, setShowLowConfidence] = useState(false);
  const [search, setSearch] = useState('');
  const [severity, setSeverity] = useState('All severities');
  const [type, setType] = useState('All types');
  const [scanError, setScanError] = useState('');
  const [scanJob, setScanJob] = useState<any>(null);
  const filters = ['All Findings', 'Active in Current Code', 'Hidden in Git History', 'Encoded / Branch Leaks', 'Suppressed False Positives'];
  const activeFindings = scan?.findings ?? [];
  const suppressedFindings = scan?.suppressed_findings ?? [];
  const hasResult = Array.isArray(scan?.findings);
  const lowConfidence = filter === 'Suppressed False Positives';
  const sourceFindings = lowConfidence
    ? suppressedFindings
    : [...activeFindings, ...(showLowConfidence ? suppressedFindings : [])];
  const typeOptions = [...new Set(sourceFindings.map((item: any) => String(item.secret_type ?? 'Unknown')))].sort();
  const findings = sourceFindings.filter((item: any) => {
    const lifecycle = item.lifecycle_status ?? item.git_lifecycle_state;
    const isActive = lifecycle === 'ACTIVE_IN_HEAD' || lifecycle === 'ACTIVE_HEAD';
    const isHistorical = ['DELETED_BUT_RECOVERABLE', 'UNREACHABLE_LOCAL_ONLY', 'DELETED_HISTORY'].includes(lifecycle);
    const matchesStatus = filter === 'All Findings'
      || lowConfidence
      || (filter === 'Active in Current Code' && isActive)
      || (filter === 'Hidden in Git History' && isHistorical)
      || (filter === 'Encoded / Branch Leaks' && (['BRANCH_TAG', 'REWRITTEN'].includes(lifecycle) || item.is_base64_encoded));
    const score = Number(item.risk_score ?? 0);
    const matchesSeverity = severity === 'All severities'
      || (severity === 'High / critical' && score >= 70)
      || (severity === 'Medium' && score >= 40 && score < 70)
      || (severity === 'Low' && score < 40);
    const matchesType = type === 'All types' || item.secret_type === type;
    const text = `${item.secret_type} ${item.masked_match ?? item.masked_value} ${item.file_path ?? item.file} ${item.commit_sha ?? item.commit}`.toLowerCase();
    return matchesStatus && matchesSeverity && matchesType && text.includes(search.toLowerCase());
  });
  const counts = {
    active: activeFindings.filter((item: any) => ['ACTIVE_IN_HEAD', 'ACTIVE_HEAD'].includes(item.lifecycle_status ?? item.git_lifecycle_state)).length,
    historical: activeFindings.filter((item: any) => ['DELETED_BUT_RECOVERABLE', 'UNREACHABLE_LOCAL_ONLY', 'DELETED_HISTORY'].includes(item.lifecycle_status ?? item.git_lifecycle_state)).length,
    high: activeFindings.filter((item: any) => Number(item.risk_score ?? 0) >= 70).length,
    suppressed: suppressedFindings.length,
  };
  const skippedFiles = scan?.skipped_files ?? scan?.coverage?.skipped?.items ?? [];
  const scanAction = () => {
    setScanError('');
    setScanJob(null);
    void run(
      'scan',
      () => scanCp1({ repo_url: repo || undefined, synthetic_fixture: !repo, use_ai_filter: ai, fast_scan: fastScan }, job => setScanJob(job)),
      (result: any) => {
        setScan(result);
        if (result?.partial) setScanError(`${result.error?.stage ?? 'Scan'}: ${result.error?.reason ?? 'Partial results only.'}`);
      },
      (error: any) => {
        const reason = error?.response?.data?.detail ?? error?.message ?? 'The scan could not complete.';
        setScanError(String(reason).replace(/\s+/g, ' ').slice(0, 240));
      },
    );
  };
  const handleRotated = (findingId: string, result: any) => {
    if (result?.state !== 'VERIFIED_REVOKED') return;
    setScan((current: any) => {
      const currentItem = (current?.findings ?? []).find((item: any) => item.fingerprint === findingId);
      if (!currentItem) return current;
      const resolvedItem = {
        ...currentItem,
        status: 'VERIFIED_REVOKED',
        lifecycle_badge: 'Verified revoked in local sandbox',
        shap: [],
        remediation_playbook: {
          ...currentItem.remediation_playbook,
          rotation_status: 'VERIFIED_REVOKED_IN_LOCAL_SANDBOX',
        },
      };
      return {
        ...current,
        findings: (current.findings ?? []).filter((item: any) => item.fingerprint !== findingId),
        resolved_findings: [...(current.resolved_findings ?? []), resolvedItem],
        summary: {
          ...current.summary,
          active_head: currentItem.lifecycle_status === 'ACTIVE_IN_HEAD'
            ? Math.max(0, Number(current.summary.active_head) - 1)
            : current.summary.active_head,
          total: Math.max(0, Number(current.summary.total) - 1),
        },
      };
    });
  };
  const coverage = scan?.coverage;
  const coverageLabel = coverage
    ? coverage.completeness === 'complete' ? 'Complete' : 'Partial'
    : scanError ? (scanError.toLowerCase().includes('refus') ? 'Refused' : 'Partial') : 'Not scanned';
  const verdict = !hasResult
    ? 'Ready to scan'
    : scan?.partial
      ? 'Partial results'
      : activeFindings.length === 0
        ? 'No secrets detected'
        : `${activeFindings.length} real secret${activeFindings.length === 1 ? '' : 's'} found`;
  const verdictTone = !hasResult || scan?.partial ? 'neutral' : activeFindings.length ? 'danger' : 'success';
  const partialFindings = scanJob?.partial_findings ?? [];
  const exportJson = () => downloadText('secretguard-scan.json', JSON.stringify(scan, null, 2), 'application/json');
  const exportSarif = () => {
    const rules = [...new Set(activeFindings.map((item: any) => item.rule_id ?? item.secret_type))].map(id => ({ id }));
    const sarif = {
      version: '2.1.0',
      $schema: 'https://json.schemastore.org/sarif-2.1.0.json',
      runs: [{
        tool: { driver: { name: 'SecretGuard', rules } },
        results: activeFindings.map((item: any) => ({
          ruleId: item.rule_id ?? item.secret_type,
          level: Number(item.risk_score ?? 0) >= 70 ? 'error' : 'warning',
          message: { text: `${item.secret_type}: ${item.masked_match ?? '[REDACTED]'}` },
          locations: [{ physicalLocation: { artifactLocation: { uri: item.file_path }, region: { startLine: item.line_number ?? item.line ?? 1 } } }],
          properties: { lifecycle: item.lifecycle_status, riskScore: item.risk_score, rotationStatus: item.remediation_playbook?.rotation_status },
        })),
      }],
    };
    downloadText('secretguard-scan.sarif', JSON.stringify(sarif, null, 2), 'application/sarif+json');
  };

  return <div className="vg-page">
    <SectionHeading eyebrow="Repository scan" title="Find and triage exposed credentials" subtitle="Scan a local repository or an authorized HTTPS URL. Results include reachable Git history and explicit coverage limits." />
    <section className="vg-control-card vg-scan-controls">
      <label className="vg-repository-label" htmlFor="repository-input">Repository URL or local path</label>
      <div className="vg-control-row">
        <input id="repository-input" value={repo} onChange={event => setRepo(event.target.value)} placeholder="https://host/owner/repository.git or C:\\path\\to\\repository" />
        <ProductButton onClick={scanAction} icon={<Play size={15} />}>{busy === 'scan' ? 'Scanning...' : 'Scan repository'}</ProductButton>
      </div>
      <div className="vg-scan-options">
        <label className="vg-toggle"><input type="checkbox" checked={fastScan} onChange={event => setFastScan(event.target.checked)} /><span />Fast scan</label>
        <label className="vg-toggle"><input type="checkbox" checked={ai} onChange={event => setAi(event.target.checked)} /><span />AI filter</label>
        <button className="vg-text-button" onClick={() => { setRepo(''); setScanError(''); }}>Try demo repo</button>
      </div>
      <p className="vg-authorisation-note">Only scan repositories you are authorized to assess. HTTPS remotes must pass the backend's public-host safety checks.</p>
      {busy === 'scan' && <div className="vg-stage-progress" aria-live="polite">
        <div className="vg-elapsed">Elapsed: {scanJob?.elapsed_ms ?? 0} ms | Findings so far: {partialFindings.length}</div>
        {(scanJob?.stages ?? []).map((stage: any) => <span key={stage.name} className={stage.status}><b>{stage.name}</b><small>{stage.status}{stage.duration_ms ? ` | ${stage.duration_ms} ms` : ''}</small></span>)}
      </div>}
      {busy === 'scan' && partialFindings.length > 0 && <div className="vg-partial-findings" role="status">
        <b>Preliminary matches (values redacted)</b>
        {partialFindings.map((item: any, index: number) => <div key={`${item.file}-${item.line}-${index}`}><code>{item.file}:{item.line}</code><span>{item.masked_value}</span><small>{String(item.commit).slice(0, 8)}</small></div>)}
      </div>}
      {scanError && <div className="vg-scan-error" role="alert"><div><b>Scan needs attention</b><p>{scanError}</p></div><ProductButton secondary onClick={scanAction}>Retry scan</ProductButton></div>}
      <div className="vg-export-actions">
        <button disabled={!hasResult} onClick={exportJson}>Export JSON</button>
        <button disabled={!hasResult} onClick={exportSarif}>Export SARIF</button>
        <button disabled={!hasResult} onClick={() => downloadPdf('SecretGuard scan report', [{ heading: 'Summary', body: JSON.stringify(scan?.summary ?? {}) }, { heading: 'Coverage', body: coverage?.human_summary ?? 'NOT MEASURED' }])}>Export PDF</button>
      </div>
      <ProductButton secondary onClick={() => setExpanded(expanded === 'pipeline' ? null : 'pipeline')}>{expanded === 'pipeline' ? 'Hide pipeline' : 'Show pipeline'}</ProductButton>
      {expanded === 'pipeline' && <Pipeline stages={scanJob?.stages} />}
    </section>

    <section className={`vg-result-panel vg-verdict vg-verdict-${verdictTone}`} aria-live="polite">
      <div className="vg-verdict-heading"><h2>{verdict}</h2><span className={`vg-coverage-badge vg-coverage-${coverageLabel.toLowerCase().replace(' ', '-')}`}>Coverage: {coverageLabel}</span></div>
      {hasResult && <p className="vg-result-metadata">{scan.repository ?? (repo || 'Demo repository')} | {coverage?.commits_actually_scanned ?? 'Not measured'} commits | {coverage?.refs?.branch_count ?? 'Not measured'} branches | {coverage?.refs?.tag_count ?? 'Not measured'} tags | {scanJob?.elapsed_ms ?? 'Not measured'} ms elapsed</p>}
      {hasResult
        ? (activeFindings.length === 0 && !scan?.partial ? <ScanEmptyState /> : <p>{scan?.meaning ?? 'Partial results do not represent a complete scan.'}</p>)
        : <p>Choose a repository and start a scan. A clean result only covers the refs, file types, and patterns reported below.</p>}
      {coverage && <p className="vg-coverage-note">{coverage.human_summary}</p>}
      {hasResult && <p><b>Rules applied:</b> {(scan?.rules_applied ?? []).join(', ') || 'Not reported'}</p>}
      <details className="vg-skipped-list">
        <summary>Skipped files ({skippedFiles.length})</summary>
        {skippedFiles.length
            ? <ul>{skippedFiles.map((item: any, index: number) => <li key={`${item.path}-${item.reason}-${index}`}><code>{item.path}</code> - {item.reason}</li>)}</ul>
          : <p>No skipped files reported.</p>}
      </details>
    </section>

    <div className="vg-kpi-grid vg-scan-summary">
      <Kpi title="Active in HEAD" value={hasResult ? counts.active : 'N/A'} tone="rose" />
      <Kpi title="Deleted but recoverable" value={hasResult ? counts.historical : 'N/A'} tone="amber" />
      <Kpi title="High severity" value={hasResult ? counts.high : 'N/A'} tone="blue" />
      <Kpi title="Suppressed (with reasons)" value={hasResult ? counts.suppressed : 'N/A'} tone="emerald" />
    </div>

    <aside className="vg-how-to-read">
      <b>How to read this</b>
      <p>Active means the value is present in HEAD. Deleted but recoverable means it remains in a reachable commit. Rotation is not verified by deleting a file or rewriting history; the rotation action uses only the local mock service.</p>
      <p>Risk is a weighted prioritization score, not a credential-validity check. Open a finding to inspect its factor-by-factor breakdown.</p>
    </aside>

    <section className="vg-panel">
      <div className="vg-panel-heading">
        <div><span className="vg-kicker">Review queue</span><h2>Findings</h2></div>
        <div className="vg-filter-row">{filters.map(item => <button key={item} className={filter === item ? 'active' : ''} onClick={() => { setFilter(item); if (item === 'Suppressed False Positives') setShowLowConfidence(true); }}>{item}</button>)}</div>
      </div>
      <div className="vg-finding-filters">
        <input aria-label="Search findings" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search type, file, masked value, commit" />
        <select aria-label="Filter by severity" value={severity} onChange={event => setSeverity(event.target.value)}>{['All severities', 'High / critical', 'Medium', 'Low'].map(option => <option key={option}>{option}</option>)}</select>
        <select aria-label="Filter by type" value={type} onChange={event => setType(event.target.value)}><option>All types</option>{typeOptions.map(option => <option key={option}>{option}</option>)}</select>
        <label className="vg-toggle"><input type="checkbox" checked={showLowConfidence} onChange={event => setShowLowConfidence(event.target.checked)} /><span />Show low-confidence</label>
      </div>
      {findings.length
        ? findings.map((item: any, index: number) => <FindingCard key={`${item.fingerprint ?? item.file}-${item.line_number ?? item.line}-${index}`} item={item} expanded={expanded === item.fingerprint} onToggle={() => setExpanded(expanded === item.fingerprint ? null : item.fingerprint)} busy={busy} run={run} onRotated={handleRotated} />)
        : <p className="vg-empty-queue">{hasResult ? 'No findings match these filters.' : 'Run a scan to populate this list.'}</p>}
    </section>

    {(scan?.resolved_findings ?? []).length > 0 && <section className="vg-panel vg-resolved-panel">
      <div className="vg-panel-heading"><div><span className="vg-kicker">Remediation history</span><h2>Mock service verification</h2></div><span className="vg-success-note"><CheckCircle2 size={14} /> Provider status was not checked</span></div>
      {scan.resolved_findings.map((item: any) => <div className="vg-resolved-row" key={item.fingerprint}><span>{item.secret_type}</span><span>{item.file_path}</span><b>Verified revoked in local sandbox</b></div>)}
    </section>}
  </div>;
}
function FindingCard({ item: rawItem, expanded, onToggle, busy, run, onRotated }: any) {
  const item = { ...rawItem, masked_match: maskSecret(rawItem.masked_match ?? rawItem.masked_value), commit_sha: maskCommit(rawItem.commit_sha ?? rawItem.commit) };
  const lifecycle = item.lifecycle_status ?? item.git_lifecycle_state ?? 'Unknown';
  const suppressed = item.status === 'SUPPRESSED_DECOY' || Boolean(item.suppression_reason);
  const verified = item.status === 'VERIFIED_REVOKED';
  const rotationStatus = item.remediation_playbook?.rotation_status ?? 'ROTATION_NOT_VERIFIED';
  const currentStep = verified ? 3 : rotationStatus.includes('ROTATED') ? 2 : 1;
  const steps = ['Detected', 'Validity unknown', 'Rotated unverified', 'Verified revoked'];
  const rotate = () => run('rotate', () => rotateCp1(item.fingerprint), (result: any) => onRotated(item.fingerprint, result));
  const riskTerms = item.risk_breakdown?.terms ?? {};
  const riskLabels: Record<string, string> = {
    lifecycle: 'Lifecycle',
    secret_severity: 'Secret type severity',
    exposure_duration: 'Exposure duration',
    public_repository: 'Public repository',
    entropy: 'Entropy',
  };
  const statusText = suppressed
    ? `Suppressed: ${item.suppression_reason ?? 'unspecified reason'}`
    : item.lifecycle_badge ?? lifecycle;

  return <article className="vg-finding">
    <div className="vg-finding-row">
      <span className={`vg-score ${Number(item.risk_score) >= 90 ? 'critical' : Number(item.risk_score) >= 70 ? 'high' : ''}`} title={item.risk_breakdown?.formula ?? 'Risk breakdown not reported.'}>{Number(item.risk_score ?? 0)}<small>/100</small></span>
      <div className="vg-finding-main"><b>{item.secret_type ?? 'Secret match'}</b><span>{item.masked_match ?? '[REDACTED]'}</span></div>
      <div className="vg-finding-file"><b>{item.file_path ?? item.file ?? 'Path unavailable'}</b><span>Line {item.line_number ?? item.line ?? 'Not reported'} | Commit {String(item.commit_sha ?? item.commit ?? 'Not reported').slice(0, 7)}</span></div>
      <span className={`vg-status ${verified ? 'status-safe' : suppressed ? 'status-muted' : lifecycle === 'ACTIVE_IN_HEAD' ? 'status-danger' : 'status-warning'}`} title={verified ? 'Verified by the local mock service only; provider status was not checked.' : suppressed ? `Suppression reason: ${item.suppression_reason ?? 'unspecified'}` : lifecycle}>{statusText}</span>
      <button className="vg-inspect" aria-expanded={expanded} onClick={onToggle}>{expanded ? 'Close details' : 'View details'} {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</button>
    </div>
    {expanded && <div className="vg-finding-detail">
      <section><h3>Evidence and exposure</h3><dl className="vg-evidence-list">
        <dt>Location</dt><dd>{item.file_path ?? item.file ?? 'Path not reported'}:{item.line_number ?? item.line ?? 'Not reported'}</dd>
        <dt>First seen</dt><dd>{String(item.first_seen_commit ?? 'Not measured').slice(0, 12)}</dd>
        <dt>Last seen</dt><dd>{String(item.last_seen_commit ?? item.commit_sha ?? 'Not measured').slice(0, 12)}</dd>
        <dt>Removed in</dt><dd>{item.removed_in_commit ? String(item.removed_in_commit).slice(0, 12) : 'Not removed / not measured'}</dd>
        <dt>Days exposed</dt><dd>{item.days_exposed ?? 'Not measured'}</dd>
        <dt>Recoverable from fresh clone</dt><dd>{item.recoverable_from_fresh_clone === true ? 'Yes' : item.recoverable_from_fresh_clone === false ? 'No' : 'Not measured'}</dd>
        <dt>Recoverable from local objects</dt><dd>{item.recoverable_from_local_objects === true ? 'Yes' : item.recoverable_from_local_objects === false ? 'No' : 'Not measured'}</dd>
        {item.suppression_reason && <><dt>Suppression reason</dt><dd>{item.suppression_reason}</dd></>}
      </dl></section>
      <section><h3 title="Weighted prioritization score; not a validity result">Risk score: {Number(item.risk_score ?? 0)}/100</h3>
        <p className="vg-risk-formula">{item.risk_breakdown?.formula ?? 'Risk breakdown not reported.'}</p>
        {Object.entries(riskTerms).map(([key, term]: [string, any]) => <div className="vg-risk-term" key={key}><span>{riskLabels[key] ?? key}</span><b>{Number(term.points ?? 0).toFixed(2)} pts</b><small>{Math.round(Number(term.factor ?? 0) * 100)}% factor | {Math.round(Number(term.weight ?? 0) * 100)}% weight</small></div>)}
      </section>
      <section><h3>Remediation playbook</h3>
        <p>{item.remediation_playbook?.first_step ?? item.recommended_action ?? 'Rotate or revoke first; rotation is not verified.'}</p>
        <p className="vg-rotation-status">Status: {rotationStatus === 'VERIFIED_REVOKED_IN_LOCAL_SANDBOX' ? 'Verified revoked in local sandbox; provider status not checked' : 'Rotation not verified'}</p>
        {item.remediation_playbook?.history_rewrite_commands?.length > 0 && <details><summary>Optional history cleanup commands (after rotation)</summary><ol>{item.remediation_playbook.history_rewrite_commands.map((command: string) => <li key={command}><code>{command}</code></li>)}</ol><p>{item.remediation_playbook.warning}</p></details>}
        <h3>Credential lifecycle</h3>
        <ol className="vg-rotation-steps" aria-label="Credential lifecycle">
          {steps.map((step, index) => <li className={index <= currentStep ? 'current' : ''} key={step}><i>{index + 1}</i>{step}</li>)}
        </ol>
        {!suppressed && !verified && <ProductButton onClick={rotate} icon={<RotateCw size={15} />}>{busy === 'rotate' ? 'Checking local sandbox...' : 'Verify with local mock service'}</ProductButton>}
        {verified && <p className="vg-success-note"><CheckCircle2 size={14} /> Revocation was verified only in the local mock service.</p>}
      </section>
    </div>}
  </article>;
}
function ArchitecturePage({ overview, expanded, setExpanded, busy, run }: any) {
  return <div className="vg-page"><SectionHeading eyebrow="Trust center" title="Security & Architecture" subtitle="Understand how VaultGuard moves from an untrusted repository to a verified safe credential." /><Pipeline /><div className="vg-accordion-list"><Accordion title="Why Git History Leaks Happen · Live Proof & OWASP Standards" open={expanded === 'proof'} onToggle={() => setExpanded(expanded === 'proof' ? null : 'proof')}>{<><Timeline overview={overview} /><ProductButton onClick={() => run('o1', reproduceO1)}>{busy === 'o1' ? 'Running proof...' : 'Run Git History Proof'}</ProductButton></>}</Accordion><Accordion title="System Capabilities & Performance Guarantees" open={expanded === 'capabilities'} onToggle={() => setExpanded(expanded === 'capabilities' ? null : 'capabilities')}><div className="vg-detail-grid">{['History traversal across all refs', 'Regex + entropy + context detection', 'Zero plaintext persistence', 'Sub-five-second scan target', 'Peak memory below 512 MB', 'Offline sandbox safety'].map(item => <div key={item}><CheckCircle2 size={16} /> {item}</div>)}</div></Accordion><Accordion title="Threat Model & Abuse Protection" open={expanded === 'threats'} onToggle={() => setExpanded(expanded === 'threats' ? null : 'threats')}><ThreatTable /></Accordion><Accordion title="System Health & Test Oracle" open={expanded === 'health'} onToggle={() => setExpanded(expanded === 'health' ? null : 'health')}><Health overview={overview} /></Accordion></div></div>;
}

function BenchmarkPage({ benchmark, setBenchmark, busy, run, expanded, setExpanded, overview }: any) {
  const format = (value: any, suffix = '%') => Number.isFinite(value) ? `${Number(value).toFixed(1)}${suffix}` : 'NOT MEASURED';
  const runBenchmark = () => run('benchmark', runCp1Benchmark, (result: any) => setBenchmark(benchmarkRows(result.approaches ?? [])));
  return <div className="vg-page">
    <SectionHeading eyebrow="Measured performance" title="AI Benchmarks" subtitle="Only recorded benchmark results are shown. Missing values are labeled NOT MEASURED." action={<ProductButton onClick={runBenchmark} icon={<RotateCw size={15} />}>{busy === 'benchmark' ? 'Running...' : 'Run live benchmark'}</ProductButton>} />
    <section className="vg-panel">
      {benchmark.length === 0
        ? <p className="vg-empty-queue">NOT MEASURED. Run the benchmark when the backend and its fixture dataset are available.</p>
        : <>
          <div className="vg-benchmark-bars">{benchmark.map((row: any) => <div key={row.name} className="vg-benchmark-group"><b>{row.name}</b>{[['Precision', row.precision], ['Recall', row.recall], ['F1 score', row.f1]].map(([label, value]: any[]) => <div className="vg-metric-bar" key={label}><span>{label}</span><i><em style={{ width: `${Number.isFinite(value) ? value : 0}%` }} /></i><strong>{format(value)}</strong></div>)}</div>)}</div>
          <div className="vg-table-wrap"><table className="vg-table"><thead><tr><th>Approach</th><th>Precision</th><th>Recall</th><th>F1</th><th>False positives</th><th>Scan time</th><th>Memory</th><th>Missed active</th></tr></thead><tbody>{benchmark.map((row: any) => <tr key={row.name}><td><b>{row.name}</b></td><td>{format(row.precision)}</td><td>{format(row.recall)}</td><td>{format(row.f1)}</td><td>{format(row.fpr)}</td><td>{format(row.time, ' ms')}</td><td>{format(row.memory, ' MB')}</td><td>{row.unsafe ?? 'NOT MEASURED'}</td></tr>)}</tbody></table></div>
        </>}
    </section>
    <div className="vg-accordion-list"><Accordion title="Feature ablation results" open={expanded === 'ablation'} onToggle={() => setExpanded(expanded === 'ablation' ? null : 'ablation')}><Ablation overview={overview} /></Accordion></div>
  </div>;
}
function IntegrationPage() {
  const snippets = {
    'Pre-Commit Hook': `repos:\n  - repo: local\n    hooks:\n      - id: secret-history-scan\n        name: Scan Git history for secrets\n        entry: python scripts/pre_commit_hook.py\n        language: system\n        stages: [commit]`,
    'GitHub Actions': `name: Secret history scan\non: [pull_request]\njobs:\n  scan:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: python scripts/pre_commit_hook.py`,
    'Docker Quickstart': `docker compose up --build\n# Frontend: http://localhost:5173\n# API docs: http://localhost:8000/docs`,
  };
  const [active, setActive] = useState(Object.keys(snippets)[0]);
  return <div className="vg-page"><SectionHeading eyebrow="Developer workflow" title="CI/CD Integration" subtitle="Example setup snippets. Validate paths and policy for your repository before enabling a blocking check." /><section className="vg-panel"><div className="vg-panel-heading"><div><span className="vg-kicker">Copyable setup examples</span><h2>Protect future commits</h2></div><Terminal size={22} /></div><div className="vg-code-tabs">{Object.keys(snippets).map(item => <button className={active === item ? 'active' : ''} key={item} onClick={() => setActive(item)}>{item}</button>)}</div><div className="vg-code-header"><span>{active}</span><CopySnippet value={snippets[active as keyof typeof snippets]} /></div><pre className="vg-code-block">{snippets[active as keyof typeof snippets]}</pre><p className="vg-muted">NOT MEASURED: team adoption, branch protection, and CI outcomes require local setup and approval.</p></section></div>;
}
function SectionHeading({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle?: string; action?: React.ReactNode }) { return <div className="vg-section-heading"><div><span className="vg-kicker">{eyebrow}</span><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{action}</div>; }
function Kpi({ title, value, tone }: { title: string; value: string; tone: string }) { return <div className={`vg-kpi vg-kpi-${tone}`}><span>{title}</span><b>{value}</b></div>; }
function Pipeline({ stages }: { stages?: any[] } = {}) {
  const names = ['clone', 'preflight', 'scan', 'parse', 'filter', 'dedupe', 'mask', 'lifecycle', 'report'];
  const byName = new Map((stages ?? []).map(stage => [stage.name, stage]));
  return <div className="vg-pipeline">{names.map((name, index) => {
    const stage = byName.get(name);
    return <div key={name}><span>{index + 1}</span><b>{name}</b><small>{stage?.status ?? 'queued'} · {stage?.count ?? 0} · {stage?.duration_ms ?? 0} ms</small>{(stage?.sub_steps ?? []).map((sub: any) => <small key={sub.name}>{sub.name}: {sub.status} · {sub.duration_ms} ms</small>)}{index < names.length - 1 && <ArrowRight size={17} />}</div>;
  })}</div>;
}
function Timeline({ overview }: any) {
  const timeline = overview?.reproduction?.timeline;
  if (!Array.isArray(timeline) || timeline.length === 0) return <p className="vg-empty-queue">NOT MEASURED. Run the Git history proof to record a timeline.</p>;
  return <div className="vg-timeline">{timeline.slice(0, 3).map((item: any, index: number) => <div key={`${item.sha ?? 'step'}-${index}`}><span>{index + 1}</span><b>{item.message ?? 'Commit event'}</b><code>{item.sha ? String(item.sha).slice(0, 12) : 'Commit not reported'}</code></div>)}</div>;
}
function ThreatTable() {
  const rows = [
    ['Untrusted repository', 'Isolated repository traversal and URL validation'],
    ['Resource exhaustion', 'Stage and job timeouts'],
    ['Secret disclosure', 'Masked finding payloads and redacted reports'],
    ['Rotation claims', 'Fail-closed local verification state machine'],
  ];
  return <table className="vg-table"><thead><tr><th>Concern</th><th>Implemented control</th></tr></thead><tbody>{rows.map(row => <tr key={row[0]}><td>{row[0]}</td><td>{row[1]}</td></tr>)}</tbody></table>;
}
function Health({ overview }: any) {
  const dependencies = overview?.dependencies ?? {};
  const entries = [
    ['Git CLI', 'git_cli'], ['GitPython', 'gitpython'], ['Gitleaks', 'gitleaks'],
    ['XGBoost', 'xgboost'], ['SHAP', 'shap'], ['Database', 'database'],
    ['Docker rotation sandbox', 'docker_rotation_sandbox'],
  ];
  return <div className="vg-health-grid">{entries.map(([label, key]) => {
    const available = dependencies[key]?.available;
    return <div className={available === true ? '' : 'vg-health-unavailable'} key={key}><b>{label}</b><span>{available === true ? 'Available' : available === false ? 'Unavailable' : 'Not measured'}</span></div>;
  })}</div>;
}
function Ablation({ overview }: any) {
  const rows = overview?.extras?.xgboost_ablation?.stages ?? [];
  if (rows.length === 0) return <p className="vg-empty-queue">NOT MEASURED. No feature ablation results were returned.</p>;
  return <div className="vg-ablation">{rows.map((row: any) => {
    const f1 = row.f1 ?? row.metrics?.f1;
    const measured = Number.isFinite(f1);
    return <div key={row.name}><span>{row.name}</span><i><em style={{ width: `${measured ? f1 * 100 : 0}%` }} /></i><b>{measured ? `${(f1 * 100).toFixed(1)}%` : 'NOT MEASURED'}</b></div>;
  })}</div>;
}
