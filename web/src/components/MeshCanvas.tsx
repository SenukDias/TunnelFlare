import React, { useCallback, useMemo, useState, useRef, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  BackgroundVariant,
  Panel,
} from '@xyflow/react';
import type { Connection, Edge, Node, EdgeMouseHandler } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toPng } from 'html-to-image';
import {
  Plus, LayoutGrid, GitBranch, Layers,
  Download, Maximize2, History, HelpCircle, X
} from 'lucide-react';

import { SiteNode } from './SiteNode';
import { FlowEdge } from './FlowEdge';
import { ContextMenu } from './ContextMenu';
import type { MeshNode, MeshLink } from '../types';

interface ContextMenuState {
  x: number;
  y: number;
  type: 'edge' | 'node';
  edgeId?: string;
  nodeId?: string;
  label?: string;
  sublabel?: string;
}

interface MeshCanvasProps {
  nodesList: MeshNode[];
  linksList: MeshLink[];
  onConnectSites: (sourceNode: MeshNode, targetNode: MeshNode) => void;
  onOpenAddSiteModal: () => void;
  onDeleteLink?: (source: string, target: string) => void;
  onPingNode?: (nodeId: string) => void;
  onOpenHistory?: () => void;
  onAccessApp?: (node: MeshNode) => void;
}

type LayoutMode = 'hub-spoke' | 'bidirectional' | 'mesh';

const LAYOUT_LABELS: Record<LayoutMode, { label: string; icon: React.ReactNode }> = {
  'hub-spoke':     { label: 'Hub & Spoke',    icon: <GitBranch size={13} /> },
  'bidirectional': { label: 'Bidirectional',  icon: <Layers size={13} /> },
  'mesh':          { label: 'Full Mesh',       icon: <LayoutGrid size={13} /> },
};

function computeLayout(nodes: MeshNode[], mode: LayoutMode): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {};
  const onlineNodes = nodes.filter((n) => n.status !== 'offline');
  const offlineNodes = nodes.filter((n) => n.status === 'offline');

  const onlineLocal = onlineNodes.find((n) => n.is_local);
  const onlineRemotes = onlineNodes.filter((n) => !n.is_local);

  let maxOnlineY = 120;

  if (mode === 'hub-spoke') {
    // Local left, online remotes fanned right
    if (onlineLocal) {
      const centerY = onlineRemotes.length > 0
        ? 60 + ((onlineRemotes.length - 1) * 200) / 2
        : 120;
      positions[onlineLocal.id] = { x: 60, y: Math.max(60, centerY) };
      maxOnlineY = Math.max(maxOnlineY, positions[onlineLocal.id].y + 200);
    }
    onlineRemotes.forEach((n, i) => {
      const y = 60 + i * 200;
      positions[n.id] = { x: 480, y };
      maxOnlineY = Math.max(maxOnlineY, y + 200);
    });
  } else if (mode === 'bidirectional') {
    // All online nodes in a horizontal chain
    onlineNodes.forEach((n, i) => {
      const x = 80 + i * 320;
      const y = 140;
      positions[n.id] = { x, y };
      maxOnlineY = Math.max(maxOnlineY, y + 200);
    });
  } else {
    // Full mesh — circular layout for online nodes
    if (onlineNodes.length <= 1) {
      onlineNodes.forEach((n) => {
        positions[n.id] = { x: 340, y: 120 };
        maxOnlineY = Math.max(maxOnlineY, 320);
      });
    } else {
      const cx = 380, cy = 180, r = Math.min(220, 100 + onlineNodes.length * 30);
      onlineNodes.forEach((n, i) => {
        const angle = (2 * Math.PI * i) / onlineNodes.length - Math.PI / 2;
        const x = cx + r * Math.cos(angle);
        const y = cy + r * Math.sin(angle);
        positions[n.id] = { x, y };
        maxOnlineY = Math.max(maxOnlineY, y + 200);
      });
    }
  }

  // ── Position offline nodes docked at the bottom in gray ────────────────
  const offlineStartY = Math.max(460, maxOnlineY + 80);
  offlineNodes.forEach((n, i) => {
    const col = i % 4;
    const row = Math.floor(i / 4);
    positions[n.id] = {
      x: 60 + col * 290,
      y: offlineStartY + row * 220,
    };
  });

  return positions;
}

