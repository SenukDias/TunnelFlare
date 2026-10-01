import React from 'react';
import { X, Link2, Link2Off, Wifi, AlertCircle, CheckCircle2 } from 'lucide-react';

export type EventType = 'connect' | 'disconnect' | 'ping' | 'error' | 'heal';

export interface HistoryEvent {
  id: string;
  type: EventType;
  timestamp: number;
  title: string;
  detail?: string;
}

interface HistorySidebarProps {
  events: HistoryEvent[];
  onClose: () => void;
}

const EVENT_META: Record<EventType, { Icon: React.FC<any>; iconColor: string; bg: string }> = {
  connect:    { Icon: Link2,         iconColor: '#2dd4bf', bg: 'rgba(45,212,191,0.1)' },
  disconnect: { Icon: Link2Off,      iconColor: '#ef4444', bg: 'rgba(239,68,68,0.1)' },
  ping:       { Icon: Wifi,          iconColor: '#38bdf8', bg: 'rgba(56,189,248,0.1)' },
  error:      { Icon: AlertCircle,   iconColor: '#f59e0b', bg: 'rgba(245,158,11,0.1)' },
  heal:       { Icon: CheckCircle2,  iconColor: '#22c55e', bg: 'rgba(34,197,94,0.1)' },
};

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}

function timeAgo(ts: number): string {
  const secs = Math.floor((Date.now() - ts) / 1000);
  if (secs < 60)  return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  return `${Math.floor(secs / 3600)}h ago`;
}

export const HistorySidebar: React.FC<HistorySidebarProps> = ({ events, onClose }) => {
  return (
    <div className="history-sidebar">
      {/* Header */}
      <div
        style={{
          padding: '14px 16px',
          borderBottom: '1px solid var(--border-1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}
      >
        <div>
          <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-1)' }}>Connection History</div>
          <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 1 }}>{events.length} events</div>
        </div>
        <button className="btn btn-ghost btn-icon" onClick={onClose} title="Close">
          <X size={14} />
        </button>
      </div>

      {/* Event List */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {events.length === 0 ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '200px',
              gap: 8,
              color: 'var(--text-3)',
            }}
          >
            <Wifi size={24} strokeWidth={1} />
            <span style={{ fontSize: 12 }}>No events yet</span>
          </div>
        ) : (
          [...events].reverse().map((evt) => {
            const { Icon, iconColor, bg } = EVENT_META[evt.type];
            return (
              <div key={evt.id} className="history-event fade-in">
                {/* Icon */}
                <div
                  className="history-event-icon"
                  style={{ background: bg }}
                >
                  <Icon size={14} color={iconColor} strokeWidth={1.8} />
                </div>

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-1)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {evt.title}
                  </div>
                  {evt.detail && (
                    <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>
                      {evt.detail}
                    </div>
                  )}
                </div>

                {/* Time */}
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontSize: 10, color: 'var(--text-3)' }}>{timeAgo(evt.timestamp)}</div>
                  <div style={{ fontSize: 9, color: 'var(--text-4)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>
                    {formatTime(evt.timestamp)}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '10px 16px',
          borderTop: '1px solid var(--border-1)',
          display: 'flex',
          justifyContent: 'flex-end',
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 10, color: 'var(--text-3)' }}>Press H to toggle</span>
      </div>
    </div>
  );
};
