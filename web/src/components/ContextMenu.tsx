import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Zap, Copy, BarChart2, Wifi } from 'lucide-react';

export interface ContextMenuProps {
  x: number;
  y: number;
  type: 'edge' | 'node';
  label?: string;
  sublabel?: string;
  onDisconnect?: () => void;
  onCopy?: () => void;
  onTelemetry?: () => void;
  onPing?: () => void;
  onClose: () => void;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({
  x, y, type, label, sublabel,
  onDisconnect, onCopy, onTelemetry, onPing, onClose,
}) => {
  const menuRef = useRef<HTMLDivElement>(null);

  // Clamp to viewport
  const menuX = Math.min(x, window.innerWidth - 210);
  const menuY = Math.min(y, window.innerHeight - 200);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleEsc);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleEsc);
    };
  }, [onClose]);

  return (
    <div
      ref={menuRef}
      className="context-menu"
      style={{ left: menuX, top: menuY }}
    >
      {/* Header */}
      {label && (
        <>
          <div className="context-menu-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>{label}</span>
            <button
              onClick={onClose}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--text-3)' }}
            >
              <X size={11} />
            </button>
          </div>
          {sublabel && (
            <div style={{ padding: '0 10px 6px', fontSize: 11, color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>
              {sublabel}
            </div>
          )}
          <div className="context-menu-divider" />
        </>
      )}

      {/* Edge actions */}
      {type === 'edge' && (
        <>
          {onTelemetry && (
            <button className="context-menu-item" onClick={() => { onTelemetry(); onClose(); }}>
              <BarChart2 size={13} color="var(--text-2)" />
              View Telemetry
            </button>
          )}
          {onCopy && (
            <button className="context-menu-item" onClick={() => { onCopy(); onClose(); }}>
              <Copy size={13} color="var(--text-2)" />
              Copy Route Details
            </button>
          )}
          <div className="context-menu-divider" />
          {onDisconnect && (
            <button className="context-menu-item context-menu-item--danger" onClick={() => { onDisconnect(); onClose(); }}>
              <X size={13} />
              Disconnect Route
            </button>
          )}
        </>
      )}

      {/* Node actions */}
      {type === 'node' && (
        <>
          {onPing && (
            <button className="context-menu-item" onClick={() => { onPing(); onClose(); }}>
              <Wifi size={13} color="var(--text-2)" />
              Ping Node
            </button>
          )}
          {onTelemetry && (
            <button className="context-menu-item" onClick={() => { onTelemetry(); onClose(); }}>
              <BarChart2 size={13} color="var(--text-2)" />
              View Telemetry
            </button>
          )}
          {onCopy && (
            <button className="context-menu-item" onClick={() => { onCopy(); onClose(); }}>
              <Copy size={13} color="var(--text-2)" />
              Copy Node Info
            </button>
          )}
          {onDisconnect && (
            <>
              <div className="context-menu-divider" />
              <button className="context-menu-item context-menu-item--danger" onClick={() => { onDisconnect(); onClose(); }}>
                <Zap size={13} />
                Disconnect All Routes
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
};
