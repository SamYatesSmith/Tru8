'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import {
  Key,
  Copy,
  Check,
  Trash2,
  Plus,
  Loader2,
  AlertCircle,
  Shield,
} from 'lucide-react';
import { apiClient } from '@/lib/api';

interface APIKeyItem {
  id: string;
  key_prefix: string;
  name: string;
  is_active: boolean;
  last_used_at: string | null;
  usage_count: number;
  created_at: string;
}

export function DeveloperTab() {
  const { getToken } = useAuth();
  const [keys, setKeys] = useState<APIKeyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [creating, setCreating] = useState(false);

  // Newly created key (shown once)
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Revoke state
  const [revoking, setRevoking] = useState<string | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null);

  // Load keys on mount
  useEffect(() => {
    const fetchKeys = async () => {
      try {
        setLoading(true);
        setError(null);
        const token = await getToken();
        const data = await apiClient.listAPIKeys(token);
        setKeys(data.keys);
      } catch (err: any) {
        console.error('Failed to fetch API keys:', err);
        setError(err?.message || 'Failed to load API keys.');
      } finally {
        setLoading(false);
      }
    };
    fetchKeys();
  }, [getToken]);

  const handleCreate = async () => {
    if (!newKeyName.trim()) return;
    try {
      setCreating(true);
      setError(null);
      const token = await getToken();
      const result = await apiClient.createAPIKey({ name: newKeyName.trim() }, token);
      setCreatedKey(result.key);
      setCopied(false);
      setNewKeyName('');
      setShowCreate(false);
      // Refresh list
      const data = await apiClient.listAPIKeys(token);
      setKeys(data.keys);
    } catch (err: any) {
      setError(err?.message || 'Failed to create API key.');
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (keyId: string) => {
    try {
      setRevoking(keyId);
      setError(null);
      const token = await getToken();
      await apiClient.revokeAPIKey(keyId, token);
      setConfirmRevoke(null);
      // Refresh list
      const data = await apiClient.listAPIKeys(token);
      setKeys(data.keys);
    } catch (err: any) {
      setError(err?.message || 'Failed to revoke API key.');
    } finally {
      setRevoking(null);
    }
  };

  const handleCopy = async () => {
    if (!createdKey) return;
    try {
      await navigator.clipboard.writeText(createdKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = createdKey;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  const activeKeys = keys.filter((k) => k.is_active);
  const revokedKeys = keys.filter((k) => !k.is_active);

  if (loading) {
    return (
      <div className="space-y-8">
        <section className="bg-white border border-zinc-200 p-6">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-zinc-400 animate-spin" />
            <span className="ml-3 text-zinc-400">Loading API keys...</span>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Error banner */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <p className="text-xs text-red-600">{error}</p>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-xs text-red-400 hover:text-red-600"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Newly created key — shown once */}
      {createdKey && (
        <section className="bg-amber-50 border border-amber-300 p-6">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-bold text-amber-900">
                Save your API key now
              </h4>
              <p className="text-xs text-amber-700 mt-1">
                This key will not be shown again. Copy it and store it securely.
              </p>
              <div className="mt-3 flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-white border border-amber-200 text-xs font-mono text-zinc-900 truncate select-all">
                  {createdKey}
                </code>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 px-3 py-2 bg-zinc-900 text-white text-xs font-medium hover:bg-zinc-800 transition-colors"
                >
                  {copied ? (
                    <>
                      <Check size={14} />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy size={14} />
                      Copy
                    </>
                  )}
                </button>
              </div>
            </div>
            <button
              onClick={() => setCreatedKey(null)}
              className="text-xs text-amber-500 hover:text-amber-700"
            >
              Dismiss
            </button>
          </div>
        </section>
      )}

      {/* API Keys section */}
      <section className="bg-white border border-zinc-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
            <Key size={20} />
            API Keys
          </h3>
          <button
            onClick={() => setShowCreate(!showCreate)}
            disabled={activeKeys.length >= 5}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors ${
              activeKeys.length >= 5
                ? 'bg-zinc-100 text-zinc-400 cursor-not-allowed'
                : 'bg-zinc-900 text-white hover:bg-zinc-800'
            }`}
          >
            <Plus size={14} />
            New Key
          </button>
        </div>

        {/* Create form */}
        {showCreate && (
          <div className="mb-6 p-4 border border-zinc-200 bg-zinc-50">
            <label className="block font-mono text-[10px] tracking-widest uppercase text-zinc-400 mb-2">
              Key Name
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                placeholder="e.g. Production Agent, Dev Testing"
                maxLength={100}
                className="flex-1 px-3 py-2 bg-white border border-zinc-200 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:border-zinc-900"
              />
              <button
                onClick={handleCreate}
                disabled={creating || !newKeyName.trim()}
                className="flex items-center gap-1.5 px-4 py-2 bg-zinc-900 text-white text-xs font-medium hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {creating ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Plus size={14} />
                )}
                Create
              </button>
              <button
                onClick={() => {
                  setShowCreate(false);
                  setNewKeyName('');
                }}
                className="px-3 py-2 border border-zinc-200 text-xs text-zinc-600 hover:bg-zinc-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Active keys */}
        {activeKeys.length === 0 && !showCreate ? (
          <div className="text-center py-8">
            <Key className="w-8 h-8 text-zinc-300 mx-auto mb-3" />
            <p className="text-sm text-zinc-500">No API keys yet</p>
            <p className="text-xs text-zinc-400 mt-1">
              Create a key to authenticate API requests from your agents
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeKeys.map((key) => (
              <div
                key={key.id}
                className="flex items-center justify-between p-3 border border-zinc-100 hover:border-zinc-200 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-zinc-900">
                      {key.name}
                    </span>
                    <code className="text-xs font-mono text-zinc-400">
                      {key.key_prefix}...
                    </code>
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-zinc-400">
                      Created {formatDate(key.created_at)}
                    </span>
                    {key.last_used_at && (
                      <span className="text-xs text-zinc-400">
                        Last used {formatDate(key.last_used_at)}
                      </span>
                    )}
                    {key.usage_count > 0 && (
                      <span className="text-xs text-zinc-400">
                        {key.usage_count.toLocaleString()} request{key.usage_count !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </div>

                {/* Revoke */}
                {confirmRevoke === key.id ? (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-red-600">Revoke?</span>
                    <button
                      onClick={() => handleRevoke(key.id)}
                      disabled={revoking === key.id}
                      className="px-2 py-1 text-xs bg-red-500 text-white hover:bg-red-600 disabled:opacity-50 transition-colors"
                    >
                      {revoking === key.id ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        'Yes'
                      )}
                    </button>
                    <button
                      onClick={() => setConfirmRevoke(null)}
                      className="px-2 py-1 text-xs border border-zinc-200 text-zinc-600 hover:bg-zinc-50 transition-colors"
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmRevoke(key.id)}
                    className="flex items-center gap-1 px-2 py-1 text-xs text-zinc-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={14} />
                    Revoke
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Key limit indicator */}
        <div className="mt-4 pt-4 border-t border-zinc-100">
          <p className="text-xs text-zinc-400">
            {activeKeys.length}/5 active keys
          </p>
        </div>

        {/* Revoked keys (collapsed) */}
        {revokedKeys.length > 0 && (
          <details className="mt-4">
            <summary className="text-xs text-zinc-400 cursor-pointer hover:text-zinc-600">
              {revokedKeys.length} revoked key{revokedKeys.length !== 1 ? 's' : ''}
            </summary>
            <div className="mt-2 space-y-2">
              {revokedKeys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center justify-between p-3 border border-zinc-100 opacity-50"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-zinc-500 line-through">
                        {key.name}
                      </span>
                      <code className="text-xs font-mono text-zinc-400">
                        {key.key_prefix}...
                      </code>
                    </div>
                    <span className="text-xs text-zinc-400">
                      Created {formatDate(key.created_at)}
                      {key.usage_count > 0 &&
                        ` · ${key.usage_count.toLocaleString()} requests`}
                    </span>
                  </div>
                  <span className="text-xs text-red-400 font-mono">REVOKED</span>
                </div>
              ))}
            </div>
          </details>
        )}
      </section>

      {/* Quick reference */}
      <section className="bg-zinc-50 border border-zinc-200 p-6">
        <h3 className="text-sm font-bold text-zinc-900 mb-3">Quick Reference</h3>
        <p className="text-xs text-zinc-600 mb-3">
          Include your API key in the <code className="px-1 py-0.5 bg-white border border-zinc-200 text-zinc-700 font-mono text-[11px]">X-API-Key</code> header:
        </p>
        <pre className="bg-white border border-zinc-200 p-4 overflow-x-auto text-xs font-mono text-zinc-700 leading-relaxed">
{`curl -H "X-API-Key: tru8_sk_..." \\
     https://api.trueight.com/api/v1/checks`}
        </pre>
        <div className="mt-3 flex items-center gap-4">
          <a
            href="/api/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-zinc-500 hover:text-zinc-900 underline underline-offset-2"
          >
            API Documentation
          </a>
          <a
            href="/api/redoc"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-zinc-500 hover:text-zinc-900 underline underline-offset-2"
          >
            API Reference
          </a>
        </div>
      </section>
    </div>
  );
}
