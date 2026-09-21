import { CheckCircle2, CircleDashed, Clock3, Cloud, Github, Gitlab } from 'lucide-react';

export default function SettingsPage() {
  const providerStatus = [
    { name: 'GitHub', status: 'connected', icon: Github },
    { name: 'GitLab', status: 'not connected', icon: Gitlab },
    { name: 'Azure DevOps', status: 'connected', icon: Cloud },
  ];

  return (
    <div className="page-shell settings-shell">
      <section className="panel-card settings-card">
        <div className="panel-header panel-header--simple">
          <h2>Provider status</h2>
        </div>

        <div className="settings-list">
          {providerStatus.map(({ name, status, icon: Icon }) => (
            <div key={name} className="settings-row">
              <div className="provider-meta">
                <div className="provider-icon-wrap">
                  <Icon size={16} />
                </div>
                <span>{name}</span>
              </div>

              <span className={`status-indicator ${status === 'connected' ? 'connected' : 'offline'}`}>
                {status === 'connected' ? <CheckCircle2 size={12} /> : <CircleDashed size={12} />}
                {status === 'connected' ? 'Connected' : 'Not connected'}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel-card settings-card">
        <div className="panel-header panel-header--simple">
          <h2>Re-check interval</h2>
        </div>

        <div className="settings-config">
          <div className="settings-config__label">
            <Clock3 size={16} />
            <span>Interval</span>
          </div>

          <select className="interval-select" defaultValue="8h">
            <option value="6h">6 hours</option>
            <option value="8h">8 hours</option>
            <option value="10h">10 hours</option>
            <option value="12h">12 hours</option>
          </select>
        </div>
      </section>
    </div>
  );
}
