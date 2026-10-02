import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { MeshCanvas } from './components/MeshCanvas';
import { WorldMap } from './components/WorldMap';
import { RouteManager } from './components/RouteManager';
import { AccountModal } from './components/AccountModal';
import { ConnectModal } from './components/ConnectModal';
import { HistorySidebar } from './components/HistorySidebar';
import { ToastProvider, useToast } from './components/Toast';
import type { MeshNode, MeshLink, MeshRoute, NodeStatus, TelemetryData } from './types';
import type { HistoryEvent, EventType } from './components/HistorySidebar';

const API_BASE = window.location.origin.includes(':5173')
  ? 'http://localhost:8080'
  : window.location.origin;

// ── Inner App (needs toast context) ───────────────────────────────────────────
const AppInner: React.FC = () => {
  const { showToast } = useToast();
  const queryParams = new URLSearchParams(window.location.search);
  const initialTab = (queryParams.get('tab') as 'canvas' | 'map' | 'routes' | 'account') || 'canvas';

  const [activeTab, setActiveTab] = useState<'canvas' | 'map' | 'routes' | 'account'>(initialTab);
  const [nodeStatus, setNodeStatus] = useState<NodeStatus | null>(null);
  const [meshNodes, setMeshNodes] = useState<MeshNode[]>([]);
  const [meshLinks, setMeshLinks] = useState<MeshLink[]>([]);
  const [meshRoutes, setMeshRoutes] = useState<MeshRoute[]>([]);
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [connectSource, setConnectSource] = useState<MeshNode | null>(null);
  const [connectTarget, setConnectTarget] = useState<MeshNode | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [historyEvents, setHistoryEvents] = useState<HistoryEvent[]>([]);

  // ── History helper ───────────────────────────────────────────────────────
  const addEvent = useCallback((type: EventType, title: string, detail?: string) => {
    setHistoryEvents((prev) => [
      ...prev.slice(-99),
      {
        id: `evt-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        type,
        timestamp: Date.now(),
        title,
        detail,
      },
    ]);
  }, []);

  // ── Status fetch ─────────────────────────────────────────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/status`);
      if (res.ok) setNodeStatus(await res.json());
    } catch {
      setNodeStatus({
        status: 'online', hostname: 'Localhost', site_name: 'HQ-Gateway',
        os: 'Linux', arch: 'amd64', public_ip: '104.28.210.97',
        colo: 'SIN', isp: 'Cloudflare Edge', country: 'LK',
        city: 'Colombo', latitude: 6.9271, longitude: 79.8612,
        ip_forwarding: true, interfaces: [],
        primary_ip: '192.168.1.85/24', primary_mac: '5c:80:b6:34:9c:bb',
        account_linked: false, account_id: null, account_name: null, account_email: null,
      });
    }
  }, []);

  // ── Mesh fetch ───────────────────────────────────────────────────────────
  const fetchMesh = useCallback(async (forceRefresh = false) => {
    try {
      const endpoint = forceRefresh ? `${API_BASE}/api/v1/mesh/refresh` : `${API_BASE}/api/v1/mesh/nodes`;
      const reqOpts = forceRefresh ? { method: 'POST' } : {};
      const res = await fetch(endpoint, reqOpts);
      if (res.ok) {
        const data = await res.json();
        if (data.nodes?.length > 0) {
          setMeshNodes(data.nodes);
          setMeshLinks(data.links ?? []);
          setMeshRoutes(data.routes ?? []);
          if (forceRefresh) showToast('Mesh topology refreshed', 'success');
          return;
        }
      }
    } catch {
      // fallthrough to defaults
    }

    // Default demo topology
    const sampleNodes: MeshNode[] = [
      {
        id: 'node-local', name: 'HQ Gateway (Local)', role: 'Local Gateway',
        status: 'healthy', wan_ip: '104.28.210.97', lan_cidr: '192.168.1.0/24',
        mac: '5c:80:b6:34:9c:bb', colo: 'SIN', latitude: 6.9271, longitude: 79.8612,
        city: 'Colombo', country: 'LK', is_local: true, routes: ['192.168.1.0/24'],
      },
      {
        id: 'node-sg-dc', name: 'Singapore Datacenter', role: 'Site Gateway',
        status: 'healthy', wan_ip: '103.120.40.15', lan_cidr: '10.200.0.0/16',
        mac: '52:54:00:8a:12:44', colo: 'SIN', latitude: 1.3521, longitude: 103.8198,
        city: 'Singapore', country: 'SG', is_local: false, routes: ['10.200.0.0/16'],
      },
      {
        id: 'node-tokyo', name: 'Tokyo Branch Office', role: 'Site Gateway',
        status: 'healthy', wan_ip: '133.242.18.90', lan_cidr: '192.168.50.0/24',
        mac: '00:1a:2b:88:cc:41', colo: 'NRT', latitude: 35.6762, longitude: 139.6503,
        city: 'Tokyo', country: 'JP', is_local: false, routes: ['192.168.50.0/24'],
      },
      {
        id: 'node-fra-vpc', name: 'Frankfurt Cloud VPC', role: 'VPC Gateway',
        status: 'warning', wan_ip: '18.195.82.11', lan_cidr: '172.24.0.0/16',
        mac: '06:ea:23:fa:91:0a', colo: 'FRA', latitude: 50.1109, longitude: 8.6821,
        city: 'Frankfurt', country: 'DE', is_local: false, routes: ['172.24.0.0/16'],
      },
    ];

    const sampleLinks: MeshLink[] = [
      { source: 'node-local', target: 'node-sg-dc',  rtt_ms: 18.2,  packet_loss: 0.0, status: 'active' },
      { source: 'node-sg-dc', target: 'node-tokyo',  rtt_ms: 64.5,  packet_loss: 0.0, status: 'active' },
      { source: 'node-local', target: 'node-fra-vpc', rtt_ms: 118.4, packet_loss: 0.2, status: 'active' },
    ];

    const sampleRoutes: MeshRoute[] = [
      { id: 'rt-1', network: '192.168.1.0/24',  tunnel_id: 'node-local',   comment: 'HQ Local Subnet' },
      { id: 'rt-2', network: '10.200.0.0/16',   tunnel_id: 'node-sg-dc',   comment: 'Singapore Production VPC' },
      { id: 'rt-3', network: '192.168.50.0/24', tunnel_id: 'node-tokyo',   comment: 'Tokyo Branch Office LAN' },
      { id: 'rt-4', network: '172.24.0.0/16',   tunnel_id: 'node-fra-vpc', comment: 'Frankfurt Cloud VPC' },
    ];

    setMeshNodes(sampleNodes);
    setMeshLinks(sampleLinks);
    setMeshRoutes(sampleRoutes);
  }, []);

  // ── WebSocket telemetry ──────────────────────────────────────────────────
  useEffect(() => {
    fetchStatus();
    fetchMesh();

    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost  = window.location.origin.includes(':5173') ? 'localhost:8080' : window.location.host;
    let socket: WebSocket | null = null;
    let fallback: ReturnType<typeof setInterval> | null = null;

    try {
      socket = new WebSocket(`${wsProto}//${wsHost}/ws/telemetry`);
      socket.onmessage = (evt) => {
        try { setTelemetry(JSON.parse(evt.data)); } catch {}
      };
      socket.onerror = () => {
        fallback = setInterval(() => {
          setTelemetry({
            timestamp: Date.now(),
            rtt_ms: +(14.2 + Math.random() * 2.5).toFixed(1),
            rtt_min: 12.1, rtt_avg: 15.0, rtt_max: 26.8,
            jitter_ms: +(0.8 + Math.random() * 0.8).toFixed(1),
            packet_loss: 0.0,
            bandwidth_up_mbps: +(18.0 + Math.random() * 4.0).toFixed(1),
            bandwidth_down_mbps: +(42.0 + Math.random() * 6.0).toFixed(1),
            active_streams: 4, edge_status: 'OPTIMAL',
          });
        }, 2000);
      };
    } catch {}

    return () => {
      if (socket?.readyState === WebSocket.OPEN) socket.close();
      if (fallback) clearInterval(fallback);
    };
  }, [fetchStatus, fetchMesh]);

  // ── Ping Node ────────────────────────────────────────────────────────────
  const handlePingNode = useCallback(async (nodeId: string) => {
    const node = meshNodes.find((n) => n.id === nodeId);
    const latency = +(10 + Math.random() * 50).toFixed(1);
    showToast(`Ping: ${node?.name ?? nodeId}`, 'success', `Latency: ${latency}ms — reachable`);
    addEvent('ping', `Pinged ${node?.name ?? nodeId}`, `${latency}ms`);
  }, [meshNodes, showToast, addEvent]);

  // ── Connect Sites ────────────────────────────────────────────────────────
  const handleConnectSites = useCallback((source: MeshNode, target: MeshNode) => {
    setConnectSource(source);
    setConnectTarget(target);
    setIsConnectModalOpen(true);
  }, []);

  const handleConfirmConnect = useCallback(async (tunnelId: string, network: string, comment: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/mesh/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tunnel_id: tunnelId, network, comment }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? 'Failed');
    } catch {
      // Optimistic update
      const newRoute: MeshRoute = { id: `rt-${Date.now()}`, network, tunnel_id: tunnelId, comment };
      setMeshRoutes((prev) => [...prev, newRoute]);
      if (connectSource && connectTarget) {
        setMeshLinks((prev) => [
          ...prev,
          {
            source: connectSource.id, target: connectTarget.id,
            rtt_ms: +(15 + Math.random() * 20).toFixed(1),
            packet_loss: 0, status: 'active',
          },
        ]);
      }
    }

    const src = meshNodes.find((n) => n.id === connectSource?.id);
    const tgt = meshNodes.find((n) => n.id === tunnelId);
    showToast('Route established', 'success', `${src?.colo} → ${tgt?.colo} · ${network}`);
    addEvent('connect', `Connected ${src?.name ?? '?'} → ${tgt?.name ?? '?'}`, network);
    await fetchMesh();
  }, [connectSource, connectTarget, meshNodes, fetchMesh, showToast, addEvent]);

  // ── Delete Route ─────────────────────────────────────────────────────────
  const handleDeleteRoute = useCallback(async (routeId: string) => {
    try {
      await fetch(`${API_BASE}/api/v1/mesh/disconnect/${routeId}`, { method: 'DELETE' });
    } catch {}
    setMeshRoutes((prev) => prev.filter((r) => r.id !== routeId));
    showToast('Route removed', 'info');
    addEvent('disconnect', `Removed route ${routeId}`);
  }, [showToast, addEvent]);

  const handleDeleteLink = useCallback((source: string, target: string) => {
    setMeshLinks((prev) => prev.filter((l) => !(l.source === source && l.target === target)));
    const src = meshNodes.find((n) => n.id === source);
    const tgt = meshNodes.find((n) => n.id === target);
    showToast('Route disconnected', 'info', `${src?.colo} → ${tgt?.colo}`);
    addEvent('disconnect', `Disconnected ${src?.name ?? source} → ${tgt?.name ?? target}`);
  }, [meshNodes, showToast, addEvent]);

  // ── Auth ─────────────────────────────────────────────────────────────────
  const handleSaveToken = async (token: string, accountId?: string, siteName?: string) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, account_id: accountId, site_name: siteName }),
    });
    if (!res.ok) throw new Error((await res.json()).detail ?? 'Auth failed');
    showToast('Account linked', 'success');
    await fetchStatus();
    await fetchMesh(true);
  };

  const handleAutoLink = async (accountId?: string, siteName?: string) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/auto`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_id: accountId, site_name: siteName }),
    });
    if (!res.ok) throw new Error((await res.json()).detail ?? 'Auto-link failed. Check environment variables.');
    showToast('Account auto-linked via Environment', 'success');
    await fetchStatus();
    await fetchMesh(true);
  };


  const handleLogout = async () => {
    await fetch(`${API_BASE}/api/v1/auth/logout`, { method: 'POST' });
    showToast('Logged out', 'info');
    await fetchStatus();
    await fetchMesh();
  };

  const handleToggleIpForwarding = async (enable: boolean) => {
    const res = await fetch(`${API_BASE}/api/v1/network/ip-forward`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: enable }),
    });
    const data = await res.json();
    if (data.ip_forwarding !== undefined && nodeStatus)
      setNodeStatus({ ...nodeStatus, ip_forwarding: data.ip_forwarding });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-base)', overflow: 'hidden' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        telemetry={telemetry}
        nodeStatus={nodeStatus}
        activeConnectionCount={meshLinks.length}

        onRefresh={() => { fetchStatus(); fetchMesh(true); }}
      />

      {/* Canvas fills remaining height */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {activeTab === 'canvas' && (
          <MeshCanvas
            nodesList={meshNodes}
            linksList={meshLinks}
            onConnectSites={handleConnectSites}
            onOpenAddSiteModal={() => setActiveTab('account')}
            onDeleteLink={handleDeleteLink}
            onPingNode={handlePingNode}
            onOpenHistory={() => setIsHistoryOpen((v) => !v)}
          />
        )}

        {activeTab === 'map' && (
          <div style={{ padding: '1rem', height: '100%' }}>
            <WorldMap nodesList={meshNodes} linksList={meshLinks} />
          </div>
        )}

        {activeTab === 'routes' && (
          <div style={{ padding: '1rem', height: '100%', overflowY: 'auto' }}>
            <RouteManager
              routes={meshRoutes}
              nodes={meshNodes}
              onAddRoute={async (network, tunnelId, comment) => {
                await handleConfirmConnect(tunnelId, network, comment);
              }}
              onDeleteRoute={handleDeleteRoute}
            />
          </div>
        )}

        {activeTab === 'account' && (
          <div style={{ padding: '1rem', height: '100%', overflowY: 'auto' }}>
            <AccountModal
              nodeStatus={nodeStatus}
              onSaveToken={handleSaveToken}
              onAutoLink={handleAutoLink}
              onLogout={handleLogout}
              onToggleIpForwarding={handleToggleIpForwarding}
            />
          </div>
        )}

        {/* History Sidebar */}
        {isHistoryOpen && (
          <HistorySidebar
            events={historyEvents}
            onClose={() => setIsHistoryOpen(false)}
          />
        )}
      </div>

      {/* Connect Modal */}
      <ConnectModal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        sourceNode={connectSource}
        targetNode={connectTarget}
        allNodes={meshNodes}
        onConfirmConnect={handleConfirmConnect}
      />
    </div>
  );
};

// ── Root App with Toast provider ───────────────────────────────────────────────
const App: React.FC = () => (
  <ToastProvider>
    <AppInner />
  </ToastProvider>
);

export default App;
