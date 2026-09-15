import axios from "axios";
import { AlertTriangle, Database, Eye, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import CommitTimeline from "./components/CommitTimeline";
import BlobTable from "./components/BlobTable";
import RepoInput from "./components/RepoInput";

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

  async function scanRepository({ repoPath, repoId }) {
    setLoading(true); setError(""); setScanResult(null);
    try {
      const scan = await axios.post(`${API_URL}/scan`, { repo_path: repoPath, repo_id: repoId });
      const [commitResponse, deletedResponse] = await Promise.all([
        axios.get(`${API_URL}/repos/${encodeURIComponent(repoId)}/commits`),
        axios.get(`${API_URL}/repos/${encodeURIComponent(repoId)}/deleted-blobs`),
      ]);
      setRepo({ repoPath, repoId }); setScanResult(scan.data.blobs_written);
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
    } catch { setError("Could not load blobs for this commit."); }
  }

  useEffect(() => {
    document.title = repo ? `${repo.repoId} | Secret History Detector` : "Secret History Detector";
  }, [repo]);

  const deletedHashes = new Set(deletedBlobs.map((blob) => blob.commit_hash));
  return <main className="app-shell">
    <header className="topbar"><div className="brand"><span className="brand-mark"><ShieldCheck size={19} /></span><span>SHD<span className="brand-muted"> / SECRET HISTORY DETECTOR</span></span></div><div className="connection"><span className="connection-dot" /> MYSQL LEDGER <span className="api-label">API :8000</span></div></header>
    <RepoInput onScan={scanRepository} loading={loading} result={scanResult} />
    {error && <div className="error-banner"><AlertTriangle size={17} /> {error}</div>}
    {repo ? <>
      <section className="repo-strip"><div><span className="panel-kicker">ACTIVE REPOSITORY</span><strong>{repo.repoId}</strong><code>{repo.repoPath}</code></div><div className="repo-metrics"><span><Database size={16} /> {commits.length} commits</span><span><Eye size={16} /> {deletedBlobs.length} deleted records</span></div></section>
      <div className="workspace-grid"><CommitTimeline commits={commits} selectedHash={selectedCommit?.commit_hash} onSelect={selectCommit} deletedHashes={deletedHashes} deletedOnly={deletedOnly} onFilterChange={setDeletedOnly} /><BlobTable blobs={blobs} selectedHash={selectedCommit?.commit_hash} /></div>
    </> : <section className="welcome-band"><div className="welcome-icon"><ShieldCheck size={25} /></div><div><span className="panel-kicker">HISTORY LEDGER READY</span><h2>Start with a repository path.</h2><p>Every commit becomes a searchable record. Deleted files stay visible long after they disappear from the working tree.</p></div></section>}
    <footer>SECRET HISTORY DETECTOR <span>LOCAL ANALYSIS WORKBENCH</span></footer>
  </main>;
}
