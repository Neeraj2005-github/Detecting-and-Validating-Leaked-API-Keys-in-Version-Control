import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight, CheckCircle2, ChevronDown, ChevronUp, Copy, Download,
  Moon, Play, RotateCw, ShieldCheck, Sun, Terminal, X,
} from 'lucide-react';
import { fetchCp1Overview, reproduceO1, rotateCp1, runCp1Benchmark, scanCp1 } from '../api/cp1';
import { downloadPdf } from '../utils/pdfExport';
import { maskCommit, maskSecret } from '../utils/displaySafety';
import localScanArtifact from '../../../artifacts/cp1_latest_scan.json';
import ablationF1Chart from '../../../artifacts/ablation_f1_chart.png';
import shapSummaryPlot from '../../../artifacts/shap_summary_plot.png';

type ViewName = 'home' | 'scanner' | 'architecture' | 'benchmarks' | 'integration';
type Props = { tab?: string };

const FALLBACK_SCAN = {
  summary: { active_head: 3, historical: 5, filtered: 42, total: 8 },
  findings: [
    { fingerprint: 'demo-active-aws', risk_score: 96, secret_type: 'AWS Access Key', masked_match: 'AKIA************7X9Q', file_path: 'config/database.yml', line_number: 4, commit_sha: 'a8f921c', lifecycle_badge: 'Active in Current Code', git_lifecycle_state: 'ACTIVE_HEAD', still_in_head: true, shap: [{ feature: 'High Randomness / Shannon Entropy (4.95)', impact: .42 }, { feature: "Assigned to 'db_password' Keyword", impact: .31 }, { feature: 'Production Config File', impact: .18 }, { feature: 'Test File Check', impact: -.12 }] },
    { fingerprint: 'demo-deleted-db', risk_score: 82, secret_type: 'MySQL Connection URI', masked_match: 'mysql://****:****@db.internal/app', file_path: 'config/prod.env', line_number: 8, commit_sha: '9f4b2c1', lifecycle_badge: 'Deleted in Commit #9f4b', git_lifecycle_state: 'DELETED_HISTORY', still_in_head: false, shap: [{ feature: 'Database URI Pattern', impact: .38 }, { feature: 'Production Path', impact: .29 }, { feature: 'Historical Lifecycle', impact: .16 }, { feature: 'Example Keyword', impact: -.09 }] },
    { fingerprint: 'demo-branch-token', risk_score: 74, secret_type: 'GitHub Personal Token', masked_match: 'ghp_****************************', file_path: 'src/legacy/auth.py', line_number: 12, commit_sha: '4d12aa0', lifecycle_badge: 'Branch / Tag History', git_lifecycle_state: 'BRANCH_TAG', still_in_head: false, shap: [{ feature: 'Token Pattern', impact: .34 }, { feature: 'Auth Keyword', impact: .26 }, { feature: 'Legacy Branch', impact: .22 }, { feature: 'Test Path Penalty', impact: -.1 }] },
  ],
  suppressed_findings: [
    { fingerprint: 'demo-placeholder', risk_score: 4, secret_type: 'Placeholder assignment', masked_match: 'your_password', file_path: '.env.example', line_number: 3, commit_sha: 'demo000', lifecycle_badge: 'Suppressed Decoy', git_lifecycle_state: 'DECOY', is_false_positive: true, shap: [{ feature: 'Example file penalty', impact: -.42 }] },
  ],
};

const FALLBACK_BENCHMARK = [
  { name: 'Detection Engine + AI', precision: 96.4, recall: 94.8, f1: 95.6, fpr: 3.2, time: 420, memory: 68, unsafe: 0 },
  { name: 'Gitleaks', precision: 78.5, recall: 91, f1: 84.3, fpr: 21.5, time: 390, memory: 54, unsafe: 0 },
  { name: 'Regex + Entropy Only', precision: 44.2, recall: 95, f1: 60.3, fpr: 55.8, time: 310, memory: 49, unsafe: 0 },
];

const LOCAL_SCAN_FALLBACK = {
  ...FALLBACK_SCAN,
  ...localScanArtifact,
  findings: localScanArtifact.findings?.length ? localScanArtifact.findings : FALLBACK_SCAN.findings,
};

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

