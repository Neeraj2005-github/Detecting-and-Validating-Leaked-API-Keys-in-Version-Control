import { GitCommitHorizontal, SlidersHorizontal } from "lucide-react";

function shortHash(value) {
  return value?.slice(0, 8) ?? "--------";
}

export default function CommitTimeline({ commits, selectedHash, onSelect, deletedHashes, deletedOnly, onFilterChange }) {
  const visibleCommits = deletedOnly ? commits.filter((commit) => deletedHashes.has(commit.commit_hash)) : commits;

  return (
    <section className="timeline-panel">
      <div className="section-heading">
        <div><span className="panel-kicker"><GitCommitHorizontal size={15} /> HISTORY</span><h2>Commit timeline</h2></div>
        <span className="count-label">{visibleCommits.length} commits</span>
      </div>
      <div className="filter-tabs" role="tablist" aria-label="Commit filter">
        <button className={!deletedOnly ? "is-active" : ""} onClick={() => onFilterChange(false)}><SlidersHorizontal size={14} /> All commits</button>
        <button className={deletedOnly ? "is-active is-danger" : ""} onClick={() => onFilterChange(true)}>Deleted files</button>
      </div>
      <div className="timeline-list">
        {visibleCommits.length === 0 ? <p className="empty-note">No commits match this filter.</p> : visibleCommits.map((commit) => (
          <button key={commit.commit_hash} className={`commit-card ${selectedHash === commit.commit_hash ? "is-selected" : ""}`} onClick={() => onSelect(commit)}>
            <span className="commit-dot" />
            <span className="commit-copy"><strong>{shortHash(commit.commit_hash)}</strong><small>{new Date(commit.commit_timestamp).toLocaleString()}</small></span>
            {deletedHashes.has(commit.commit_hash) && <span className="commit-alert">!</span>}
          </button>
        ))}
      </div>
    </section>
  );
}
