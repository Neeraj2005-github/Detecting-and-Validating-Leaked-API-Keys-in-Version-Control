import { useEffect, useRef, useState } from 'react';
import { Check, FolderGit2, LoaderCircle, Pencil, Plus, RefreshCcw, Trash2, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import * as AlertDialog from '@radix-ui/react-alert-dialog';
import { addRepository, deleteRepository, fetchRepositories, scanRepository, updateRepository } from '../api/repositories';
import EmptyState from '../components/EmptyState';
import LoadingSkeleton from '../components/LoadingSkeleton';
import type { Repository } from '../types';

type RepositoryScanState = {
  status: 'success' | 'error';
  message: string;
};

function getScanErrorMessage(error: unknown) {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail;
    if (detail) return detail;
  }
  return 'Check the repository path and backend logs.';
}

export default function RepositoriesPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [url, setUrl] = useState('');
  const [scanningId, setScanningId] = useState<string | null>(null);
  const [scanStates, setScanStates] = useState<Record<string, RepositoryScanState>>({});
  const [addedRepoId, setAddedRepoId] = useState<string | null>(null);
  const [addedRepoUrl, setAddedRepoUrl] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Repository | null>(null);
  const repositoryInputRef = useRef<HTMLInputElement>(null);

  async function load(): Promise<Repository[]> {
    setLoading(true);
    try {
      const data = await fetchRepositories();
      const nextRepos = Array.isArray(data) ? data : [];
      setRepos(nextRepos);
      return nextRepos;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!loading && repos.length === 0) {
      repositoryInputRef.current?.focus();
    }
  }, [loading, repos.length]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!url.trim()) return;
    const repositoryUrl = url.trim();
    const created = await addRepository(repositoryUrl);
    setUrl('');
    const loadedRepos = await load();
    const createdId = typeof created?.id === 'string' ? created.id : created?.repository?.id;
    const matchingRepo = loadedRepos.find((repo) => repo.url === repositoryUrl);
    setAddedRepoId(createdId ?? matchingRepo?.id ?? null);
    setAddedRepoUrl(repositoryUrl);
  }

  async function onScan(id: string) {
    setScanningId(id);
    try {
      const result = await scanRepository(id);
      await load();
      setScanStates((states) => ({
        ...states,
        [id]: { status: 'success', message: `Scan complete - ${result.finding_count} findings` },
      }));
      setStatusMessage('Repository scanned');
    } catch (error) {
      setScanStates((states) => ({
        ...states,
        [id]: { status: 'error', message: `Scan failed - ${getScanErrorMessage(error)}` },
      }));
    } finally {
      setScanningId(null);
    }
  }

  async function onSaveEdit(id: string) {
    const value = editingValue.trim();
    if (!value) return;
    try {
      await updateRepository(id, value);
      setEditingId(null);
      setEditingValue('');
      setStatusMessage('Repository updated');
      await load();
    } catch (error) {
      setScanStates((states) => ({
        ...states,
        [id]: { status: 'error', message: `Update failed - ${getScanErrorMessage(error)}` },
      }));
    }
  }

  async function onDeleteRepo(id: string) {
    try {
      await deleteRepository(id);
      setDeleteTarget(null);
      setStatusMessage('Repository deleted');
      await load();
    } catch (error) {
      setScanStates((states) => ({
        ...states,
        [id]: { status: 'error', message: `Delete failed - ${getScanErrorMessage(error)}` },
      }));
    }
  }

  return (
    <div className="page-shell">
      <AlertDialog.Root open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialog.Portal>
          <AlertDialog.Overlay className="alert-dialog-overlay" />
          <AlertDialog.Content className="alert-dialog-content">
            <AlertDialog.Title className="alert-dialog-title">Delete this repository?</AlertDialog.Title>
            <AlertDialog.Description className="alert-dialog-description">
              {`This will permanently remove ${deleteTarget?.finding_count ?? 0} findings associated with it. This can't be undone.`}
            </AlertDialog.Description>
            <div className="alert-dialog-actions">
              <AlertDialog.Cancel asChild>
                <button type="button" className="ghost-button ghost-button--small">Cancel</button>
              </AlertDialog.Cancel>
              <AlertDialog.Action asChild>
                <button type="button" className="primary-button primary-button--inline primary-button--danger" onClick={() => deleteTarget && onDeleteRepo(deleteTarget.id)}>
                  Delete repository
                </button>
              </AlertDialog.Action>
            </div>
          </AlertDialog.Content>
        </AlertDialog.Portal>
      </AlertDialog.Root>

      <section className="panel-card repositories-card">
        <div className="panel-header panel-header--tight">
          <div className="panel-heading-group">
            <div className="panel-icon-wrap">
              <FolderGit2 size={16} />
            </div>
            <h2>Repositories</h2>
          </div>

          <button className="ghost-button" onClick={load} type="button">
            <RefreshCcw size={14} />
            Refresh
          </button>
        </div>

        <form className="repository-form" onSubmit={onSubmit}>
          <input
            ref={repositoryInputRef}
            className={`repository-input ${!loading && repos.length === 0 ? 'repository-input--guided' : ''}`}
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://github.com/example/repo"
            autoFocus={!loading && repos.length === 0}
          />
          <button type="submit" className="primary-button primary-button--wide">
            <Plus size={14} /> Add Repository
          </button>
        </form>

        {addedRepoUrl && (
          <div className="scan-status scan-status--success" role="status">
            Repository added successfully.{' '}
            {addedRepoId ? (
              <button type="button" className="ghost-button ghost-button--small" onClick={() => onScan(addedRepoId)} disabled={scanningId !== null}>
                <RefreshCcw size={14} /> Scan now
              </button>
            ) : (
              <span>Refresh to scan it.</span>
            )}
          </div>
        )}

        {statusMessage && (
          <div className="scan-status scan-status--success" role="status">
            {statusMessage}
          </div>
        )}

        {loading ? (
          <LoadingSkeleton rows={4} />
        ) : repos.length === 0 ? (
          <EmptyState
            icon={<FolderGit2 size={18} />}
            title="Get started"
            description="Add a repository URL below to begin the O2 scan workflow."
            action={<ol className="onboarding-steps"><li>Add a repository below</li><li>Click Scan now</li><li>View results on the Dashboard</li></ol>}
          />
        ) : (
          <>
            <div className="repo-list">
              {repos.map((repo) => (
                <div key={repo.id} className="repo-list__item">
                  <div className="repo-list__body">
                    {editingId === repo.id ? (
                      <div className="repo-edit-row">
                        <input
                          className="repository-input"
                          value={editingValue}
                          onChange={(event) => setEditingValue(event.target.value)}
                          autoFocus
                        />
                        <div className="repo-edit-actions">
                          <button type="button" className="icon-action icon-action--edit" aria-label="Save repository URL" onClick={() => onSaveEdit(repo.id)}>
                            <Check size={14} />
                          </button>
                          <button type="button" className="icon-action icon-action--cancel" aria-label="Cancel editing" onClick={() => { setEditingId(null); setEditingValue(''); }}>
                            <X size={14} />
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="repo-list__name">{repo.url}</div>
                    )}
                    <div className="repo-list__meta">
                      <span>{repo.last_scan ? `Last scan: ${new Date(repo.last_scan).toLocaleString()}` : 'Last scan: Never scanned'}</span>
                      <a href={`/dashboard?repo=${encodeURIComponent(repo.url)}`} className="repo-findings-link">
                        Findings: {repo.finding_count ?? 0}
                      </a>
                    </div>
                  </div>
                  <div className="repo-list__action">
                    <div className="repo-list__toolbar">
                      <button
                        type="button"
                        className="ghost-button ghost-button--small"
                        onClick={() => onScan(repo.id)}
                        disabled={scanningId !== null}
                      >
                        {scanningId === repo.id ? <LoaderCircle size={14} className="spin" /> : <RefreshCcw size={14} />}
                        {scanningId === repo.id ? 'Scanning...' : 'Scan now'}
                      </button>
                      <button
                        type="button"
                        className="icon-action icon-action--edit"
                        aria-label="Edit repository"
                        onClick={() => {
                          setEditingId(repo.id);
                          setEditingValue(repo.url);
                        }}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        type="button"
                        className="icon-action icon-action--delete"
                        aria-label="Delete repository"
                        onClick={() => setDeleteTarget(repo)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                    {scanStates[repo.id] && (
                      <span className={`scan-status scan-status--${scanStates[repo.id].status}`} role={scanStates[repo.id].status === 'error' ? 'alert' : 'status'}>
                        {scanStates[repo.id].message}
                        {scanStates[repo.id].status === 'success' && (
                          <Link to={`/dashboard?repo=${encodeURIComponent(repo.url)}`} className="scan-status__link">View results -&gt;</Link>
                        )}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