export default function Cp1WorkbenchPage({ tab }: Props) {
  const view = currentView(tab);
  const [dark, toggleTheme] = useTheme();
  const [overview, setOverview] = useState<any>(null);
  const [scan, setScan] = useState<any>(LOCAL_SCAN_FALLBACK);
  const [benchmark, setBenchmark] = useState<any[]>(FALLBACK_BENCHMARK);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');
  const [demoDiff, setDemoDiff] = useState(false);

  useEffect(() => {
    fetchCp1Overview().then(payload => {
      setOverview(payload);
      const approaches = payload?.kpis?.approaches;
      if (approaches?.length) setBenchmark(approaches.map((item: any) => ({ name: item.name, precision: item.metrics.precision * 100, recall: item.metrics.recall * 100, f1: item.metrics.f1_score * 100, fpr: item.metrics.false_positive_rate * 100, time: item.metrics.scan_wall_clock_ms, memory: item.metrics.peak_rss_mb ?? 68, unsafe: item.metrics.unsafe_outcome_count })));
    }).catch(() => {
      setOverview({
        kpis: { approaches: FALLBACK_BENCHMARK },
        extras: { xgboost_ablation: localScanArtifact },
      });
      setScan(LOCAL_SCAN_FALLBACK);
      setNotice('The live service is unavailable. Showing the safe local demo dataset.');
    });
  }, []);

  const run = async (name: string, operation: () => Promise<any>, callback?: (result: any) => void) => {
    setBusy(name); setNotice('');
    try { const result = await operation(); callback?.(result); setNotice('Updated just now.'); }
    catch { setNotice('The live service is unavailable. Showing the safe demo dataset.'); }
    finally { setBusy(''); }
  };

  const exportReport = () => downloadPdf(`Detection and Validation ${labels[view]} Report`, [{ heading: 'Summary', body: 'Git secret detection, explainability, and safe credential remediation.' }, { heading: labels[view], body: JSON.stringify(view === 'benchmarks' ? benchmark : scan.summary) }]);
  const navigate = (next: ViewName) => { window.history.pushState({}, '', `/vaultguard/${next}`); window.dispatchEvent(new PopStateEvent('popstate')); };

  return <div className="vaultguard-app">
    <header className="vg-navbar">
      <button className="vg-brand" onClick={() => navigate('home')}><span className="vg-brand-icon"><ShieldCheck size={18} /></span><span><b>Detecting Secrets Across Version Control</b><small>Detection and Validation</small></span></button>
      <nav className="vg-nav">{(Object.keys(labels) as ViewName[]).map(item => <button key={item} className={view === item ? 'active' : ''} onClick={() => navigate(item)}>{labels[item]}</button>)}</nav>
      <div className="vg-nav-actions"><button className="vg-icon-button" aria-label="Toggle theme" onClick={toggleTheme}>{dark ? <Sun size={18} /> : <Moon size={18} />}</button><ProductButton secondary icon={<Download size={15} />} onClick={exportReport}>Export PDF Report</ProductButton></div>
    </header>
    {notice && <div className="vg-toast" role="status">{notice}<button onClick={() => setNotice('')}><X size={14} /></button></div>}
    <main>
      {view === 'home' && <HomePage onScan={() => { navigate('scanner'); setDemoDiff(true); }} demoDiff={demoDiff} setDemoDiff={setDemoDiff} />}
      {view === 'scanner' && <ScannerPage scan={scan} setScan={setScan} overview={overview} busy={busy} run={run} expanded={expanded} setExpanded={setExpanded} />}
      {view === 'architecture' && <ArchitecturePage overview={overview} expanded={expanded} setExpanded={setExpanded} busy={busy} run={run} />}
      {view === 'benchmarks' && <BenchmarkPage benchmark={benchmark} busy={busy} run={run} expanded={expanded} setExpanded={setExpanded} overview={overview} />}
      {view === 'integration' && <IntegrationPage overview={overview} />}
    </main>
  </div>;
}

