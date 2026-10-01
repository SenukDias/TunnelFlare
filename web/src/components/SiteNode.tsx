import React from 'react';
import { Handle, Position } from '@xyflow/react';
import {
  Building2, Server, Cloud, Network,
  Copy, Check, Globe, Cpu,
} from 'lucide-react';
import type { MeshNode } from '../types';

interface SiteNodeProps {
  data: {
    node: MeshNode;
    onContextMenu?: (e: React.MouseEvent, nodeId: string) => void;
  };
  selected?: boolean;
}

const getRoleIcon = (node: MeshNode) => {
  if (node.is_local) return { Icon: Building2, color: '#2dd4bf', bg: 'rgba(45,212,191,0.1)' };
  if (node.name.toLowerCase().includes('cloud') || node.name.toLowerCase().includes('vpc'))
    return { Icon: Cloud, color: '#a78bfa', bg: 'rgba(167,139,250,0.1)' };
  return { Icon: Server, color: '#f97316', bg: 'rgba(249,115,22,0.1)' };
};

const getStatusStyle = (status: string) => {
  if (status === 'healthy')  return { dotClass: 'status-dot--healthy',  label: 'Healthy',  badgeClass: 'badge-success' };
  if (status === 'warning')  return { dotClass: 'status-dot--warning',  label: 'Degraded', badgeClass: 'badge-warning' };
  return { dotClass: 'status-dot--offline', label: 'Offline',  badgeClass: 'badge-error' };
};

const HANDLE_POSITIONS = [
  { type: 'target' as const, pos: Position.Top,    id: 'top' },
  { type: 'source' as const, pos: Position.Right,  id: 'right' },
  { type: 'target' as const, pos: Position.Bottom, id: 'bottom' },
  { type: 'source' as const, pos: Position.Left,   id: 'left' },
];

export const SiteNode: React.FC<SiteNodeProps> = ({ data, selected }) => {
  const { node } = data;
  const [copied, setCopied] = React.useState(false);
  const { Icon, color, bg } = getRoleIcon(node);
  const { dotClass, label, badgeClass } = getStatusStyle(node.status);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const borderColor = selected
    ? color
    : node.is_local
    ? `${color}50`
    : 'var(--border-1)';

  return (
    <div
      onContextMenu={(e) => {
        e.preventDefault();
        data.onContextMenu?.(e, node.id);
      }}
      style={{
        width: 260,
        background: 'var(--bg-surface)',
        border: `1px solid ${borderColor}`,
        borderRadius: 'var(--radius-lg)',
        overflow: 'hidden',
        userSelect: 'none',
        boxShadow: selected
          ? `0 0 0 1px ${color}30, var(--shadow-md)`
          : 'var(--shadow-sm)',
        transition: 'border-color 0.15s, box-shadow 0.15s',
      }}
    >
      {/* Connection handles — all 4 sides */}
      {HANDLE_POSITIONS.map(({ type, pos, id }) => (
        <Handle
          key={id}
          type={type}
          position={pos}
          id={id}
          style={{ zIndex: 10 }}
        />
      ))}
      {/* Source handles on same sides as targets (for bidirectional) */}
      <Handle type="source" position={Position.Top}    id="top-src"    style={{ opacity: 0, pointerEvents: 'none' }} />
      <Handle type="source" position={Position.Bottom} id="bottom-src" style={{ opacity: 0, pointerEvents: 'none' }} />
      <Handle type="target" position={Position.Right}  id="right-tgt"  style={{ opacity: 0, pointerEvents: 'none' }} />
      <Handle type="target" position={Position.Left}   id="left-tgt"   style={{ opacity: 0, pointerEvents: 'none' }} />

      {/* ── Card Header ─────────────────────────── */}
      <div style={{ padding: '12px 12px 10px', display: 'flex', alignItems: 'center', gap: 10 }}>
        {/* Icon box */}
        <div
          className="node-icon-box"
          style={{ background: bg, borderColor: `${color}25` }}
        >
          <Icon size={16} color={color} strokeWidth={1.8} />
        </div>

        {/* Name + location */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {node.name.replace(/^[^\w]+ /, '')}
            </span>
            {node.is_local && (
              <span className="badge badge-info" style={{ fontSize: 9, padding: '1px 5px', lineHeight: 1.4 }}>
                LOCAL
              </span>
            )}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 1 }}>
            {node.city || 'Zero Trust Node'}{node.country ? `, ${node.country}` : ''}
          </div>
        </div>

        {/* Status badge */}
        <div className={`badge ${badgeClass}`} style={{ flexShrink: 0, padding: '2px 7px' }}>
          <span className={`status-dot ${dotClass}`} style={{ width: 5, height: 5 }} />
          <span style={{ fontSize: 10 }}>{label}</span>
        </div>
      </div>

      {/* ── Divider ──────────────────────────────── */}
      <div className="divider" />

      {/* ── Data Rows ────────────────────────────── */}
      <div style={{ padding: '6px 12px 8px' }}>
        {/* Subnet CIDR — primary value */}
        <div
          style={{
            background: 'var(--bg-surface-2)',
            border: '1px solid var(--border-1)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 8,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Network size={11} color="var(--state-success)" strokeWidth={2} />
            <div>
              <div style={{ fontSize: 9, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Subnet</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--state-success)' }}>
                {node.lan_cidr}
              </div>
            </div>
          </div>
          <button
            onClick={() => copyToClipboard(node.lan_cidr)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: 'var(--text-3)', display: 'flex' }}
            title="Copy"
          >
            {copied ? <Check size={11} color="var(--state-success)" /> : <Copy size={11} />}
          </button>
        </div>

        {/* Two-column detail grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          {/* WAN IP */}
          <div style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-1)', borderRadius: 'var(--radius-sm)', padding: '5px 8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
              <Globe size={9} color="var(--text-3)" />
              <span style={{ fontSize: 9, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>WAN IP</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, fontWeight: 500, color: 'var(--text-1)' }}>
              {node.wan_ip}
            </div>
          </div>

          {/* PoP / Region */}
          <div style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-1)', borderRadius: 'var(--radius-sm)', padding: '5px 8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
              <Cpu size={9} color="var(--text-3)" />
              <span style={{ fontSize: 9, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>PoP</span>
            </div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#f97316' }}>
              {node.colo || 'SIN'}
            </div>
          </div>
        </div>
      </div>

      {/* ── Footer ───────────────────────────────── */}
      <div
        style={{
          padding: '6px 12px',
          borderTop: '1px solid var(--border-1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-surface-2)',
        }}
      >
        <span style={{ fontSize: 10, color: 'var(--text-3)' }}>
          {node.routes?.length ?? 0} routes
        </span>
        <span style={{ fontSize: 10, color: 'var(--text-3)', fontStyle: 'italic' }}>
          Drag handle to connect →
        </span>
      </div>
    </div>
  );
};
