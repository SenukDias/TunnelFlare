import React, { useState, useCallback, useRef } from 'react';
import {
  EdgeLabelRenderer,
  getBezierPath,
} from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import { Activity, X } from 'lucide-react';

export interface FlowEdgeData {
  rtt_ms?: number;
  packet_loss?: number;
  status?: 'active' | 'degraded' | 'error' | 'pending';
  label?: string;
  onDisconnect?: (edgeId: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  active:   '#2dd4bf',
  degraded: '#f59e0b',
  error:    '#ef4444',
  pending:  '#3f3f46',
};



// Mini RTT sparkline — last 8 values rendered as SVG bars
const Sparkline: React.FC<{ value: number }> = ({ value }) => {
  const bars = Array.from({ length: 8 }, (_, i) => {
    const h = 4 + Math.sin(i * 0.9 + value * 0.01) * 3 + (i === 7 ? 2 : 0);
    return Math.max(2, Math.min(12, h));
  });
  return (
    <svg width="36" height="14" viewBox="0 0 36 14" style={{ display: 'block' }}>
      {bars.map((h, i) => (
        <rect
          key={i}
          x={i * 4.5}
          y={14 - h}
          width="3"
          height={h}
          rx="1"
          fill={i === 7 ? '#2dd4bf' : 'rgba(255,255,255,0.2)'}
        />
      ))}
    </svg>
  );
};

export const FlowEdge: React.FC<EdgeProps> = ({
  id,
  sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition,
  data,
  selected,
}) => {
  const edgeData = data as FlowEdgeData | undefined;
  const status = edgeData?.status ?? 'active';
  const strokeColor = STATUS_COLORS[status] ?? STATUS_COLORS.active;

  const [hovered, setHovered] = useState(false);
  const particleRef = useRef<SVGCircleElement>(null);

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  });

  const pathId = `edge-path-${id}`;
  const gradientId = `edge-grad-${id}`;

  const rtt = edgeData?.rtt_ms ?? 0;
  const loss = edgeData?.packet_loss ?? 0;

  const handleDisconnect = useCallback(() => {
    edgeData?.onDisconnect?.(id);
  }, [edgeData, id]);

  const isActive = status === 'active' || status === 'degraded';

  return (
    <>
      {/* Gradient definition */}
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
          <stop offset="50%" stopColor={strokeColor} stopOpacity="0.9" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0.3" />
        </linearGradient>
      </defs>

      {/* Named path for animateMotion */}
      <path id={pathId} d={edgePath} fill="none" stroke="none" />

      {/* Selection/hover glow layer */}
      {(selected || hovered) && (
        <path
          d={edgePath}
          fill="none"
          stroke={strokeColor}
          strokeWidth={8}
          strokeOpacity={0.08}
          strokeLinecap="round"
          style={{ pointerEvents: 'none' }}
        />
      )}

      {/* Main edge stroke */}
      <path
        d={edgePath}
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth={selected || hovered ? 2 : 1.5}
        strokeLinecap="round"
        style={{ transition: 'stroke-width 0.15s' }}
      />

      {/* Invisible thick hit area for click/hover */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={18}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{ cursor: 'pointer' }}
      />

      {/* Animated particle dot — travels along path */}
      {isActive && (
        <g style={{ pointerEvents: 'none' }}>
          <circle ref={particleRef} r="3" fill={strokeColor} opacity="0.9">
            <animateMotion
              dur={status === 'active' ? '2.5s' : '4s'}
              repeatCount="indefinite"
              calcMode="spline"
              keySplines="0.4 0 0.6 1"
            >
              <mpath href={`#${pathId}`} />
            </animateMotion>
          </circle>
          {/* Soft trail behind the dot */}
          <circle r="5" fill={strokeColor} opacity="0.15">
            <animateMotion
              dur={status === 'active' ? '2.5s' : '4s'}
              repeatCount="indefinite"
              calcMode="spline"
              keySplines="0.4 0 0.6 1"
            >
              <mpath href={`#${pathId}`} />
            </animateMotion>
          </circle>
        </g>
      )}

      {/* RTT chip label */}
      <EdgeLabelRenderer>
        {/* Floating RTT pill on the edge midpoint */}
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          <div
            style={{
              background: 'var(--bg-surface-2)',
              border: `1px solid ${hovered || selected ? strokeColor : 'var(--border-1)'}`,
              borderRadius: 'var(--radius-full)',
              padding: '2px 8px',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-2)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              whiteSpace: 'nowrap',
              cursor: 'pointer',
              transition: 'border-color 0.15s, background 0.15s',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <span
              style={{
                width: '5px',
                height: '5px',
                borderRadius: '50%',
                background: strokeColor,
                flexShrink: 0,
              }}
            />
            {rtt > 0 ? `${rtt}ms` : '—'}
            {loss > 0 && (
              <span style={{ color: STATUS_COLORS.degraded, marginLeft: 2 }}>
                {loss}%↑
              </span>
            )}
          </div>
        </div>

        {/* Hover tooltip — rich detail */}
        {hovered && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, calc(-100% - 14px)) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: 'all',
              zIndex: 10,
            }}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
          >
            <div
              className="tooltip scale-in"
              style={{
                background: 'var(--bg-surface-2)',
                border: `1px solid ${strokeColor}33`,
                borderRadius: 'var(--radius-md)',
                padding: '10px 12px',
                minWidth: '180px',
                pointerEvents: 'all',
              }}
            >
              {/* Header row */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Activity size={12} color={strokeColor} />
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Tunnel Metrics
                  </span>
                </div>
                <button
                  onClick={handleDisconnect}
                  style={{
                    background: 'var(--state-error-dim)',
                    border: '1px solid var(--state-error-border)',
                    borderRadius: 'var(--radius-xs)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 3,
                    padding: '2px 6px',
                    color: 'var(--state-error)',
                    fontSize: 10,
                    fontWeight: 500,
                    cursor: 'pointer',
                    transition: 'all 0.1s',
                  }}
                  title="Disconnect this route"
                >
                  <X size={9} />
                  Disconnect
                </button>
              </div>

              {/* Sparkline + RTT */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <Sparkline value={rtt} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, color: strokeColor }}>
                  {rtt}ms
                </span>
              </div>

              {/* Stats row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 12px' }}>
                {[
                  { label: 'Latency', value: `${rtt}ms`, color: strokeColor },
                  { label: 'Loss', value: loss === 0 ? '0%' : `${loss}%`, color: loss > 0 ? '#f59e0b' : 'var(--text-2)' },
                  { label: 'Protocol', value: 'QUIC', color: 'var(--text-2)' },
                  { label: 'Status', value: status.toUpperCase(), color: strokeColor },
                ].map(({ label, value, color }) => (
                  <div key={label}>
                    <div style={{ fontSize: 10, color: 'var(--text-3)', marginBottom: 1 }}>{label}</div>
                    <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 600, color }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
};
