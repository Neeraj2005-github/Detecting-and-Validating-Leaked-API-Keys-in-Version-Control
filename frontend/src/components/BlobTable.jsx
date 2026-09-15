import { ChevronDown, ChevronRight, FileCode2 } from "lucide-react";
import { useState } from "react";
import DeletedFileBadge from "./DeletedFileBadge";

function shortHash(value) {
  return value?.slice(0, 8) ?? "--------";
}

export default function BlobTable({ blobs, selectedHash }) {
  const [expandedId, setExpandedId] = useState(null);
  return (
    <section className="blob-panel">
      <div className="section-heading">
        <div><span className="panel-kicker"><FileCode2 size={15} /> CONTENT INDEX</span><h2>{selectedHash ? `Blobs in ${shortHash(selectedHash)}` : "Select a commit"}</h2></div>
        <span className="count-label">{blobs.length} files</span>
      </div>
      {blobs.length === 0 ? <div className="empty-state"><FileCode2 size={31} /><p>Select a commit to inspect its files.</p><span>Historical content appears here, including files removed from HEAD.</span></div> : (
        <div className="blob-table-wrap"><table><thead><tr><th>File path</th><th>Commit</th><th>Status</th><th aria-label="Expand" /></tr></thead><tbody>
          {blobs.map((blob) => {
            const expanded = expandedId === blob.id;
            return <tr key={blob.id} className={expanded ? "is-expanded" : ""}>
              <td><button className="file-name" onClick={() => setExpandedId(expanded ? null : blob.id)}>{expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}<span>{blob.file_path}</span></button>{expanded && <pre className="blob-preview">{blob.blob_content || "[empty file]"}</pre>}</td>
              <td><code>{shortHash(blob.commit_hash)}</code></td>
              <td><DeletedFileBadge isHead={blob.is_head} /></td>
              <td />
            </tr>;
          })}
        </tbody></table></div>
      )}
    </section>
  );
}
