import { FolderGit2, LoaderCircle, ScanSearch } from "lucide-react";
import { useState } from "react";

export default function RepoInput({ onScan, loading, result }) {
  const [repoPath, setRepoPath] = useState("");
  const [repoId, setRepoId] = useState("local-repo");

  function submit(event) {
    event.preventDefault();
    if (repoPath.trim() && repoId.trim()) onScan({ repoPath: repoPath.trim(), repoId: repoId.trim() });
  }

  return (
    <section className="scan-panel">
      <div className="panel-kicker"><FolderGit2 size={15} /> REPOSITORY SCAN</div>
      <h1>Trace every file that ever existed.</h1>
      <p className="lede">Walk a local or remote Git history, preserve deleted blobs, and inspect what survived in the archive.</p>
      <form className="scan-form" onSubmit={submit}>
        <label>
          <span>Repository path or URL</span>
          <input value={repoPath} onChange={(event) => setRepoPath(event.target.value)} placeholder="D:\\projects\\service or https://..." />
        </label>
        <label>
          <span>Repository ID</span>
          <input value={repoId} onChange={(event) => setRepoId(event.target.value)} placeholder="payments-service" />
        </label>
        <button className="primary-button" disabled={loading || !repoPath.trim() || !repoId.trim()}>
          {loading ? <LoaderCircle className="spin" size={17} /> : <ScanSearch size={17} />}
          {loading ? "Scanning" : "Scan history"}
        </button>
      </form>
      {result && <p className="scan-result">Indexed {result} blobs into the history ledger.</p>}
    </section>
  );
}
