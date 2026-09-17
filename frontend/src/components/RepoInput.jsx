import { FolderGit2, LoaderCircle, ScanSearch } from "lucide-react";
import { useState } from "react";

export default function RepoInput({ onScan, loading, result }) {
  const [repoPath, setRepoPath] = useState("");
  const [repoId, setRepoId] = useState("local-repo");
  const [analysisMode, setAnalysisMode] = useState("full");

  function submit(event) {
    event.preventDefault();
    if (repoPath.trim() && repoId.trim()) onScan({ repoPath: repoPath.trim(), repoId: repoId.trim(), analysisMode });
  }

  return (
    <section className="scan-panel">
      <div className="panel-kicker"><FolderGit2 size={15} /> REPOSITORY SCAN</div>
      <h1>Trace every file that ever existed.</h1>
      <p className="lede">Choose current-source analysis, Git history analysis, or both. Results come from the repository ledger, never placeholder data.</p>
      <form className="scan-form" onSubmit={submit}>
        <label>
          <span>Repository path or URL</span>
          <input value={repoPath} onChange={(event) => setRepoPath(event.target.value)} placeholder="D:\\projects\\service or https://..." />
        </label>
        <label>
          <span>Repository ID</span>
          <input value={repoId} onChange={(event) => setRepoId(event.target.value)} placeholder="payments-service" />
        </label>
        <fieldset className="analysis-mode">
          <legend>Analysis mode</legend>
          <label><input type="radio" checked={analysisMode === "current"} onChange={() => setAnalysisMode("current")} /> Current source</label>
          <label><input type="radio" checked={analysisMode === "history"} onChange={() => setAnalysisMode("history")} /> Git history</label>
          <label><input type="radio" checked={analysisMode === "full"} onChange={() => setAnalysisMode("full")} /> Full analysis</label>
        </fieldset>
        <button className="primary-button" disabled={loading || !repoPath.trim() || !repoId.trim()}>
          {loading ? <LoaderCircle className="spin" size={17} /> : <ScanSearch size={17} />}
          {loading ? "Analyzing" : "Run analysis"}
        </button>
      </form>
      {result && <p className="scan-result">Indexed {result.blobs} history blobs and detected {result.findings} current-source findings.</p>}
    </section>
  );
}
