import React, { useState, useId } from 'react';
import { X, Zap, Server, Cloud, Building2 } from 'lucide-react';
import type { MeshNode } from '../types';

interface ConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  sourceNode: MeshNode | null;
  targetNode: MeshNode | null;
  allNodes: MeshNode[];
  onConfirmConnect: (tunnelId: string, network: string, comment: string) => Promise<void>;
}

// Tiny animated bezier preview line component
const PreviewLine: React.FC<{ status?: 'ok' | 'error' }> = ({ status = 'ok' }) => {
  const color = status === 'ok' ? '#2dd4bf' : '#ef4444';
  const pathId = useId();
  return (
    <svg width="80" height="40" viewBox="0 0 80 40" style={{ overflow: 'visible' }}>
      <defs>
        <path id={pathId} d="M 0 20 C 30 20 50 20 80 20" />
      </defs>
      {/* Track */}
      <path d="M 0 20 C 30 20 50 20 80 20" fill="none" stroke="var(--border-1)" strokeWidth="1.5" />
      {/* Animated stroke */}
      <path
        d="M 0 20 C 30 20 50 20 80 20"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeDasharray="8 4"
        strokeOpacity="0.7"
        style={{ animation: 'flow-particle 1.5s linear infinite' }}
      />
      {/* Traveling dot */}
      <circle r="3" fill={color}>
        <animateMotion dur="1.8s" repeatCount="indefinite" calcMode="spline" keySplines="0.4 0 0.6 1">
          <mpath href={`#${pathId}`} />
        </animateMotion>
      </circle>
    </svg>
  );
};

const NodeMiniCard: React.FC<{ node: MeshNode }> = ({ node }) => {
  const isLocal = node.is_local;
  const isCloud = node.name.toLowerCase().includes('cloud') || node.name.toLowerCase().includes('vpc');
  const Icon = isLocal ? Building2 : isCloud ? Cloud : Server;
  const color = isLocal ? '#2dd4bf' : isCloud ? '#a78bfa' : '#f97316';

  return (
    <div
      style={{
        background: 'var(--bg-surface-2)',
        border: `1px solid ${color}30`,
        borderRadius: 10,
        padding: '10px 14px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 6,
        minWidth: 90,
      }}
    >
      <div
        style={{
          width: 32, height: 32,
          borderRadius: 8,
          background: `${color}15`,
          border: `1px solid ${color}25`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
      >
        <Icon size={16} color={color} strokeWidth={1.8} />
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', whiteSpace: 'nowrap' }}>
          {node.name.replace(/^[^\w]+ /, '').split(' ').slice(0, 2).join(' ')}
        </div>
        <div style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-3)', marginTop: 1 }}>
          {node.colo || 'PoP'}
        </div>
      </div>
    </div>
  );
};

export const ConnectModal: React.FC<ConnectModalProps> = ({
  isOpen,
  onClose,
  sourceNode,
  targetNode,
  allNodes,
  onConfirmConnect,
}) => {
  const [selectedTarget, setSelectedTarget] = useState<string>(targetNode?.id ?? '');
  const [network, setNetwork] = useState('');
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    if (targetNode) setSelectedTarget(targetNode.id);
    if (targetNode?.lan_cidr) setNetwork(targetNode.lan_cidr);
  }, [targetNode]);

  if (!isOpen || !sourceNode) return null;

  const resolvedTarget = allNodes.find((n) => n.id === selectedTarget) ?? null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTarget || !network.trim()) return;
    setError(null);
    setLoading(true);
    try {
      await onConfirmConnect(selectedTarget, network.trim(), comment.trim());
      onClose();
    } catch (err: any) {
      setError(err.message ?? 'Failed to establish route');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 460 }}>
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-1)' }}>Establish Zero Trust Route</div>
            <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>
              Connect two sites via a private tunnel
            </div>
          </div>
          <button className="btn btn-ghost btn-icon" onClick={onClose}>
            <X size={14} />
          </button>
        </div>

        {/* Preview diagram */}
        <div
          style={{
            margin: '16px 20px 0',
            background: 'var(--bg-surface-2)',
            border: '1px solid var(--border-1)',
            borderRadius: 10,
            padding: '14px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
          }}
        >
          <NodeMiniCard node={sourceNode} />
          <PreviewLine status={error ? 'error' : 'ok'} />
          {resolvedTarget ? (
            <NodeMiniCard node={resolvedTarget} />
          ) : (
            <div
              style={{
                minWidth: 90, height: 72,
                background: 'var(--bg-surface)',
                border: '1px dashed var(--border-1)',
                borderRadius: 10,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10, color: 'var(--text-4)',
              }}
            >
              Select target
            </div>
          )}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: '16px 20px 20px' }}>
          {/* Target site selector */}
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-3)', marginBottom: 5 }}>
              Target Site
            </label>
            <select
              value={selectedTarget}
              onChange={(e) => {
                setSelectedTarget(e.target.value);
                const n = allNodes.find((x) => x.id === e.target.value);
                if (n) setNetwork(n.lan_cidr);
              }}
              className="input"
              style={{ fontFamily: 'var(--font-sans)' }}
              required
            >
              <option value="">— Select a site —</option>
              {allNodes
                .filter((n) => n.id !== sourceNode.id)
                .map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.name.replace(/^[^\w]+ /, '')} — {n.lan_cidr}
                  </option>
                ))}
            </select>
          </div>

          {/* Network CIDR */}
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-3)', marginBottom: 5 }}>
              Network CIDR
            </label>
            <input
              className="input input-mono"
              placeholder="e.g. 10.200.0.0/16"
              value={network}
              onChange={(e) => setNetwork(e.target.value)}
              required
              style={{ color: 'var(--state-success)' }}
            />
          </div>

          {/* Comment */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-3)', marginBottom: 5 }}>
              Comment <span style={{ color: 'var(--text-4)' }}>(optional)</span>
            </label>
            <input
              className="input"
              placeholder="e.g. Singapore Production VPC"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>

          {/* Error */}
          {error && (
            <div
              style={{
                marginBottom: 12,
                padding: '8px 12px',
                background: 'var(--state-error-dim)',
                border: '1px solid var(--state-error-border)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 12,
                color: 'var(--state-error)',
              }}
            >
              {error}
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="btn btn-danger" onClick={onClose} style={{ flex: 1 }}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !selectedTarget || !network}
              style={{ flex: 2 }}
            >
              {loading ? (
                <>
                  <span style={{ display: 'inline-block', animation: 'spin-slow 1s linear infinite' }}>⟳</span>
                  Establishing...
                </>
              ) : (
                <>
                  <Zap size={13} />
                  Confirm Route
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
