import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { 
  Building2, 
  Server, 
  Cloud, 
  Network, 
  Copy, 
  Check, 
  Cpu, 
  Globe 
} from 'lucide-react';
import type { MeshNode } from '../types';

interface SiteNodeProps {
  data: {
    node: MeshNode;
    onConnectNode?: (nodeId: string) => void;
  };
}

export const SiteNode: React.FC<SiteNodeProps> = ({ data }) => {
  const { node } = data;
  const [copied, setCopied] = React.useState(false);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const getRoleIcon = () => {
    if (node.is_local) return <Building2 size={16} color="var(--cyan)" />;
    if (node.name.toLowerCase().includes('cloud') || node.name.toLowerCase().includes('vpc')) {
      return <Cloud size={16} color="var(--purple)" />;
    }
    return <Server size={16} color="var(--cf-orange)" />;
  };

  const getStatusBadge = () => {
    if (node.status === 'healthy') {
      return (
        <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--emerald)' }} />
          HEALTHY
        </span>
      );
    }
    if (node.status === 'warning') {
      return (
        <span className="badge badge-orange" style={{ fontSize: '0.65rem' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--amber)' }} />
          DEGRADED
        </span>
      );
    }
    return (
      <span className="badge" style={{ background: 'rgba(255, 51, 102, 0.15)', color: 'var(--rose)', border: '1px solid rgba(255, 51, 102, 0.3)', fontSize: '0.65rem' }}>
        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--rose)' }} />
        OFFLINE
      </span>
    );
  };

  return (
    <div style={{
      width: '290px',
      background: node.is_local ? 'linear-gradient(180deg, #111e3b 0%, #0c1529 100%)' : 'linear-gradient(180deg, #141c2e 0%, #0d1424 100%)',
      border: node.is_local ? '1.5px solid var(--cyan)' : '1px solid var(--border-highlight)',
      borderRadius: 'var(--radius-lg)',
      padding: '0.85rem',
      boxShadow: node.is_local ? '0 0 25px rgba(0, 229, 255, 0.25)' : 'var(--shadow-card)',
      color: 'var(--text-main)',
      position: 'relative',
      userSelect: 'none'
    }}>
      {/* Top Handle */}
      <Handle type="target" position={Position.Top} style={{ background: 'var(--cyan)', width: '10px', height: '10px' }} />
      <Handle type="source" position={Position.Top} id="top-source" style={{ background: 'var(--cf-orange)', width: '10px', height: '10px', opacity: 0 }} />

      {/* Card Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.65rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{
            background: 'var(--bg-surface-elevated)',
            padding: '0.4rem',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid var(--border-subtle)'
          }}>
            {getRoleIcon()}
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.92rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span>{node.name}</span>
              {node.is_local && (
                <span style={{ fontSize: '0.65rem', background: 'rgba(0, 229, 255, 0.15)', color: 'var(--cyan)', padding: '0.1rem 0.35rem', borderRadius: '4px', fontWeight: 700 }}>
                  LOCAL
                </span>
              )}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
              {node.city || 'Zero Trust Node'}, {node.country || 'Edge'}
            </div>
          </div>
        </div>

        {getStatusBadge()}
      </div>

      {/* Primary LAN Subnet CIDR (Crucial for Site-to-Site VPN) */}
      <div style={{
        background: 'var(--bg-base)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '0.5rem 0.65rem',
        marginBottom: '0.65rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
          <Network size={14} color="var(--emerald)" />
          <div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Routed Subnet CIDR</div>
            <div className="mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--emerald)' }}>
              {node.lan_cidr}
            </div>
          </div>
        </div>
        <button 
          onClick={() => copyToClipboard(node.lan_cidr)}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-dim)', padding: '0.2rem' }}
          title="Copy CIDR"
        >
          {copied ? <Check size={13} color="var(--emerald)" /> : <Copy size={13} />}
        </button>
      </div>

      {/* Network Details Grid (WAN IP, Hardware MAC) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.75rem' }}>
        {/* WAN Public IP */}
        <div style={{ background: 'var(--bg-surface-elevated)', padding: '0.4rem 0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ color: 'var(--text-dim)', fontSize: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Globe size={11} color="var(--cf-orange)" />
            <span>Public WAN IP</span>
          </div>
          <div className="mono" style={{ fontWeight: 600, color: 'var(--text-main)', marginTop: '0.15rem' }}>
            {node.wan_ip}
          </div>
        </div>

        {/* Physical Hardware MAC */}
        <div style={{ background: 'var(--bg-surface-elevated)', padding: '0.4rem 0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ color: 'var(--text-dim)', fontSize: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Cpu size={11} color="var(--purple)" />
            <span>Physical MAC</span>
          </div>
          <div className="mono" style={{ fontWeight: 600, color: 'var(--text-main)', marginTop: '0.15rem', fontSize: '0.7rem' }}>
            {node.mac || '5c:80:b6:34:9c:bb'}
          </div>
        </div>
      </div>

      {/* Footer Tag & Drag Hint */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '0.65rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
        <span>PoP: <strong style={{ color: 'var(--cf-orange)' }}>[{node.colo || 'SIN'}]</strong></span>
        <span style={{ color: 'var(--cyan)', fontStyle: 'italic', fontSize: '0.68rem' }}>● Drag port to link</span>
      </div>

      {/* Left, Right, Bottom Connection Handles */}
      <Handle type="target" position={Position.Left} id="left-target" style={{ background: 'var(--cyan)', width: '10px', height: '10px' }} />
      <Handle type="source" position={Position.Left} id="left-source" style={{ background: 'var(--cf-orange)', width: '10px', height: '10px', opacity: 0 }} />

      <Handle type="target" position={Position.Right} id="right-target" style={{ background: 'var(--cyan)', width: '10px', height: '10px' }} />
      <Handle type="source" position={Position.Right} id="right-source" style={{ background: 'var(--cf-orange)', width: '10px', height: '10px', opacity: 0 }} />

      <Handle type="target" position={Position.Bottom} id="bottom-target" style={{ background: 'var(--cyan)', width: '10px', height: '10px' }} />
      <Handle type="source" position={Position.Bottom} id="bottom-source" style={{ background: 'var(--cf-orange)', width: '10px', height: '10px', opacity: 0 }} />
    </div>
  );
};