export const MeshCanvas: React.FC<MeshCanvasProps> = ({
  nodesList,
  linksList,
  onConnectSites,
  onOpenAddSiteModal,
  onDeleteLink,
  onPingNode,
  onOpenHistory,
  onAccessApp,
}) => {
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('hub-spoke');
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [, setIsFullscreen] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const canvasRef = useRef<HTMLDivElement>(null);

  const edgeTypes = useMemo(() => ({ flowEdge: FlowEdge }), []);
  const nodeTypes = useMemo(() => ({ siteNode: SiteNode }), []);

  const layoutPositions = useMemo(
    () => computeLayout(nodesList, layoutMode),
    [nodesList, layoutMode]
  );

  const initialNodes: Node[] = useMemo(() =>
    nodesList.map((site) => ({
      id: site.id,
      type: 'siteNode',
      position: layoutPositions[site.id] ?? { x: 0, y: 0 },
      data: {
        node: site,
        onContextMenu: (e: React.MouseEvent, nodeId: string) => {
          e.preventDefault();
          e.stopPropagation();
          const n = nodesList.find((x) => x.id === nodeId);
          setContextMenu({
            x: e.clientX, y: e.clientY,
            type: 'node',
            nodeId,
            label: n?.name.replace(/^[^\w]+ /, '') ?? 'Node',
            sublabel: n?.lan_cidr,
          });
        },
        onAccessApp: (n: MeshNode) => {
          onAccessApp?.(n);
        },
      },
    })),
    [nodesList, layoutPositions, onAccessApp]
  );

  // Filter edges so offline nodes NEVER have active connection links
  const initialEdges: Edge[] = useMemo(() => {
    const isOnline = (id: string) => {
      const n = nodesList.find((x) => x.id === id);
      return n && n.status !== 'offline';
    };

    return linksList
      .filter((link) => isOnline(link.source) && isOnline(link.target))
      .map((link, i) => ({
        id: `edge-${link.source}-${link.target}-${i}`,
        source: link.source,
        target: link.target,
        sourceHandle: 'right',
        targetHandle: 'left-tgt',
        type: 'flowEdge',
        data: {
          rtt_ms: link.rtt_ms,
          packet_loss: link.packet_loss,
          status: link.status === 'active'
            ? (link.packet_loss > 0.5 ? 'degraded' : 'active')
            : 'error',
          onDisconnect: (edgeId: string) => {
            setEdges((eds) => eds.filter((e) => e.id !== edgeId));
            onDeleteLink?.(link.source, link.target);
          },
        },
      }));
  }, [linksList, nodesList, onDeleteLink]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync when props change
  useEffect(() => { setNodes(initialNodes); }, [initialNodes, setNodes]);
  useEffect(() => { setEdges(initialEdges); }, [initialEdges, setEdges]);

  // Re-layout when mode changes (animate positions)
  useEffect(() => {
    const pos = computeLayout(nodesList, layoutMode);
    setNodes((nds) =>
      nds.map((n) => ({ ...n, position: pos[n.id] ?? n.position }))
    );
  }, [layoutMode, nodesList, setNodes]);

  const onConnect = useCallback(
    (params: Connection) => {
      const src = nodesList.find((n) => n.id === params.source);
      const tgt = nodesList.find((n) => n.id === params.target);
      if (src && tgt) {
        // Disallow connecting to or from offline nodes
        if (src.status === 'offline' || tgt.status === 'offline') {
          return;
        }
        setEdges((eds) => addEdge({
          ...params,
          type: 'flowEdge',
          data: { rtt_ms: 0, packet_loss: 0, status: 'active' },
        }, eds));
        onConnectSites(src, tgt);
      }
    },
    [nodesList, onConnectSites, setEdges]
  );

  const isValidConnection = useCallback(
    (connection: Connection | Edge) => {
      const src = nodesList.find((n) => n.id === connection.source);
      const tgt = nodesList.find((n) => n.id === connection.target);
      if (!src || !tgt) return false;
      if (src.status === 'offline' || tgt.status === 'offline') return false;
      return src.id !== tgt.id;
    },
    [nodesList]
  );

  const onEdgeContextMenu: EdgeMouseHandler = useCallback((e, edge) => {
    e.preventDefault();
    const src = nodesList.find((n) => n.id === edge.source);
    const tgt = nodesList.find((n) => n.id === edge.target);
    const d = edge.data as any;
    setContextMenu({
      x: e.clientX, y: e.clientY,
      type: 'edge',
      edgeId: edge.id,
      label: `${src?.colo ?? edge.source} → ${tgt?.colo ?? edge.target}`,
      sublabel: `${d?.rtt_ms ?? 0}ms • ${d?.packet_loss ?? 0}% loss`,
    });
  }, [nodesList]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'k' || e.key === 'K') setShowShortcuts((v) => !v);
      if (e.key === 'f' || e.key === 'F') toggleFullscreen();
      if (e.key === 'h' || e.key === 'H') onOpenHistory?.();
      if (e.key === 'Escape') { setContextMenu(null); setShowShortcuts(false); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onOpenHistory]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement && canvasRef.current) {
      canvasRef.current.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  };

  const handleExport = async () => {
    const el = document.querySelector('.react-flow__viewport') as HTMLElement;
    if (!el) return;
    try {
      const png = await toPng(el, { backgroundColor: '#09090b', quality: 1 });
      const link = document.createElement('a');
      link.download = `tunnelflare-topology-${Date.now()}.png`;
      link.href = png;
      link.click();
    } catch (err) {
      console.warn('Export failed:', err);
    }
  };

  const dismissContext = () => setContextMenu(null);

  return (
    <div
      ref={canvasRef}
      style={{ width: '100%', height: 'calc(100vh - 58px)', position: 'relative', background: 'var(--bg-base)' }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        isValidConnection={isValidConnection}
        onEdgeContextMenu={onEdgeContextMenu}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.15, maxZoom: 1.2 }}
        minZoom={0.3}
        maxZoom={2}
        attributionPosition="bottom-left"
        onPaneClick={dismissContext}
        deleteKeyCode="Delete"
        multiSelectionKeyCode="Shift"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="rgba(255,255,255,0.05)"
        />

        <Controls
          showInteractive={false}
          position="bottom-right"
          style={{ bottom: '1rem', right: '1rem' }}
        />

        <MiniMap
          nodeColor={(n) => {
            const site = nodesList.find((x) => x.id === n.id);
            if (!site) return '#27272a';
            if (site.status === 'healthy') return '#2dd4bf';
            if (site.status === 'warning') return '#f59e0b';
            return '#52525b';
          }}
          maskColor="rgba(9,9,11,0.85)"
          position="bottom-left"
          style={{ bottom: '1rem', left: '1rem' }}
        />

        {/* ── Top-left: Legend ─────────────────── */}
        <Panel position="top-left">
          <div
            className="card"
            style={{ padding: '6px 10px', display: 'flex', alignItems: 'center', gap: 12, fontSize: 11 }}
          >
            {[
              { label: 'Connected', color: '#2dd4bf' },
              { label: 'Degraded',  color: '#f59e0b' },
              { label: 'Offline (Standby)', color: '#71717a' },
            ].map(({ label, color }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'block' }} />
                <span style={{ color: 'var(--text-3)' }}>{label}</span>
              </div>
            ))}
          </div>
        </Panel>

        {/* ── Top-center: Layout Switcher ───────── */}
        <Panel position="top-center">
          <div className="card" style={{ display: 'flex', gap: 2, padding: '3px' }}>
            {(Object.entries(LAYOUT_LABELS) as [LayoutMode, { label: string; icon: React.ReactNode }][]).map(
              ([mode, { label, icon }]) => (
                <button
                  key={mode}
                  onClick={() => setLayoutMode(mode)}
                  className="btn btn-ghost"
                  style={{
                    padding: '4px 10px',
                    fontSize: 12,
                    background: layoutMode === mode ? 'var(--bg-surface-3)' : 'transparent',
                    color: layoutMode === mode ? 'var(--text-1)' : 'var(--text-3)',
                    borderRadius: 'var(--radius-sm)',
                    gap: 5,
                  }}
                >
                  {icon}
                  {label}
                </button>
              )
            )}
          </div>
        </Panel>

        {/* ── Top-right: Actions ────────────────── */}
        <Panel position="top-right">
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <div className="card" style={{ padding: '4px 10px', fontSize: 11, color: 'var(--text-3)', display: 'flex', alignItems: 'center', gap: 5 }}>
              <span>Drag handle to connect</span>
            </div>

            <button className="btn btn-ghost btn-icon" onClick={() => onOpenHistory?.()} title="History (H)">
              <History size={15} />
            </button>
            <button className="btn btn-ghost btn-icon" onClick={handleExport} title="Export PNG">
              <Download size={15} />
            </button>
            <button className="btn btn-ghost btn-icon" onClick={toggleFullscreen} title="Fullscreen (F)">
              <Maximize2 size={15} />
            </button>
            <button className="btn btn-ghost btn-icon" onClick={() => setShowShortcuts(true)} title="Keyboard Shortcuts (K)">
              <HelpCircle size={15} />
            </button>

            <button
              className="btn btn-primary"
              onClick={onOpenAddSiteModal}
              style={{ padding: '5px 12px', fontSize: 12 }}
            >
              <Plus size={13} />
              Add Site
            </button>
          </div>
        </Panel>
      </ReactFlow>

      {/* ── Context Menu ─────────────────────────── */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          type={contextMenu.type}
          label={contextMenu.label}
          sublabel={contextMenu.sublabel}
          onClose={dismissContext}
          onDisconnect={
            contextMenu.type === 'edge' && contextMenu.edgeId
              ? () => {
                  setEdges((eds) => eds.filter((e) => e.id !== contextMenu.edgeId));
                  dismissContext();
                }
              : undefined
          }
          onCopy={
            contextMenu.type === 'edge'
              ? () => navigator.clipboard.writeText(`${contextMenu.label} • ${contextMenu.sublabel}`)
              : () => {
                  const n = nodesList.find((x) => x.id === contextMenu.nodeId);
                  if (n) navigator.clipboard.writeText(`${n.name}\n${n.wan_ip}\n${n.lan_cidr}`);
                }
          }
          onPing={
            contextMenu.type === 'node' && contextMenu.nodeId
              ? () => onPingNode?.(contextMenu.nodeId!)
              : undefined
          }
          onAccessApp={
            contextMenu.type === 'node' && contextMenu.nodeId
              ? () => {
                  const n = nodesList.find((x) => x.id === contextMenu.nodeId);
                  if (n) onAccessApp?.(n);
                }
              : undefined
          }
        />
      )}

      {/* ── Keyboard Shortcuts Panel ──────────────── */}
      {showShortcuts && (
        <div className="modal-backdrop" onClick={() => setShowShortcuts(false)}>
          <div className="modal-content" style={{ maxWidth: 360 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-1)' }}>
              <span style={{ fontWeight: 600, fontSize: 14 }}>Keyboard Shortcuts</span>
              <button className="btn btn-ghost btn-icon" onClick={() => setShowShortcuts(false)}>
                <X size={14} />
              </button>
            </div>
            <div style={{ padding: '12px 20px 20px' }}>
              {[
                { key: 'K',      desc: 'Open keyboard shortcuts' },
                { key: 'F',      desc: 'Toggle fullscreen' },
                { key: 'H',      desc: 'Open connection history' },
                { key: 'Del',    desc: 'Delete selected edge/node' },
                { key: 'Shift',  desc: 'Multi-select nodes' },
                { key: 'Esc',    desc: 'Close menus / cancel' },
                { key: '⌘ Fit', desc: 'Fit view to canvas' },
              ].map(({ key, desc }) => (
                <div key={key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--border-1)' }}>
                  <span style={{ fontSize: 13, color: 'var(--text-2)' }}>{desc}</span>
                  <kbd className="kbd">{key}</kbd>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
