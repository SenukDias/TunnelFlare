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
    onAccessApp?: (node: MeshNode) => void;
  };
  selected?: boolean;
}

const getRoleIcon = (node: MeshNode) => {
  if (node.status === 'offline') {
    if (node.name.toLowerCase().includes('cloud') || node.name.toLowerCase().includes('vpc'))
      return { Icon: Cloud, color: '#71717a', bg: 'rgba(255, 255, 255, 0.03)' };
    if (node.is_local)
      return { Icon: Building2, color: '#71717a', bg: 'rgba(255, 255, 255, 0.03)' };
    return { Icon: Server, color: '#71717a', bg: 'rgba(255, 255, 255, 0.03)' };
  }
  if (node.is_local) return { Icon: Building2, color: '#2dd4bf', bg: 'rgba(45,212,191,0.1)' };
  if (node.name.toLowerCase().includes('cloud') || node.name.toLowerCase().includes('vpc'))
    return { Icon: Cloud, color: '#a78bfa', bg: 'rgba(167,139,250,0.1)' };
  return { Icon: Server, color: '#f97316', bg: 'rgba(249,115,22,0.1)' };
};

const getStatusStyle = (status: string) => {
  if (status === 'healthy')  return { dotClass: 'status-dot--healthy',  label: 'Healthy',  badgeClass: 'badge-success' };
  if (status === 'warning')  return { dotClass: 'status-dot--warning',  label: 'Degraded', badgeClass: 'badge-warning' };
  return { dotClass: 'status-dot--offline', label: 'Offline',  badgeClass: 'badge-neutral' };
};

const HANDLE_POSITIONS = [
  { type: 'target' as const, pos: Position.Top,    id: 'top' },
  { type: 'source' as const, pos: Position.Right,  id: 'right' },
  { type: 'target' as const, pos: Position.Bottom, id: 'bottom' },
  { type: 'source' as const, pos: Position.Left,   id: 'left' },
];

