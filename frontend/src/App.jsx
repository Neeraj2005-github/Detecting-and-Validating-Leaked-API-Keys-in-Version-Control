import axios from "axios";
import { AlertTriangle, Database, Eye, Gauge, GitCommitHorizontal, ListChecks, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import CommitTimeline from "./components/CommitTimeline";
import BlobTable from "./components/BlobTable";
import RepoInput from "./components/RepoInput";
import { CommitDetailsPanel, DashboardPanel, DataListPanel, FindingsPanel, ScanHistoryPanel } from "./components/WorkbenchPanels";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [repo, setRepo] = useState(null);
  const [commits, setCommits] = useState([]);
  const [deletedBlobs, setDeletedBlobs] = useState([]);
  const [blobs, setBlobs] = useState([]);
  const [selectedCommit, setSelectedCommit] = useState(null);
  const [deletedOnly, setDeletedOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [scanResult, setScanResult] = useState(null);
  const [findings, setFindings] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [repositories, setRepositories] = useState([]);
  const [scanHistory, setScanHistory] = useState([]);
  const [commitDetails, setCommitDetails] = useState(null);
  const [activeView, setActiveView] = useState("dashboard");

  async function scanRepository({ repoPath, repoId, analysisMode }) {
    setLoading(true); setError(""); setScanResult(null);
    try {
      const scan = await axios.post(`${API_URL}/scan`, { repo_path: repoPath, repo_id: repoId, analysis_mode: analysisMode });
      const [commitResponse, deletedResponse] = await Promise.all([
        axios.get(`${API_URL}/repos/${encodeURIComponent(repoId)}/commits`),
        axios.get(`${API_URL}/repos/${encodeURIComponent(repoId)}/deleted-blobs`),
      ]);
      const [findingResponse, metricResponse, repositoryResponse, scanHistoryResponse] = await Promise.all([
        axios.get(`${API_URL}/findings?repo_id=${encodeURIComponent(repoId)}`),
        axios.get(`${API_URL}/metrics`),
        axios.get(`${API_URL}/repositories`),
        axios.get(`${API_URL}/scans`),
      ]);
      setRepo({ repoPath, repoId, analysisMode }); setScanResult({ blobs: scan.data.blobs_written, findings: scan.data.findings_count });
      setFindings(findingResponse.data);
      setMetrics(metricResponse.data); setRepositories(repositoryResponse.data); setScanHistory(scanHistoryResponse.data);
      setCommits(commitResponse.data); setDeletedBlobs(deletedResponse.data); setBlobs([]); setSelectedCommit(null);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "The API could not scan this repository.");
    } finally { setLoading(false); }
  }

  async function selectCommit(commit) {
    setSelectedCommit(commit); setError("");
    try {
      const response = await axios.get(`${API_URL}/repos/${encodeURIComponent(repo.repoId)}/commits/${commit.commit_hash}/blobs`);
      setBlobs(response.data);
      const details = await axios.get(`${API_URL}/repos/${encodeURIComponent(repo.repoId)}/commits/${commit.commit_hash}`);
      setCommitDetails(details.data);
    } catch { setError("Could not load blobs for this commit."); }
  }

  useEffect(() => {
    document.title = repo ? `${repo.repoId} | Secret History Detector` : "Secret History Detector";
  }, [repo]);

  const deletedHashes = new Set(deletedBlobs.map((blob) => blob.commit_hash));
  const navItems = [
    ["dashboard", "Dashboard", Gauge], ["scan", "Repository Scan", ShieldCheck], ["history", "Git History", GitCommitHorizontal],
    ["findings", "Findings", AlertTriangle], ["repositories", "Repositories", Database], ["scans", "Scan History", ListChecks],
  ];
  return <main className="app-shell">
    <header className="topbar"><div className="brand"><span className="brand-mark"><ShieldCheck size={19} /></span><span>SHD<span className="brand-muted"> / SECRET HISTORY DETECTOR</span></span></div><div className="connection"><span className="connection-dot" /> LOCAL LEDGER <span className="api-label">API :8000</span></div></header>
    <nav className="workbench-nav" aria-label="Workbench sections">{navItems.map(([id, label, Icon]) => <button key={id} className={activeView === id ? "is-active" : ""} onClick={() => setActiveView(id)}><Icon size={15} />{label}</button>)}</nav>
    {(activeView === "scan" || !repo) && <RepoInput onScan={scanRepository} loading={loading} result={scanResult} />}
    {error && <div className="error-banner"><AlertTriangle size={17} /> {error}</div>}
    {repo && <>
      <section className="repo-strip"><div><span className="panel-kicker">ACTIVE REPOSITORY · {repo.analysisMode.toUpperCase()}</span><strong>{repo.repoId}</strong><code>{repo.repoPath}</code></div><div className="repo-metrics"><span><Database size={16} /> {commits.length} commits</span><span><Eye size={16} /> {deletedBlobs.length} deleted records</span><span><AlertTriangle size={16} /> {findings.length} findings</span></div></section>
      {(activeView === "dashboard" || activeView === "scan") && <DashboardPanel metrics={metrics} scanHistory={scanHistory} />}
      {(activeView === "dashboard" || activeView === "history") && <><div className="workspace-grid"><CommitTimeline commits={commits} selectedHash={selectedCommit?.commit_hash} onSelect={selectCommit} deletedHashes={deletedHashes} deletedOnly={deletedOnly} onFilterChange={setDeletedOnly} /><BlobTable blobs={blobs} selectedHash={selectedCommit?.commit_hash} /></div>{commitDetails && <CommitDetailsPanel details={commitDetails} deleted={deletedHashes.has(commitDetails.commit_hash)} />}</>}
      {(activeView === "dashboard" || activeView === "findings") && <FindingsPanel findings={findings} />}
      {activeView === "repositories" && <DataListPanel title="Repositories" items={repositories.map((item) => `${item.repository_id} · ${item.path}`)} empty="No repositories have been scanned." />}
      {activeView === "scans" && <ScanHistoryPanel scans={scanHistory} />}
    </>}
    {!repo && <section className="welcome-band"><div className="welcome-icon"><ShieldCheck size={25} /></div><div><span className="panel-kicker">HISTORY LEDGER READY</span><h2>Start with a repository path.</h2><p>Choose an analysis mode above. Git history and current-source results are shown separately.</p></div></section>}
    <footer>SECRET HISTORY DETECTOR <span>LOCAL ANALYSIS WORKBENCH</span></footer>
  </main>;
}
