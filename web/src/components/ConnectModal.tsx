import React, { useState, useEffect } from 'react';
import { X, Network, ArrowRight, ShieldCheck } from 'lucide-react';
import type { MeshNode } from '../types';

interface ConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  sourceNode: MeshNode | null;
  targetNode: MeshNode | null;
  allNodes: MeshNode[];
  onConfirmConnect: (tunnelId: string, network: string, comment: string) => Promise<void>;
}

export const ConnectModal: React.FC<ConnectModalProps> = ({
  isOpen,
  onClose,
  sourceNode,
  targetNode,
  allNodes,
  onConfirmConnect,
}) => {
  const [selectedTunnelId, setSelectedTunnelId] = useState('');
  const [networkCidr, setNetworkCidr] = useState('');
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (sourceNode) {
      setSelectedTunnelId(sourceNode.id);
    } else if (allNodes.length > 0) {
      setSelectedTunnelId(allNodes[0].id);
    }

    if (targetNode) {
      setNetworkCidr(targetNode.lan_cidr);
      setComment(`Route to ${targetNode.name}`);
    } else {
      setNetworkCidr('');
      setComment('');
    }
  }, [sourceNode, targetNode, allNodes]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTunnelId || !networkCidr.trim()) {
      setError('Please provide both the source gateway tunnel and target subnet CIDR.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onConfirmConnect(selectedTunnelId, networkCidr.trim(), comment.trim());
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to establish route');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedNodeObj = allNodes.find((n) => n.id === selectedTunnelId);

  return (
    <div className="modal-backdrop">
      <div className="modal-content glass-panel" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{ background: 'var(--cyan-glow)', padding: '0.45rem', borderRadius: 'var(--radius-md)' }}>
              <Network size={20} color="var(--cyan)" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Establish Zero Trust Mesh Route</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                Create encrypted overlay route between site gateways via Cloudflare Virtual Networks.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Visual Route Flow Indicator */}
        <div style={{
          background: 'var(--bg-base)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-around',
          marginBottom: '1.25rem'
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Source Site</div>
            <div style={{ fontWeight: 700, color: 'var(--cyan)', marginTop: '0.15rem' }}>
              {selectedNodeObj?.name || 'Select Gateway'}
            </div>
            <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {selectedNodeObj?.lan_cidr || '0.0.0.0/0'}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--cf-orange)' }}>
            <span>─────</span>
            <ArrowRight size={18} />
          </div>

          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Target Subnet</div>
            <div style={{ fontWeight: 700, color: 'var(--emerald)', marginTop: '0.15rem' }}>
              {targetNode?.name || 'Remote Subnet'}
            </div>
            <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--emerald)', fontWeight: 700 }}>
              {networkCidr || 'CIDR Subnet'}
            </div>
          </div>
        </div>

        {error && (
          <div style={{ background: 'rgba(255, 51, 102, 0.15)', border: '1px solid var(--rose)', padding: '0.75rem', borderRadius: 'var(--radius-md)', color: 'var(--rose)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
              Source Gateway Tunnel
            </label>
            <select
              className="input-field"
              value={selectedTunnelId}
              onChange={(e) => setSelectedTunnelId(e.target.value)}
              required
            >
              {allNodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name} — {n.lan_cidr} ({n.wan_ip})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
              Target Subnet CIDR (Network IP Range to Route)
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="e.g. 192.168.20.0/24"
              value={networkCidr}
              onChange={(e) => setNetworkCidr(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
              Route Note / Description
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="e.g. Encrypted Link to Branch Office"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              <ShieldCheck size={16} />
              <span>{isSubmitting ? 'Establishing Route...' : 'Create Mesh Link'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