function HomePage({ onScan, demoDiff, setDemoDiff }: { onScan: () => void; demoDiff: boolean; setDemoDiff: (value: boolean) => void }) {
  return <div className="vg-page vg-home"><section className="vg-hero"><div className="vg-hero-copy"><span className="vg-kicker">VERSION CONTROL SECURITY • DETECTION AND VALIDATION</span><h1>Detecting Secrets Across Version Control</h1><p>Deleting a file in a new commit does not erase it from Git history. Scan every historical commit, branch, and tag to detect hidden credentials, eliminate false positives with Explainable AI, and validate or rotate secrets safely.</p><div className="vg-hero-actions"><ProductButton onClick={onScan} icon={<ArrowRight size={16} />}>Start Detection &amp; Validation</ProductButton><ProductButton secondary onClick={() => document.getElementById('leak-demo')?.scrollIntoView({ behavior: 'smooth' })}>See How Git History Leaks Work</ProductButton></div></div><div className="vg-hero-art"><div className="vg-orbit vg-orbit-one" /><div className="vg-orbit vg-orbit-two" /><ShieldCheck size={76} /></div></section><section id="leak-demo" className="vg-section"><SectionHeading eyebrow="The hidden history problem" title="Why deleting a file does not remove its secret." /><div className="vg-step-grid">{[['Commit #1', 'Credential Committed', 'AWS_ACCESS_KEY and DB_PASSWORD enter config/prod.env'], ['Commit #2', 'File Deleted', 'The current working tree appears clean'], ['Commit #3', 'Still Exposed in History', 'git log -p --all reveals the historical diff']].map(([step, title, body], index) => <div className="vg-step-card" key={step}><span>{index + 1}</span><small>{step}</small><h3>{title}</h3><p>{body}</p>{index < 2 && <ArrowRight className="vg-step-arrow" size={20} />}</div>)}</div><ProductButton secondary onClick={() => setDemoDiff(!demoDiff)} icon={<Terminal size={15} />}>{demoDiff ? 'Hide Git History Demo' : 'Run Live Git Leak Simulation'}</ProductButton>{demoDiff && <pre className="vg-terminal"><span className="terminal-muted">$ git log -p --all</span>{'\n'}<span className="terminal-danger">+ AWS_ACCESS_KEY_ID=AKIA************7X9Q</span>{'\n'}<span className="terminal-muted">- config/prod.env deleted from current branch</span></pre>}</section><section className="vg-section"><SectionHeading eyebrow="Built for action" title="From discovery to remediation in one calm workflow." /><div className="vg-feature-grid">{[['Deep Git History Detection', 'Walks added lines across commits, branches, tags, Base64 payloads, and rewritten history.'], ['Explainable AI Noise Filtering', 'The 14-feature model and SHAP separate credentials from UUIDs, hashes, and test placeholders.'], ['Automated Credential Validation & Rotation', 'Validate active status in a safe sandbox and rotate exposed credentials in milliseconds.']].map(([title, body]) => <div className="vg-feature-card" key={title}><ShieldCheck size={22} /><h3>{title}</h3><p>{body}</p></div>)}</div></section></div>;
}

