import React from 'react';
import { Flame, Network, Globe, Route, Settings, Activity, RefreshCw, ArrowUp, ArrowDown } from 'lucide-react';
import type { TelemetryData, NodeStatus } from '../types';

type TabId = 'canvas' | 'map' | 'routes' | 'account';

interface NavbarProps {
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
  telemetry: TelemetryData | null;
  nodeStatus: NodeStatus | null;
  activeConnectionCount?: number;
  onOpenConnectModal: () => void;
  onRefresh: () => void;
}

const TABS: { id: TabId; label: string; Icon: React.FC<any> }[] = [
  { id: 'canvas',  label: 'Canvas',    Icon: Network  },
  { id: 'map',     label: 'World Map', Icon: Globe    },
  { id: 'routes',  label: 'Routes',    Icon: Route    },
  { id: 'account', label: 'Account',   Icon: Settings },
];

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  telemetry,
  nodeStatus,
  activeConnectionCount = 0,
  onOpenConnectModal,
  onRefresh,
}) => {
  return (
    <header
      style={{
        height: 52,
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-1)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
        gap: 0,
        flexShrink: 0,
        position: 'relative',
        zIndex: 50,
      }}
    >
      {/* ── Brand ──────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 28, flexShrink: 0 }}>
        <div
          style={{
            width: 28, height: 28,
            borderRadius: 8,
            background: 'var(--brand-orange)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <Flame size={15} color="#fff" strokeWidth={2.2} />
        </div>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-1)', letterSpacing: '-0.01em' }}>
          TunnelFlare
        </span>
        <span className="badge badge-orange" style={{ fontSize: 9, padding: '1px 5px' }}>
          Mesh
        </span>
      </div>

      {/* ── Tab Nav ────────────────────────────── */}
      <nav style={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
        {TABS.map(({ id, label, Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '5px 12px',
                background: 'transparent',
                border: 'none',
                borderBottom: isActive ? '2px solid var(--text-1)' : '2px solid transparent',
                borderRadius: 0,
                color: isActive ? 'var(--text-1)' : 'var(--text-3)',
                fontSize: 13,
                fontWeight: isActive ? 500 : 400,
                cursor: 'pointer',
                height: 52,
                transition: 'color 0.15s, border-color 0.15s',
                position: 'relative',
              }}
            >
              <Icon size={13} strokeWidth={isActive ? 2 : 1.5} />
              {label}
              {/* Active connection count badge on Canvas tab */}
              {id === 'canvas' && activeConnectionCount > 0 && (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 16, height: 16,
                    borderRadius: '50%',
                    background: 'var(--bg-surface-3)',
                    border: '1px solid var(--border-1)',
                    fontSize: 9,
                    fontWeight: 600,
                    color: 'var(--text-2)',
                  }}
                >
                  {activeConnectionCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* ── Right: Telemetry + Live ─────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto', flexShrink: 0 }}>
        {/* Telemetry pills */}
        {telemetry && (
          <>
            <div
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '3px 10px',
                background: 'var(--bg-surface-2)',
                border: '1px solid var(--border-1)',
                borderRadius: 'var(--radius-full)',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-2)',
              }}
            >
              <Activity size={11} color="var(--flow-active)" />
              <span style={{ color: 'var(--text-1)' }}>{telemetry.rtt_ms}ms</span>
            </div>

            <div
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '3px 10px',
                background: 'var(--bg-surface-2)',
                border: '1px solid var(--border-1)',
                borderRadius: 'var(--radius-full)',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-2)',
              }}
            >
              <ArrowUp size={10} color="var(--state-success)" />
              <span>{telemetry.bandwidth_up_mbps}M</span>
              <span style={{ color: 'var(--border-2)' }}>·</span>
              <ArrowDown size={10} color="var(--state-info)" />
              <span>{telemetry.bandwidth_down_mbps}M</span>
            </div>
          </>
        )}

        {/* Live indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-3)' }}>
          <span className="status-dot status-dot--live" />
          <span>Live</span>
        </div>

        {/* Divider */}
        <div style={{ width: 1, height: 20, background: 'var(--border-1)' }} />

        {/* Refresh */}
        <button className="btn btn-ghost btn-icon" onClick={onRefresh} title="Refresh">
          <RefreshCw size={13} />
        </button>

        {/* Node site name */}
        {nodeStatus && (
          <div
            style={{
              padding: '3px 10px',
              background: 'var(--bg-surface-2)',
              border: '1px solid var(--border-1)',
              borderRadius: 'var(--radius-full)',
              fontSize: 11,
              color: 'var(--text-2)',
              display: 'flex', alignItems: 'center', gap: 5,
            }}
          >
            <span
              style={{
                width: 5, height: 5, borderRadius: '50%',
                background: nodeStatus.status === 'online' ? 'var(--state-success)' : 'var(--state-error)',
              }}
            />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5 }}>
              {nodeStatus.site_name || nodeStatus.hostname}
            </span>
          </div>
        )}
      </div>
    </header>
  );
};
