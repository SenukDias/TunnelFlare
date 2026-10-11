import React, { useState, useEffect, useRef } from 'react';
import {
  X, Server, Check, Copy, ArrowRight, RefreshCw,
  Terminal, ShieldCheck, CheckCircle2, ChevronRight,
  Boxes
} from 'lucide-react';
import type { CreateConnectorResponse, ConnectorStatus } from '../types';

interface AddSiteModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiBase: string;
  onSiteCreated: () => Promise<void>;
}

export const AddSiteModal: React.FC<AddSiteModalProps> = ({
  isOpen,
  onClose,
  apiBase,
  onSiteCreated,
}) => {
  const [step, setStep] = useState<1 | 2>(1);
  const [siteName, setSiteName] = useState<string>('Site-B-Remote');
  const [lanCidr, setLanCidr] = useState<string>('10.200.0.0/24');
  const [comment, setComment] = useState<string>('TunnelFlare P2P Connector');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [connectorData, setConnectorData] = useState<CreateConnectorResponse | null>(null);
  const [status, setStatus] = useState<ConnectorStatus | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const pollTimerRef = useRef<any>(null);

  useEffect(() => {
    if (!isOpen) {
      setStep(1);
      setError(null);
      setConnectorData(null);
      setStatus(null);
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    }
  }, [isOpen]);

  useEffect(() => {
    if (step === 2 && connectorData?.tunnel_id) {
      const pollStatus = async () => {
        try {
          const res = await fetch(`${apiBase}/api/v1/connector/status/${connectorData.tunnel_id}`);
          if (res.ok) {
            const data: ConnectorStatus = await res.json();
            setStatus(data);
          }
        } catch {
          // ignore transient poll failure
        }
      };

      pollStatus();
      pollTimerRef.current = setInterval(pollStatus, 2500);

      return () => {
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      };
    }
  }, [step, connectorData, apiBase]);

  if (!isOpen) return null;

  const handleCreateConnector = async () => {
    if (!siteName.trim()) {
      setError('Site name is required');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/v1/connector/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          site_name: siteName.trim(),
          lan_cidr: lanCidr.trim(),
          comment: comment.trim(),
          auto_route: true,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create connector');
      }

      const data: CreateConnectorResponse = await res.json();
      setConnectorData(data);
      setStep(2);
    } catch (e: any) {
      setError(e.message || 'Error communicating with TunnelFlare backend');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleFinish = async () => {
    await onSiteCreated();
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ zIndex: 1100 }}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '90vw',
          maxWidth: 680,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-1)',
          borderRadius: 14,
          overflow: 'hidden',
          boxShadow: '0 25px 50px -12px rgba(0,0,0,0.7)',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '14px 20px',
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
                background: 'rgba(249, 115, 22, 0.15)',
                border: '1px solid rgba(249, 115, 22, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Server size={18} color="#f97316" />
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-1)' }}>
                Point-to-Point Connector Setup
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-3)' }}>
                {step === 1 ? 'Step 1: Configure Site Identity & Subnet' : 'Step 2: Deploy Connector to Remote Site'}
              </div>
            </div>
          </div>

          <button onClick={onClose} className="btn btn-ghost btn-icon">
            <X size={16} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px 24px' }}>
          {error && (
            <div
              style={{
                marginBottom: 16,
                padding: '10px 14px',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: 8,
                color: '#f87171',
                fontSize: 12,
              }}
            >
              {error}
            </div>
          )}

          {step === 1 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-2)', marginBottom: 6 }}>
                  REMOTE SITE NAME
                </label>
                <input
                  type="text"
                  value={siteName}
                  onChange={(e) => setSiteName(e.target.value)}
                  className="input"
                  style={{ width: '100%', fontSize: 13, padding: '8px 12px' }}
                  placeholder="e.g. Site-B-Branch"
                />
                <span style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 4, display: 'block' }}>
                  A unique identifier for this remote node on the mesh topology.
                </span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-2)', marginBottom: 6 }}>
                  PRIVATE SUBNET CIDR
                </label>
                <input
                  type="text"
                  value={lanCidr}
                  onChange={(e) => setLanCidr(e.target.value)}
                  className="input"
                  style={{ width: '100%', fontSize: 13, fontFamily: 'var(--font-mono)', padding: '8px 12px' }}
                  placeholder="e.g. 10.200.0.0/24 or 192.168.10.0/24"
                />
                <span style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 4, display: 'block' }}>
                  The private IP range hosting the internal web application at the remote site.
                </span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-2)', marginBottom: 6 }}>
                  COMMENT / PURPOSE
                </label>
                <input
                  type="text"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  className="input"
                  style={{ width: '100%', fontSize: 13, padding: '8px 12px' }}
                  placeholder="e.g. P2P Private Web Access"
                />
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  background: 'var(--bg-surface-2)',
                  borderRadius: 8,
                  border: '1px solid var(--border-1)',
                  fontSize: 11,
                  color: 'var(--text-2)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                }}
              >
                <ShieldCheck size={16} color="#2dd4bf" style={{ flexShrink: 0, marginTop: 1 }} />
                <span>
                  TunnelFlare will provision a dedicated outbound-only encrypted tunnel token. No firewall openings or public IP addresses are needed at the remote site.
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                <button onClick={onClose} className="btn btn-secondary" style={{ padding: '8px 16px' }}>
                  Cancel
                </button>
                <button
                  onClick={handleCreateConnector}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ padding: '8px 20px', gap: 6 }}
                >
                  {loading ? <RefreshCw size={14} className="spin" /> : null}
                  <span>Generate Connector</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Live Connection Tracker Badge */}
              <div
                style={{
                  padding: '12px 16px',
                  background: status?.connected ? 'rgba(34, 197, 94, 0.1)' : 'rgba(249, 115, 22, 0.1)',
                  border: `1px solid ${status?.connected ? 'rgba(34, 197, 94, 0.3)' : 'rgba(249, 115, 22, 0.3)'}`,
                  borderRadius: 8,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {status?.connected ? (
                    <CheckCircle2 size={18} color="#4ade80" />
                  ) : (
                    <div style={{ width: 14, height: 14, borderRadius: '50%', background: '#f97316', animation: 'pulse 1.5s infinite' }} />
                  )}
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: status?.connected ? '#4ade80' : '#fb923c' }}>
                      {status?.connected ? 'Connector Online & Connected!' : 'Waiting for Remote Connector...'}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>
                      {status?.connected
                        ? `Edge PoP: ${status.colo || 'SIN'} • ${status.connection_count || 1} active connection(s)`
                        : 'Run one of the commands below on Site B to establish the tunnel.'}
                    </div>
                  </div>
                </div>

                {status?.connected && (
                  <span className="badge badge-success" style={{ fontSize: 11 }}>
                    HEALTHY
                  </span>
                )}
              </div>

              {/* Install Commands */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <Boxes size={14} color="#2dd4bf" />
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-1)' }}>
                    Option A: Run via Docker (Recommended for Site B)
                  </span>
                </div>
                <div
                  style={{
                    position: 'relative',
                    background: '#09090b',
                    border: '1px solid var(--border-1)',
                    borderRadius: 8,
                    padding: '10px 12px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    color: '#a1a1aa',
                    wordBreak: 'break-all',
                  }}
                >
                  {connectorData?.install_commands.docker}
                  <button
                    onClick={() => copyToClipboard(connectorData?.install_commands.docker || '', 'docker')}
                    style={{
                      position: 'absolute',
                      right: 8,
                      top: 8,
                      background: 'rgba(255,255,255,0.08)',
                      border: '1px solid var(--border-1)',
                      borderRadius: 4,
                      color: copiedKey === 'docker' ? '#4ade80' : 'var(--text-2)',
                      padding: '3px 7px',
                      cursor: 'pointer',
                      fontSize: 10,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    {copiedKey === 'docker' ? <Check size={11} /> : <Copy size={11} />}
                    {copiedKey === 'docker' ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <Terminal size={14} color="#f97316" />
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-1)' }}>
                    Option B: Run as Linux System Service
                  </span>
                </div>
                <div
                  style={{
                    position: 'relative',
                    background: '#09090b',
                    border: '1px solid var(--border-1)',
                    borderRadius: 8,
                    padding: '10px 12px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    color: '#a1a1aa',
                    wordBreak: 'break-all',
                  }}
                >
                  {connectorData?.install_commands.linux_service}
                  <button
                    onClick={() => copyToClipboard(connectorData?.install_commands.linux_service || '', 'linux')}
                    style={{
                      position: 'absolute',
                      right: 8,
                      top: 8,
                      background: 'rgba(255,255,255,0.08)',
                      border: '1px solid var(--border-1)',
                      borderRadius: 4,
                      color: copiedKey === 'linux' ? '#4ade80' : 'var(--text-2)',
                      padding: '3px 7px',
                      cursor: 'pointer',
                      fontSize: 10,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    {copiedKey === 'linux' ? <Check size={11} /> : <Copy size={11} />}
                    {copiedKey === 'linux' ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
                <button
                  onClick={() => setStep(1)}
                  className="btn btn-ghost"
                  style={{ fontSize: 12 }}
                >
                  ← Back to Config
                </button>

                <button
                  onClick={handleFinish}
                  className="btn btn-primary"
                  style={{ padding: '8px 24px', gap: 6 }}
                >
                  <span>Finish & View Mesh</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
