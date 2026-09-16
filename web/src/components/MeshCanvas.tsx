import React, { useCallback, useMemo } from 'react';
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
import type { Connection, Edge, Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { SiteNode } from './SiteNode';
import type { MeshNode, MeshLink } from '../types';
import { Plus } from 'lucide-react';


interface MeshCanvasProps {
  nodesList: MeshNode[];
  linksList: MeshLink[];
  onConnectSites: (sourceNode: MeshNode, targetNode: MeshNode) => void;
  onOpenAddSiteModal: () => void;
}

export const MeshCanvas: React.FC<MeshCanvasProps> = ({
  nodesList,
  linksList,
  onConnectSites,
  onOpenAddSiteModal,
}) => {
  const nodeTypes = useMemo(() => ({ siteNode: SiteNode }), []);

  // Compute initial node positions in a circular or grid layout
  const initialNodes: Node[] = useMemo(() => {
    return nodesList.map((site, index) => {
      // Position nodes in a panoramic layout
      const col = index % 3;
      const row = Math.floor(index / 3);
      const x = 80 + col * 360;
      const y = 80 + row * 280;

      return {
        id: site.id,
        type: 'siteNode',
        position: { x, y },
        data: { node: site },
      };
    });
  }, [nodesList]);

  // Compute initial edges
  const initialEdges: Edge[] = useMemo(() => {
    return linksList.map((link, index) => ({
      id: `edge-${link.source}-${link.target}-${index}`,
      source: link.source,
      target: link.target,
      animated: true,
      label: `${link.rtt_ms} ms / ${link.packet_loss}% loss`,
      labelStyle: { fill: 'var(--cyan)', fontWeight: 700, fontSize: 11, fontFamily: 'var(--font-mono)' },
      labelBgStyle: { fill: 'var(--bg-surface)', fillOpacity: 0.9, rx: 6, ry: 6 },
      labelBgPadding: [6, 4] as [number, number],
      style: { stroke: 'var(--cyan)', strokeWidth: 2 },
    }));
  }, [linksList]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync state when nodesList or linksList props change
  React.useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  React.useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  // Handle drag-and-drop wire connection between nodes
  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => addEdge({ ...params, animated: true }, eds));
      const source = nodesList.find((n) => n.id === params.source);
      const target = nodesList.find((n) => n.id === params.target);
      if (source && target) {
        onConnectSites(source, target);
      }
    },
    [nodesList, onConnectSites, setEdges]
  );

  return (
    <div style={{ width: '100%', height: 'calc(100vh - 160px)', position: 'relative' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1.5} color="rgba(0, 229, 255, 0.15)" />
        <Controls showInteractive={false} position="bottom-right" />
        <MiniMap
          nodeColor={() => 'var(--cyan)'}
          maskColor="rgba(6, 9, 17, 0.85)"
          position="bottom-left"
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
          }}
        />

        {/* Floating Canvas Action Panel */}
        <Panel position="top-right" style={{ display: 'flex', gap: '0.5rem' }}>
          <div className="glass-panel" style={{ padding: '0.4rem 0.65rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              ⚡ Drag connector handle between cards to establish Zero Trust Route
            </span>
            <button className="btn btn-primary" onClick={onOpenAddSiteModal} style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>
              <Plus size={14} />
              <span>Add Site</span>
            </button>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};