export const SiteNode: React.FC<SiteNodeProps> = ({ data, selected }) => {
  const { node } = data;
  const isOffline = node.status === 'offline';
  const [copied, setCopied] = React.useState(false);
  const { Icon, color, bg } = getRoleIcon(node);
  const { dotClass, label, badgeClass } = getStatusStyle(node.status);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const borderColor = selected
    ? (isOffline ? '#71717a' : color)
    : isOffline
    ? 'rgba(113, 113, 122, 0.35)'
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
        background: isOffline ? 'rgba(24, 24, 27, 0.7)' : 'var(--bg-surface)',
        border: `${isOffline ? '1px dashed' : '1px solid'} ${borderColor}`,
        borderRadius: 'var(--radius-lg)',
        overflow: 'hidden',
        userSelect: 'none',
        opacity: isOffline ? 0.72 : 1,
        boxShadow: selected
          ? `0 0 0 1px ${isOffline ? '#71717a30' : `${color}30`}, var(--shadow-md)`
          : 'var(--shadow-sm)',
        transition: 'border-color 0.15s, box-shadow 0.15s, opacity 0.2s',
      }}
    >
      {/* Connection handles — only active & interactive when node is online */}
      {!isOffline && (
        <>
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
        </>
      )}

      {/* ── Card Header ─────────────────────────── */}
      <div style={{ padding: '12px 12px 10px', display: 'flex', alignItems: 'center', gap: 10 }}>
        {/* Icon box */}
        <div
          className="node-icon-box"
          style={{
            background: isOffline ? 'rgba(255, 255, 255, 0.04)' : bg,
            borderColor: isOffline ? 'rgba(113, 113, 122, 0.25)' : `${color}25`,
          }}
        >
          <Icon size={16} color={isOffline ? '#71717a' : color} strokeWidth={1.8} />
        </div>

        {/* Name + location */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: isOffline ? '#a1a1aa' : 'var(--text-1)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {node.name.replace(/^[^\w]+ /, '')}
            </span>
            {node.is_local && (
              <span
                className={`badge ${isOffline ? 'badge-neutral' : 'badge-info'}`}
                style={{ fontSize: 9, padding: '1px 5px', lineHeight: 1.4 }}
              >
                LOCAL
              </span>
            )}
          </div>
          <div style={{ fontSize: 11, color: isOffline ? '#71717a' : 'var(--text-3)', marginTop: 1 }}>
            {node.city || 'Edge Node'}{node.country ? `, ${node.country}` : ''}
          </div>
        </div>

        {/* Status badge */}
        <div
          className={`badge ${badgeClass}`}
          style={{
            flexShrink: 0,
            padding: '2px 7px',
            background: isOffline ? 'rgba(113, 113, 122, 0.15)' : undefined,
            borderColor: isOffline ? 'rgba(113, 113, 122, 0.25)' : undefined,
            color: isOffline ? '#a1a1aa' : undefined,
          }}
        >
          <span
            className={`status-dot ${dotClass}`}
            style={{
              width: 5,
              height: 5,
              background: isOffline ? '#71717a' : undefined,
              boxShadow: isOffline ? 'none' : undefined,
            }}
          />
          <span style={{ fontSize: 10 }}>{label}</span>
        </div>
      </div>

      {/* ── Divider ──────────────────────────────── */}
      <div className="divider" style={{ opacity: isOffline ? 0.4 : 1 }} />

      {/* ── Data Rows ────────────────────────────── */}
      <div style={{ padding: '6px 12px 8px' }}>
        {/* Subnet CIDR — primary value */}
        <div
          style={{
            background: 'var(--bg-surface-2)',
            border: `1px solid ${isOffline ? 'rgba(113, 113, 122, 0.2)' : 'var(--border-1)'}`,
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 8,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Network size={11} color={isOffline ? '#71717a' : 'var(--state-success)'} strokeWidth={2} />
            <div>
              <div style={{ fontSize: 9, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Subnet</div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  fontWeight: 600,
                  color: isOffline ? '#a1a1aa' : 'var(--state-success)',
                }}
              >
                {node.lan_cidr}
              </div>
            </div>
          </div>
          <button
            onClick={() => copyToClipboard(node.lan_cidr)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 2,
              color: isOffline ? '#71717a' : 'var(--text-3)',
              display: 'flex',
            }}
            title="Copy"
          >
            {copied ? <Check size={11} color={isOffline ? '#a1a1aa' : 'var(--state-success)'} /> : <Copy size={11} />}
          </button>
        </div>

        {/* Two-column detail grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          {/* WAN IP */}
          <div
            style={{
              background: 'var(--bg-surface-2)',
              border: `1px solid ${isOffline ? 'rgba(113, 113, 122, 0.2)' : 'var(--border-1)'}`,
              borderRadius: 'var(--radius-sm)',
              padding: '5px 8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
              <Globe size={9} color={isOffline ? '#71717a' : 'var(--text-3)'} />
              <span style={{ fontSize: 9, color: isOffline ? '#71717a' : 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>WAN IP</span>
            </div>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 10.5,
                fontWeight: 500,
                color: isOffline ? '#71717a' : 'var(--text-1)',
              }}
            >
              {node.wan_ip || '—'}
            </div>
          </div>

          {/* PoP / Region */}
          <div
            style={{
              background: 'var(--bg-surface-2)',
              border: `1px solid ${isOffline ? 'rgba(113, 113, 122, 0.2)' : 'var(--border-1)'}`,
              borderRadius: 'var(--radius-sm)',
              padding: '5px 8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
              <Cpu size={9} color={isOffline ? '#71717a' : 'var(--text-3)'} />
              <span style={{ fontSize: 9, color: isOffline ? '#71717a' : 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>PoP</span>
            </div>
            <div
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: isOffline ? '#71717a' : '#f97316',
              }}
            >
              {node.colo || 'SIN'}
            </div>
          </div>
        </div>
      </div>

      {/* ── Footer ───────────────────────────────── */}
      <div
        style={{
          padding: '6px 12px',
          borderTop: `1px solid ${isOffline ? 'rgba(113, 113, 122, 0.2)' : 'var(--border-1)'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-surface-2)',
        }}
      >
        <span style={{ fontSize: 10, color: isOffline ? '#71717a' : 'var(--text-3)' }}>
          {node.routes?.length ?? 0} routes
        </span>
        {isOffline ? (
          <span
            style={{
              fontSize: 10,
              color: '#71717a',
              fontStyle: 'italic',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#71717a', display: 'inline-block' }} />
            Offline • Standby
          </span>
        ) : !node.is_local ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onAccessApp?.(node);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              background: 'rgba(45, 212, 191, 0.12)',
              border: '1px solid rgba(45, 212, 191, 0.3)',
              borderRadius: 4,
              color: '#2dd4bf',
              fontSize: 10,
              fontWeight: 600,
              padding: '2px 7px',
              cursor: 'pointer',
              transition: 'background 0.15s, border-color 0.15s',
            }}
            title="Access remote web application via private IP through TunnelFlare"
          >
            <Globe size={10} color="#2dd4bf" />
            Web App
          </button>
        ) : (
          <span style={{ fontSize: 10, color: 'var(--text-3)', fontStyle: 'italic' }}>
            Local Gateway
          </span>
        )}
      </div>
    </div>
  );
};
