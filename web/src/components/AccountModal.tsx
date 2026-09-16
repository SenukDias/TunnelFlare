import React, { useState } from 'react';
import { 
  Key, 
  ShieldCheck, 
  Terminal, 
  Copy, 
  Check, 
  LogOut, 
  Cpu, 
  CheckCircle2 
} from 'lucide-react';
import type { NodeStatus } from '../types';


interface AccountModalProps {
  nodeStatus: NodeStatus | null;
  onSaveToken: (token: string, accountId?: string, siteName?: string) => Promise<void>;
  onLogout: () => Promise<void>;
  onToggleIpForwarding: (enable: boolean) => Promise<void>;
}

export const AccountModal: React.FC<AccountModalProps> = ({
  nodeStatus,
  onSaveToken,
  onLogout,
  onToggleIpForwarding,
}) => {
  const [token, setToken] = useState('');
  const [siteName, setSiteName] = useState(nodeStatus?.site_name || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) {
      setError('Please provide a valid Cloudflare Zero Trust API Token.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onSaveToken(token.trim(), undefined, siteName.trim());
      setToken('');
    } catch (err: any) {
      setError(err?.message || 'Failed to link account');
    } finally {
      setIsSubmitting(false);
    }
  };

  const enrollmentCommand = `curl -sSL https://raw.githubusercontent.com/ronin/tunnelflare/main/install.sh | bash -s -- --join-mesh --site "${siteName || 'Branch-Site'}"`;

  const copyEnrollment = () => {
    navigator.clipboard.writeText(enrollmentCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '850px', margin: '0 auto' }}>
      {/* Account Authentication Card */}
      <div className="glass-panel" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{ background: 'var(--cf-orange-glow)', padding: '0.45rem', borderRadius: 'var(--radius-md)' }}>
              <Key size={20} color="var(--cf-orange)" />
            </div>
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Cloudflare Zero Trust Credentials</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                Connect your Cloudflare account to discover, mesh, and manage multi-site private networks.
              </p>
            </div>
          </div>

          {nodeStatus?.account_linked && (
            <button className="btn btn-danger" onClick={onLogout} style={{ fontSize: '0.8rem' }}>
              <LogOut size={14} />
              <span>Disconnect</span>
            </button>
          )}
        </div>

        {nodeStatus?.account_linked ? (
          <div style={{ background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1.25rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Linked Account Name</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fff', marginTop: '0.2rem' }}>
                {nodeStatus.account_name}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Account ID</div>
              <div className="mono" style={{ fontSize: '0.85rem', color: 'var(--cyan)', marginTop: '0.2rem' }}>
                {nodeStatus.account_id}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Token Status</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '0.2rem', color: 'var(--emerald)', fontWeight: 600, fontSize: '0.85rem' }}>
                <CheckCircle2 size={15} />
                <span>ACTIVE & VERIFIED</span>
              </div>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {error && (
              <div style={{ background: 'rgba(255, 51, 102, 0.15)', border: '1px solid var(--rose)', padding: '0.75rem', borderRadius: 'var(--radius-md)', color: 'var(--rose)', fontSize: '0.85rem' }}>
                {error}
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Local Site Identifier / Name
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. Headquarters-Gateway"
                value={siteName}
                onChange={(e) => setSiteName(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Cloudflare API Token (Requires <code>Account.Cloudflare Tunnel:Edit</code>, <code>Account.Zero Trust:Read</code>)
              </label>
              <input
                type="password"
                className="input-field"
                placeholder="Paste your Cloudflare API token here..."
                value={token}
                onChange={(e) => setToken(e.target.value)}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting}
              style={{ alignSelf: 'flex-start' }}
            >
              <ShieldCheck size={16} />
              <span>{isSubmitting ? 'Verifying with Cloudflare...' : 'Verify & Link Cloudflare Mesh'}</span>
            </button>
          </form>
        )}
      </div>

      {/* Linux Gateway Packet Forwarding Card */}
      <div className="glass-panel" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{ background: 'var(--cyan-glow)', padding: '0.45rem', borderRadius: 'var(--radius-md)' }}>
              <Cpu size={20} color="var(--cyan)" />
            </div>
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Linux Kernel IP Packet Forwarding</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                Required when this machine acts as a site router forwarding traffic to other hosts in its local LAN.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ 
                width: '10px', 
                height: '10px', 
                borderRadius: '50%', 
                background: nodeStatus?.ip_forwarding ? 'var(--emerald)' : 'var(--amber)' 
              }} />
              <span className="mono" style={{ fontWeight: 700, color: nodeStatus?.ip_forwarding ? 'var(--emerald)' : 'var(--amber)' }}>
                {nodeStatus?.ip_forwarding ? 'ENABLED (1)' : 'DISABLED (0)'}
              </span>
            </div>

            {!nodeStatus?.ip_forwarding && (
              <button
                className="btn btn-cyan"
                onClick={() => onToggleIpForwarding(true)}
                style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
              >
                Enable Packet Forwarding
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Multi-Site Enrollment Command Generator */}
      <div className="glass-panel" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.85rem' }}>
          <div style={{ background: 'var(--purple-glow)', padding: '0.45rem', borderRadius: 'var(--radius-md)' }}>
            <Terminal size={20} color="var(--purple)" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Enroll Remote Branch Office</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              Run this single command on any remote client machine to automatically install TunnelFlare and join this mesh.
            </p>
          </div>
        </div>

        <div style={{ 
          background: 'var(--bg-base)', 
          border: '1px solid var(--border-subtle)', 
          borderRadius: 'var(--radius-md)', 
          padding: '0.75rem 1rem', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          gap: '1rem'
        }}>
          <code className="mono" style={{ color: 'var(--cyan)', fontSize: '0.82rem', overflowX: 'auto', whiteSpace: 'nowrap' }}>
            {enrollmentCommand}
          </code>
          <button 
            className="btn btn-secondary" 
            onClick={copyEnrollment} 
            style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem', flexShrink: 0 }}
          >
            {copied ? <Check size={14} color="var(--emerald)" /> : <Copy size={14} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
