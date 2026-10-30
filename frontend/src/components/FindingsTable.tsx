import { Link } from 'react-router-dom';
import type { Finding } from '../types';
import { maskSecret } from '../utils/displaySafety';

export default function FindingsTable({
  findings,
}: {
  findings: Finding[];
}) {
  const rows = findings.slice(0, 8);

  return (
    <div className="worklist-table-wrap overflow-x-auto">
      <table className="worklist-table">
        <thead>
          <tr>
            <th>Secret type</th>
            <th>Repository</th>
            <th>Last checked</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((finding) => (
            <tr key={finding.id}>
              <td className="secret-cell">
                <Link to={`/findings/${finding.id}`} className="secret-link">
                  <span className="secret-name">{finding.secret_type}</span>
                  <span className="secret-meta">{maskSecret(finding.masked_hash || finding.masked_preview)} · {finding.file_path}</span>
                </Link>
              </td>
              <td className="repo-cell">{finding.repository}</td>
              <td className="time-cell">{finding.last_checked}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
