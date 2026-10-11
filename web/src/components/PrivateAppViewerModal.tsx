import React, { useState, useEffect, useRef } from 'react';
import {
  X, Globe, Shield, RefreshCw, ExternalLink, Zap,
  CheckCircle2, AlertTriangle, ArrowRight, Laptop, Lock
} from 'lucide-react';
import type { MeshNode, ReachabilityResult } from '../types';

interface PrivateAppViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetNode: MeshNode | null;
  apiBase: string;
}

export const PrivateAppViewerModal: React.FC<PrivateAppViewerModalProps> = ({
  isOpen,
  onClose,
  targetNode,
  apiBase,
}) => {
  // Extract a sensible default IP from subnet (e.g., 10.200.0.0/16 -> 10.200.0.5)
  const getDefaultIp = (cidr?: string) => {
    if (!cidr) return '10.200.0.5';
    const baseIp = cidr.split('/')[0];
    const parts = baseIp.split('.');
    if (parts.length === 4) {
      if (parts[3] === '0') parts[3] = '5';
      return parts.join('.');
    }
    return baseIp;
  };

  const [ip, setIp] = useState<string>('10.200.0.5');
  const [port, setPort] = useState<string>('8080');
  const [path, setPath] = useState<string>('');
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [reachability, setReachability] = useState<ReachabilityResult | null>(null);
  const [activeProxyUrl, setActiveProxyUrl] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState<number>(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (targetNode) {
      const suggestedIp = getDefaultIp(targetNode.lan_cidr);
      setIp(suggestedIp);
      setReachability(null);
      setActiveProxyUrl(null);
    }
  }, [targetNode]);

  if (!isOpen || !targetNode) return null;

  const testReachability = async () => {
    setIsTesting(true);
    setReachability(null);
    try {
      const res = await fetch(`${apiBase}/api/v1/gateway/test-reach?ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}&timeout=3.0`);
      const data: ReachabilityResult = await res.json();
      setReachability(data);
    } catch (e: any) {
      setReachability({
        reachable: false,
        ip,
        port: parseInt(port) || 80,
        rtt_ms: -1,
        error: e.message || 'Failed to query reachability endpoint',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleLaunch = () => {
    const cleanPath = path.replace(/^\/+/, '');
    const proxyUrl = `${apiBase}/api/v1/gateway/proxy/${ip}/${port}/${cleanPath}`;
    setActiveProxyUrl(proxyUrl);
    setIframeKey((prev) => prev + 1);
  };

  const reloadIframe = () => {
    setIframeKey((prev) => prev + 1);
  };

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ zIndex: 1100 }}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '94vw',
          maxWidth: '1200px',
          height: '88vh',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-1)',
          borderRadius: 14,
          overflow: 'hidden',
          boxShadow: '0 25px 50px -12px rgba(0,0,0,0.7)',
        }}
      >
        {/* Modal Top Header */}
        <div
          style={{
            padding: '12px 18px',
            borderBottom: '1px solid var(--border-1)',
            background: 'var(--bg-surface-2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: 'rgba(45, 212, 191, 0.15)',
                border: '1px solid rgba(45, 212, 191, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Globe size={18} color="#2dd4bf" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-1)' }}>
                  Private Web Gateway
                </span>
                <span className="badge badge-info" style={{ fontSize: 10 }}>
                  {targetNode.name}
                </span>
                <span
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    fontSize: 11,
                    color: '#2dd4bf',
                    background: 'rgba(45, 212, 191, 0.08)',
                    padding: '2px 8px',
                    borderRadius: 4,
                    border: '1px solid rgba(45, 212, 191, 0.2)',
                  }}
                >
                  <Lock size={10} />
                  0 Public Ports Exposed
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>
                Routing private IP through TunnelFlare Point-to-Point overlay (Subnet: {targetNode.lan_cidr})
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="btn btn-ghost btn-icon"
            style={{ color: 'var(--text-2)' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Address & Control Toolbar */}
        <div
          style={{
            padding: '10px 18px',
            borderBottom: '1px solid var(--border-1)',
            background: 'var(--bg-surface)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            flexWrap: 'wrap',
          }}
        >
          {/* Target IP */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <label style={{ fontSize: 11, color: 'var(--text-3)', fontWeight: 500 }}>
              PRIVATE IP
            </label>
            <input
              type="text"
              value={ip}
              onChange={(e) => setIp(e.target.value)}
              className="input"
              style={{
                width: 140,
                fontSize: 12,
                fontFamily: 'var(--font-mono)',
                padding: '5px 8px',
                height: 30,
              }}
              placeholder="10.200.0.5"
            />
          </div>

          {/* Port */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <label style={{ fontSize: 11, color: 'var(--text-3)', fontWeight: 500 }}>
              PORT
            </label>
            <input
              type="text"
              value={port}
              onChange={(e) => setPort(e.target.value)}
              className="input"
              style={{
                width: 70,
                fontSize: 12,
                fontFamily: 'var(--font-mono)',
                padding: '5px 8px',
                height: 30,
              }}
              placeholder="8080"
            />
          </div>

          {/* Port Presets */}
          <div style={{ display: 'flex', gap: 4 }}>
            {['80', '8080', '3000', '9000'].map((p) => (
              <button
                key={p}
                onClick={() => setPort(p)}
                style={{
                  background: port === p ? 'rgba(45, 212, 191, 0.2)' : 'var(--bg-surface-2)',
                  border: `1px solid ${port === p ? '#2dd4bf' : 'var(--border-1)'}`,
                  color: port === p ? '#2dd4bf' : 'var(--text-3)',
                  borderRadius: 4,
                  fontSize: 10,
                  padding: '3px 6px',
                  cursor: 'pointer',
                }}
              >
                :{p}
              </button>
            ))}
          </div>

          {/* Path */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 160 }}>
            <label style={{ fontSize: 11, color: 'var(--text-3)', fontWeight: 500 }}>
              PATH
            </label>
            <input
              type="text"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              className="input"
              style={{
                flex: 1,
                fontSize: 12,
                fontFamily: 'var(--font-mono)',
                padding: '5px 8px',
                height: 30,
              }}
              placeholder="/ (optional)"
            />
          </div>

          {/* Actions: Test Reachability & Launch */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              onClick={testReachability}
              disabled={isTesting}
              className="btn btn-secondary"
              style={{ height: 30, fontSize: 11, padding: '0 10px', gap: 5 }}
            >
              <Zap size={12} color={isTesting ? 'var(--text-3)' : '#f97316'} />
              {isTesting ? 'Pinging...' : 'Test Reachability'}
            </button>

            <button
              onClick={handleLaunch}
              className="btn btn-primary"
              style={{ height: 30, fontSize: 11, padding: '0 12px', gap: 5 }}
            >
              <span>Connect</span>
              <ArrowRight size={12} />
            </button>
          </div>
        </div>

        {/* Reachability Feedback Banner */}
        {reachability && (
          <div
            style={{
              padding: '6px 18px',
              fontSize: 11,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: reachability.reachable ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              borderBottom: `1px solid ${reachability.reachable ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
              color: reachability.reachable ? '#4ade80' : '#f87171',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {reachability.reachable ? (
                <>
                  <CheckCircle2 size={13} color="#4ade80" />
                  <span>
                    <strong>Host Reachable:</strong> Socket open to {reachability.ip}:{reachability.port} via local mesh gateway in {reachability.rtt_ms}ms.
                  </span>
                </>
              ) : (
                <>
                  <AlertTriangle size={13} color="#f87171" />
                  <span>
                    <strong>Host Unreachable:</strong> {reachability.error} (Ensure Site B connector is running and private IP route is established).
                  </span>
                </>
              )}
            </div>
            {reachability.reachable && (
              <span style={{ fontSize: 10, opacity: 0.8 }}>Ready for HTTP transit</span>
            )}
          </div>
        )}

        {/* Embedded Browser Frame Viewport */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            background: '#09090b',
            position: 'relative',
          }}
        >
          {activeProxyUrl ? (
            <>
              {/* Browser sub-bar */}
              <div
                style={{
                  padding: '6px 12px',
                  background: 'var(--bg-surface-2)',
                  borderBottom: '1px solid var(--border-1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: 11,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, overflow: 'hidden' }}>
                  <button
                    onClick={reloadIframe}
                    className="btn btn-ghost btn-icon"
                    style={{ width: 22, height: 22, padding: 0 }}
                    title="Reload application"
                  >
                    <RefreshCw size={11} color="var(--text-2)" />
                  </button>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-2)',
                      fontSize: 11,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {activeProxyUrl}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <a
                    href={activeProxyUrl}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      color: '#2dd4bf',
                      textDecoration: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      fontSize: 11,
                    }}
                  >
                    <ExternalLink size={11} />
                    Open in Tab
                  </a>
                </div>
              </div>

              {/* Sandboxed iframe */}
              <iframe
                key={iframeKey}
                ref={iframeRef}
                src={activeProxyUrl}
                title="TunnelFlare Private Web View"
                style={{
                  flex: 1,
                  width: '100%',
                  border: 'none',
                  background: '#ffffff',
                }}
                sandbox="allow-scripts allow-forms allow-same-origin allow-popups"
              />
            </>
          ) : (
            /* Standby Landing State */
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 16,
                color: 'var(--text-3)',
                padding: '2rem',
                textAlign: 'center',
              }}
            >
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: 16,
                  background: 'rgba(45, 212, 191, 0.08)',
                  border: '1px solid rgba(45, 212, 191, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Laptop size={32} color="#2dd4bf" />
              </div>
              <div style={{ maxWidth: 440 }}>
                <h4 style={{ color: 'var(--text-1)', fontSize: 16, marginBottom: 6 }}>
                  Direct Private IP Access
                </h4>
                <p style={{ fontSize: 12, lineHeight: 1.6 }}>
                  Access internal web services running at <strong>{targetNode.name}</strong> over the encrypted TunnelFlare point-to-point mesh. Traffic is relayed locally by Site A’s gateway without public port exposure.
                </p>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  background: 'var(--bg-surface-2)',
                  padding: '10px 18px',
                  borderRadius: 8,
                  border: '1px solid var(--border-1)',
                  fontSize: 11,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Shield size={12} color="#2dd4bf" />
                  <span style={{ color: 'var(--text-2)' }}>Zero Trust Mesh Transit</span>
                </div>
                <span>•</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Lock size={12} color="#f97316" />
                  <span style={{ color: 'var(--text-2)' }}>End-to-End Encrypted</span>
                </div>
              </div>

              <button
                onClick={handleLaunch}
                className="btn btn-primary"
                style={{ padding: '8px 20px', gap: 6, fontSize: 12, marginTop: 4 }}
              >
                <Globe size={14} />
                Connect to http://{ip}:{port}{path}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
