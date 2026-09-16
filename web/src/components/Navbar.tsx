import React from 'react';
import { 
  Network, 
  Globe, 
  Route, 
  ShieldCheck, 
  Activity, 
  Wifi, 
  Key, 
  Plus,
  RefreshCw 
} from 'lucide-react';
import type { TelemetryData, NodeStatus } from '../types';

interface NavbarProps {
  activeTab: 'canvas' | 'map' | 'routes' | 'account';
  setActiveTab: (tab: 'canvas' | 'map' | 'routes' | 'account') => void;
  telemetry: TelemetryData | null;
  nodeStatus: NodeStatus | null;
  onOpenConnectModal: () => void;
  onRefresh: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  telemetry,
  nodeStatus,
  onOpenConnectModal,
  onRefresh,
}) => {
  return (
    <header className="glass-panel" style={{ margin: '1rem', padding: '0.75rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* Top Strip: Brand & Live Telemetry HUD */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ 
            width: '38px', 
            height: '38px', 
            borderRadius: '10px', 
            background: 'linear-gradient(135deg, var(--cf-orange), #c2410c)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px var(--cf-orange-glow)'
          }}>
            <ShieldCheck size={22} color="#fff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#fff' }}>TunnelFlare</span>
              <span className="badge badge-orange" style={{ fontSize: '0.65rem', padding: '0.15rem 0.45rem' }}>Mesh 2.0</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span>Zero Trust Private Network Orchestrator</span>
              <span>•</span>
              <span style={{ color: 'var(--cyan)' }}>{nodeStatus?.site_name || 'Loading Node...'}</span>
            </div>
          </div>
        </div>

        {/* Live Telemetry HUD Bar */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '1.25rem', 
          background: 'var(--bg-surface-elevated)', 
          padding: '0.4rem 1rem', 
          borderRadius: 'var(--radius-full)',
          border: '1px solid var(--border-subtle)',
          fontSize: '0.8rem'
        }}>
          {/* Edge Colocation */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Globe size={14} color="var(--cf-orange)" />
            <span style={{ color: 'var(--text-muted)' }}>Edge PoP:</span>
            <span className="mono" style={{ color: 'var(--cf-orange)', fontWeight: 700 }}>
              [{nodeStatus?.colo || 'EDGE'}]
            </span>
          </div>

          <div style={{ width: '1px', height: '14px', background: 'var(--border-subtle)' }} />

          {/* RTT Latency */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Activity size={14} color="var(--cyan)" />
            <span style={{ color: 'var(--text-muted)' }}>RTT:</span>
            <span className="mono" style={{ color: 'var(--cyan)', fontWeight: 700 }}>
              {telemetry ? `${telemetry.rtt_ms} ms` : '14.5 ms'}
            </span>
          </div>

          <div style={{ width: '1px', height: '14px', background: 'var(--border-subtle)' }} />

          {/* Jitter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>Jitter:</span>
            <span className="mono" style={{ color: 'var(--emerald)', fontWeight: 600 }}>
              {telemetry ? `±${telemetry.jitter_ms} ms` : '±1.2 ms'}
            </span>
          </div>

          <div style={{ width: '1px', height: '14px', background: 'var(--border-subtle)' }} />

          {/* Throughput */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Wifi size={14} color="var(--purple)" />
            <span className="mono" style={{ color: 'var(--purple)', fontWeight: 600 }}>
              ▲ {telemetry?.bandwidth_up_mbps || 18.5} / ▼ {telemetry?.bandwidth_down_mbps || 42.0} Mbps
            </span>
          </div>

          <div style={{ width: '1px', height: '14px', background: 'var(--border-subtle)' }} />

          {/* Health Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ 
              width: '8px', 
              height: '8px', 
              borderRadius: '50%', 
              backgroundColor: 'var(--emerald)',
              boxShadow: '0 0 8px var(--emerald)'
            }} />
            <span style={{ color: 'var(--emerald)', fontWeight: 700, fontSize: '0.75rem' }}>
              {telemetry?.edge_status || 'OPTIMAL'}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button 
            className="btn btn-primary" 
            onClick={onOpenConnectModal}
            title="Connect subnets over Cloudflare Virtual Network"
          >
            <Plus size={16} />
            <span>Connect Route</span>
          </button>

          <button 
            className="btn btn-secondary" 
            onClick={onRefresh}
            title="Refresh network topology"
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        borderTop: '1px solid var(--border-subtle)', 
        paddingTop: '0.65rem' 
      }}>
        <nav style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button 
            className={`btn ${activeTab === 'canvas' ? 'btn-cyan' : 'btn-secondary'}`}
            onClick={() => setActiveTab('canvas')}
          >
            <Network size={16} />
            <span>Topology Mesh Canvas</span>
          </button>

          <button 
            className={`btn ${activeTab === 'map' ? 'btn-cyan' : 'btn-secondary'}`}
            onClick={() => setActiveTab('map')}
          >
            <Globe size={16} />
            <span>Geographic World Map</span>
          </button>

          <button 
            className={`btn ${activeTab === 'routes' ? 'btn-cyan' : 'btn-secondary'}`}
            onClick={() => setActiveTab('routes')}
          >
            <Route size={16} />
            <span>Subnet CIDR Routes</span>
          </button>

          <button 
            className={`btn ${activeTab === 'account' ? 'btn-cyan' : 'btn-secondary'}`}
            onClick={() => setActiveTab('account')}
          >
            <Key size={16} />
            <span>Zero Trust Account</span>
          </button>
        </nav>

        {/* Account status indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {nodeStatus?.account_linked ? (
            <span className="badge badge-emerald" style={{ cursor: 'pointer' }} onClick={() => setActiveTab('account')}>
              ● Cloudflare Account Linked ({nodeStatus.account_name || 'Active'})
            </span>
          ) : (
            <span className="badge badge-orange" style={{ cursor: 'pointer' }} onClick={() => setActiveTab('account')}>
              ⚠️ Standalone Mode (Link Account for Cloud Mesh)
            </span>
          )}
        </div>
      </div>
    </header>
  );
};