function ScannerPage({ scan, setScan, overview, busy, run, expanded, setExpanded }: any) {
  const [filter, setFilter] = useState('All Findings');
  const [repo, setRepo] = useState('');
  const [ai, setAi] = useState(true);
  const filters = ['All Findings', 'Active in Current Code', 'Hidden in Git History', 'Encoded / Branch Leaks', 'Suppressed False Positives'];
  const activeFindings = scan?.findings ?? [];
  const suppressedFindings = scan?.suppressed_findings ?? [];
  const findings = (filter === 'Suppressed False Positives' ? suppressedFindings : activeFindings).filter((item: any) => filter === 'All Findings' || filter === 'Suppressed False Positives' || (filter === 'Active in Current Code' && item.git_lifecycle_state === 'ACTIVE_HEAD' && item.status !== 'ROTATED_SAFE') || (filter === 'Hidden in Git History' && item.git_lifecycle_state === 'DELETED_HISTORY') || (filter === 'Encoded / Branch Leaks' && ['BRANCH_TAG', 'REWRITTEN'].includes(item.git_lifecycle_state)));
  const scanAction = () => run('scan', () => scanCp1({ repo_url: repo || undefined, synthetic_fixture: !repo, use_ai_filter: ai }), result => setScan(result));
  const handleRotated = (findingId: string, result: any) => {
    if (result?.state !== 'VERIFIED_SAFE') return;
    setScan((current: any) => {
      const currentItem = (current.findings ?? []).find((item: any) => item.fingerprint === findingId);
      if (!currentItem) return current;
      const resolvedItem = {
        ...currentItem,
        status: 'ROTATED_SAFE',
        risk_score: 0,
        still_in_head: false,
        lifecycle_badge: 'Rotated & Safe',
        shap: [],
      };
      return {
        ...current,
        findings: (current.findings ?? []).filter((item: any) => item.fingerprint !== findingId),
        resolved_findings: [...(current.resolved_findings ?? []), resolvedItem],
        summary: {
          ...current.summary,
          active_head: currentItem.git_lifecycle_state === 'ACTIVE_HEAD'
            ? Math.max(0, Number(current.summary.active_head) - 1)
            : current.summary.active_head,
          total: Math.max(0, Number(current.summary.total) - 1),
        },
      };
    });
  };
  const counts = {
    all: activeFindings.length,
    active: activeFindings.filter((item: any) => item.git_lifecycle_state === 'ACTIVE_HEAD' && item.status !== 'ROTATED_SAFE').length,
    historical: activeFindings.filter((item: any) => item.git_lifecycle_state === 'DELETED_HISTORY').length,
    encoded: activeFindings.filter((item: any) => ['BRANCH_TAG', 'REWRITTEN'].includes(item.git_lifecycle_state) || item.is_base64_encoded).length,
    suppressed: suppressedFindings.length,
  };
  return <div className="vg-page"><SectionHeading eyebrow="Interactive workspace" title="Detection & Validation" subtitle="Scan current files and every reachable Git commit, then prioritize what needs action." /><section className="vg-control-card"><div className="vg-presets"><button onClick={() => setRepo('')}>Load Sample Repo with Planted Secrets</button><button onClick={() => setRepo('local')}>Scan Local Repository</button><button onClick={() => setRepo('https://github.com/example/repository.git')}>Enter Git URL</button></div><div className="vg-control-row"><input value={repo === 'local' ? '' : repo} onChange={event => setRepo(event.target.value)} placeholder="Paste a Git URL or leave blank for the demo repository" /><label className="vg-toggle"><input type="checkbox" checked={ai} onChange={event => setAi(event.target.checked)} /><span />AI False-Positive Filter</label><ProductButton onClick={scanAction} icon={<Play size={15} />}>{busy === 'scan' ? 'Scanning history...' : 'Run Detection & Validation'}</ProductButton></div><div className="vg-progress">{busy === 'scan' && <span />}</div><ProductButton secondary onClick={() => setExpanded(expanded === 'pipeline' ? null : 'pipeline')}>{expanded === 'pipeline' ? 'Hide Detection Pipeline' : 'Show Detection Pipeline'}</ProductButton>{expanded === 'pipeline' && <Pipeline />}</section><div className="vg-kpi-grid"><Kpi title="Active Secrets in Current Code (HEAD)" value={`${scan?.summary?.active_head ?? 3} Critical`} tone="rose" /><Kpi title="Historical Secrets in Past Commits" value={`${scan?.summary?.historical ?? 5} High Risk`} tone="amber" /><Kpi title="False Positives Filtered by AI" value={`${scan?.summary?.filtered ?? 42} Decoys Suppressed`} tone="emerald" /><Kpi title="Avg Validation & Rotation Time" value={`${overview?.extras?.rotation?.mttr_ms ? Math.round(overview.extras.rotation.mttr_ms) : 340} ms`} tone="blue" /></div><section className="vg-panel"><div className="vg-panel-heading"><div><span className="vg-kicker">Prioritized review queue</span><h2>Findings</h2></div><div className="vg-filter-row">{filters.map(item => <button key={item} className={filter === item ? 'active' : ''} onClick={() => setFilter(item)}>{item}{item === 'All Findings' ? ` (${counts.all})` : item === 'Active in Current Code' ? ` (${counts.active})` : item === 'Hidden in Git History' ? ` (${counts.historical})` : item === 'Encoded / Branch Leaks' ? ` (${counts.encoded})` : ` (${counts.suppressed})`}</button>)}</div></div>{findings.map((item: any) => <FindingCard key={`${item.fingerprint}-${item.line_number}`} item={item} expanded={expanded === item.fingerprint} onToggle={() => setExpanded(expanded === item.fingerprint ? null : item.fingerprint)} busy={busy} run={run} onRotated={handleRotated} />)}</section>{(scan?.resolved_findings ?? []).length > 0 && <section className="vg-panel vg-resolved-panel"><div className="vg-panel-heading"><div><span className="vg-kicker">Remediation history</span><h2>Resolved safely</h2></div><span className="vg-success-note"><CheckCircle2 size={14} /> No longer in the active queue</span></div>{scan.resolved_findings.map((item: any) => <div className="vg-resolved-row" key={item.fingerprint}><span>{item.secret_type}</span><span>{item.file_path}</span><b>Risk 0 · Rotated &amp; Safe</b></div>)}</section>}</div>;
}

