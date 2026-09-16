import React, { useState } from 'react';
import { Route, Trash2, Plus, Shield, Network } from 'lucide-react';

import type { MeshRoute, MeshNode } from '../types';


interface RouteManagerProps {
  routes: MeshRoute[];
  nodes: MeshNode[];
  onAddRoute: (network: string, tunnelId: string, comment: string) => Promise<void>;
  onDeleteRoute: (routeId: string) => Promise<void>;
}

export const RouteManager: React.FC<RouteManagerProps> = ({
  routes,
  nodes,
  onAddRoute,
  onDeleteRoute,
}) => {
  const [network, setNetwork] = useState('');
  const [tunnelId, setTunnelId] = useState(nodes[0]?.id || '');
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!network.trim() || !tunnelId) {
      setError('Please provide both a subnet CIDR and target tunnel gateway.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onAddRoute(network.trim(), tunnelId, comment.trim());
      setNetwork('');
      setComment('');
    } catch (err: any) {
      setError(err?.message || 'Failed to add route');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Route Creation Form */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <Shield size={20} color="var(--cyan)" />
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Add Zero Trust CIDR Route</h2>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
          Direct IP traffic targeting this private network range to route through a Cloudflare Tunnel gateway.
        </p>

        {error && (
          <div style={{ background: 'rgba(255, 51, 102, 0.15)', border: '1px solid var(--rose)', padding: '0.75rem', borderRadius: 'var(--radius-md)', color: 'var(--rose)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', alignItems: 'end' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
              Subnet CIDR Network (e.g. 192.168.20.0/24)
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="192.168.20.0/24"
              value={network}
              onChange={(e) => setNetwork(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
              Target Gateway Tunnel
            </label>
            <select
              className="input-field"
              value={tunnelId}
              onChange={(e) => setTunnelId(e.target.value)}
              style={{ height: '40px' }}
            >
              {nodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.name} ({node.lan_cidr})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
              Route Comment / Note
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="Site B Branch Office"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSubmitting}
            style={{ height: '40px' }}
          >
            <Plus size={16} />
            <span>{isSubmitting ? 'Registering...' : 'Register Route'}</span>
          </button>
        </form>
      </div>

      {/* Routes Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Route size={20} color="var(--emerald)" />
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Active Mesh Routes ({routes.length})</h2>
          </div>
        </div>

        {routes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-dim)' }}>
            <Network size={36} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
            <p>No active CIDR routes configured yet.</p>
            <p style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>Register a private subnet above or link nodes in the topology canvas.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-dim)' }}>
                  <th style={{ padding: '0.75rem' }}>Subnet CIDR</th>
                  <th style={{ padding: '0.75rem' }}>Target Gateway</th>
                  <th style={{ padding: '0.75rem' }}>Comment</th>
                  <th style={{ padding: '0.75rem' }}>Status</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {routes.map((route) => {
                  const matchedNode = nodes.find((n) => n.id === route.tunnel_id);
                  return (
                    <tr
                      key={route.id}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        transition: 'background 0.2s',
                      }}
                    >
                      <td style={{ padding: '0.75rem' }}>
                        <span className="mono" style={{ color: 'var(--emerald)', fontWeight: 700, fontSize: '0.9rem' }}>
                          {route.network}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <span style={{ fontWeight: 600 }}>{matchedNode?.name || 'Tunnel'}</span>
                          <span className="mono" style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>
                            ({route.tunnel_id.slice(0, 8)}...)
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>
                        {route.comment || 'TunnelFlare Route'}
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        <span className="badge badge-emerald">
                          ● ACTIVE
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                        <button
                          className="btn btn-danger"
                          onClick={() => onDeleteRoute(route.id)}
                          style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                          title="Revoke Route"
                        >
                          <Trash2 size={13} />
                          <span>Revoke</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