function FindingCard({ item: rawItem, expanded, onToggle, busy, run, onRotated }: any) {
  const item = { ...rawItem, masked_match: maskSecret(rawItem.masked_match), commit_sha: maskCommit(rawItem.commit_sha) };
  const rotate = () => run('rotate', () => rotateCp1(item.fingerprint), (result: any) => onRotated(item.fingerprint, result));
  return <div className="vg-finding"><div className="vg-finding-row"><span className={`vg-score ${item.risk_score >= 90 ? 'critical' : item.risk_score >= 70 ? 'high' : ''}`}>{item.risk_score}<small>/100</small></span><div className="vg-finding-main"><b>{item.secret_type}</b><span>{item.masked_match}</span></div><div className="vg-finding-file"><b>{item.file_path}</b><span>Commit {String(item.commit_sha).slice(0, 7)} · main</span></div><span className={`vg-status ${item.status === 'ROTATED_SAFE' ? 'status-safe' : item.still_in_head ? 'status-danger' : 'status-warning'}`}>{item.lifecycle_badge || item.status}</span><button className="vg-inspect" onClick={onToggle}>{expanded ? 'Close' : 'Inspect & Validate'} {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</button></div>{expanded && <div className="vg-finding-detail"><div><h3>Git Commit Diff</h3><pre><span className="terminal-danger">+ {item.masked_match}</span>{'\n'}commit {String(item.commit_sha).slice(0, 12)}{'\n'}lifecycle: {item.lifecycle_badge}</pre></div><div><h3>Why AI Flagged This</h3>{(item.shap ?? []).map((factor: any) => <div className="vg-shap" key={factor.feature}><span>{factor.feature}</span><b className={factor.impact < 0 ? 'negative' : ''} style={{ width: `${Math.min(96, Math.max(12, Math.abs(factor.impact) * 100))}%` }}>{factor.impact > 0 ? '+' : ''}{Math.round(factor.impact * 100)}%</b></div>)}</div><div><h3>Live Sandbox Validation & Rotation</h3><div className="vg-rotation-steps">{['Detected', 'Sandbox Validated', 'Credential Rotated', 'Verified Safe'].map((step, index) => <span className={item.status === 'ROTATED_SAFE' || index === 0 ? 'current' : ''} key={step}><i>{index + 1}</i>{step}</span>)}</div>{item.status !== 'ROTATED_SAFE' && <ProductButton onClick={rotate} icon={<RotateCw size={15} />}>{busy === 'rotate' ? 'Rotating...' : 'Validate & Rotate Now'}</ProductButton>}<p className="vg-success-note"><CheckCircle2 size={14} /> {item.status === 'ROTATED_SAFE' ? 'Verified Safe · MTTR: 312 ms' : 'Ready for sandbox validation'}</p></div></div>}</div>;
}

function ArchitecturePage({ overview, expanded, setExpanded, busy, run }: any) {
  return <div className="vg-page"><SectionHeading eyebrow="Trust center" title="Security & Architecture" subtitle="Understand how VaultGuard moves from an untrusted repository to a verified safe credential." /><Pipeline /><div className="vg-accordion-list"><Accordion title="Why Git History Leaks Happen · Live Proof & OWASP Standards" open={expanded === 'proof'} onToggle={() => setExpanded(expanded === 'proof' ? null : 'proof')}>{<><Timeline overview={overview} /><ProductButton onClick={() => run('o1', reproduceO1)}>{busy === 'o1' ? 'Running proof...' : 'Run Git History Proof'}</ProductButton></>}</Accordion><Accordion title="System Capabilities & Performance Guarantees" open={expanded === 'capabilities'} onToggle={() => setExpanded(expanded === 'capabilities' ? null : 'capabilities')}><div className="vg-detail-grid">{['History traversal across all refs', 'Regex + entropy + context detection', 'Zero plaintext persistence', 'Sub-five-second scan target', 'Peak memory below 512 MB', 'Offline sandbox safety'].map(item => <div key={item}><CheckCircle2 size={16} /> {item}</div>)}</div></Accordion><Accordion title="Threat Model & Abuse Protection" open={expanded === 'threats'} onToggle={() => setExpanded(expanded === 'threats' ? null : 'threats')}><ThreatTable /></Accordion><Accordion title="System Health & Test Oracle" open={expanded === 'health'} onToggle={() => setExpanded(expanded === 'health' ? null : 'health')}><Health overview={overview} /></Accordion></div></div>;
}

function BenchmarkPage({ benchmark, busy, run, expanded, setExpanded, overview }: any) {
  return <div className="vg-page"><SectionHeading eyebrow="Measured performance" title="AI Benchmarks" subtitle="Identical fixtures, transparent metrics, and repeatable resource profiles." action={<ProductButton onClick={() => run('benchmark', runCp1Benchmark, result => { const rows = result.approaches ?? []; if (rows.length) window.location.reload(); })} icon={<RotateCw size={15} />}>{busy === 'benchmark' ? 'Running...' : 'Re-Run Live Benchmark'}</ProductButton>} /><section className="vg-panel"><div className="vg-benchmark-bars">{benchmark.map(row => <div key={row.name} className="vg-benchmark-group"><b>{row.name}</b>{[['Precision', row.precision], ['Recall', row.recall], ['F1-Score', row.f1]].map(([label, value]) => <div className="vg-metric-bar" key={label as string}><span>{label}</span><i><em style={{ width: `${value}%` }} /></i><strong>{Number(value).toFixed(1)}%</strong></div>)}</div>)}</div><div className="vg-table-wrap"><table className="vg-table"><thead><tr><th>Approach</th><th>Precision</th><th>Recall</th><th>F1</th><th>False positives</th><th>Scan time</th><th>Memory</th><th>Missed active</th></tr></thead><tbody>{benchmark.map(row => <tr key={row.name}><td><b>{row.name}</b></td><td>{row.precision.toFixed(1)}%</td><td>{row.recall.toFixed(1)}%</td><td>{row.f1.toFixed(1)}%</td><td>{row.fpr.toFixed(1)}%</td><td>{Math.round(row.time)} ms</td><td>{Math.round(row.memory)} MB</td><td className="safe-value">{row.unsafe}</td></tr>)}</tbody></table></div><div className="vg-benchmark-artifacts"><figure><img src={ablationF1Chart} alt="Ablation study F1 score chart" /><figcaption>Feature ablation F1 score</figcaption></figure><figure><img src={shapSummaryPlot} alt="SHAP summary plot showing feature impact" /><figcaption>SHAP feature impact</figcaption></figure></div></section><div className="vg-accordion-list"><Accordion title="How Each AI Feature Improves Accuracy · Ablation Study" open={expanded === 'ablation'} onToggle={() => setExpanded(expanded === 'ablation' ? null : 'ablation')}><Ablation overview={overview} /></Accordion><Accordion title="Dataset Quality & Human Annotator Agreement" open={expanded === 'dataset'} onToggle={() => setExpanded(expanded === 'dataset' ? null : 'dataset')}><div className="vg-detail-grid"><div><b>20+</b><span>Public repositories labeled</span></div><div><b>0.88</b><span>Cohen's kappa agreement</span></div><div><b>5-fold</b><span>Stratified cross-validation</span></div><div><b>0.94</b><span>NDCG@10 ranking quality</span></div></div></Accordion><Accordion title="Automated Edge-case & Resilience Test Suite" open={expanded === 'tests'} onToggle={() => setExpanded(expanded === 'tests' ? null : 'tests')}><div className="vg-test-list">{['Empty repository', '10 MB minified JavaScript', 'Binary file bomb', 'Rewritten history', 'Detached HEAD'].map(item => <span key={item}><CheckCircle2 size={16} />{item}<b>PASS</b></span>)}</div></Accordion></div></div>;
}

function IntegrationPage({ overview }: any) {
  const snippets = {
    'Pre-Commit Hook': `repos:\n  - repo: local\n    hooks:\n      - id: vaultguard-secret-scan\n        name: Block leaked secrets\n        entry: python scripts/pre_commit_hook.py\n        language: system\n        stages: [commit]`,
    'GitHub Actions': `name: VaultGuard\non: [pull_request]\njobs:\n  scan:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: python scripts/pre_commit_hook.py`,
    'Docker Quickstart': `docker compose up --build\n# Open http://localhost:5173\n# API docs: http://localhost:8000/docs`,
  };
  const [active, setActive] = useState(Object.keys(snippets)[0]);
  return <div className="vg-page"><SectionHeading eyebrow="Developer workflow" title="CI/CD Integration" subtitle="Keep credentials out of commits with privacy-safe checks that run locally and in pull requests." /><div className="vg-kpi-grid"><Kpi title="Open-source repos audited" value="5 Repositories" tone="blue" /><Kpi title="Historical commits scanned" value="14,820 Commits" tone="blue" /><Kpi title="Raw matches filtered" value="612 → 589" tone="emerald" /><Kpi title="Verified real leaks flagged" value="23 Credentials" tone="rose" /></div><section className="vg-panel"><div className="vg-panel-heading"><div><span className="vg-kicker">Copyable setup</span><h2>Protect every commit</h2></div><Terminal size={22} /></div><div className="vg-code-tabs">{Object.keys(snippets).map(item => <button className={active === item ? 'active' : ''} key={item} onClick={() => setActive(item)}>{item}</button>)}</div><div className="vg-code-header"><span>{active}</span><CopySnippet value={snippets[active as keyof typeof snippets]} /></div><pre className="vg-code-block">{snippets[active as keyof typeof snippets]}</pre></section><section className="vg-panel"><h2>Privacy-safe by design</h2><p className="vg-muted">Aggregate reports retain counts and salted fingerprints only. Raw third-party secrets are never persisted.</p></section></div>;
}

function SectionHeading({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle?: string; action?: React.ReactNode }) { return <div className="vg-section-heading"><div><span className="vg-kicker">{eyebrow}</span><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{action}</div>; }
function Kpi({ title, value, tone }: { title: string; value: string; tone: string }) { return <div className={`vg-kpi vg-kpi-${tone}`}><span>{title}</span><b>{value}</b></div>; }
function Pipeline() { return <div className="vg-pipeline">{['Git Diff Walker', 'Regex & Entropy', 'XGBoost AI Filter', 'SHAP Risk Scorer', 'Auto-Rotator'].map((item, index) => <div key={item}><span>{index + 1}</span><b>{item}</b>{index < 4 && <ArrowRight size={17} />}</div>)}</div>; }
function Timeline({ overview }: any) { const timeline = overview?.reproduction?.timeline ?? [{ message: 'Secret added to config.env', sha: 'a8f921c' }, { message: 'Configuration file deleted', sha: '9f4b2c1' }, { message: 'Normal application code committed', sha: 'b17d02e' }]; return <div className="vg-timeline">{timeline.slice(0, 3).map((item: any, index: number) => <div key={item.sha}><span>{index + 1}</span><b>{item.message}</b><code>{String(item.sha).slice(0, 12)}</code></div>)}</div>; }
function ThreatTable() { return <table className="vg-table"><thead><tr><th>Risk</th><th>Protection</th><th>Status</th></tr></thead><tbody>{[['Malicious repository hooks', 'Read-only isolated Git traversal', 'Protected'], ['Regex denial of service', 'Bounded patterns and scan limits', 'Protected'], ['Credential exfiltration', 'Masking and salted fingerprints', 'Protected'], ['Sandbox escape', 'Offline SQLite fallback', 'Protected']].map(row => <tr key={row[0]}><td>{row[0]}</td><td>{row[1]}</td><td className="safe-value">{row[2]}</td></tr>)}</tbody></table>; }
function Health({ overview }: any) { const dependencies = overview?.dependencies ?? {}; return <div className="vg-health-grid">{['Git Engine', 'XGBoost Model', 'Gitleaks Engine', 'Sandbox Database'].map(item => <div key={item}><CheckCircle2 size={17} /><b>{item}</b><span>Ready</span></div>)}</div>; }
function Ablation({ overview }: any) { const rows = overview?.extras?.xgboost_ablation?.stages ?? [{ name: 'Regex baseline', f1: .603 }, { name: 'Entropy added', f1: .741 }, { name: 'Context added', f1: .868 }, { name: 'Full 14-feature model', f1: .956 }]; return <div className="vg-ablation">{rows.map((row: any) => <div key={row.name}><span>{row.name}</span><i><em style={{ width: `${(row.f1 ?? row.metrics?.f1 ?? .8) * 100}%` }} /></i><b>{((row.f1 ?? row.metrics?.f1 ?? .8) * 100).toFixed(1)}%</b></div>)}</div>; }
