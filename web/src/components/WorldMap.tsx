import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { MeshNode, MeshLink } from '../types';

interface WorldMapProps {
  nodesList: MeshNode[];
  linksList: MeshLink[];
  onSelectNode?: (node: MeshNode) => void;
}

export const WorldMap: React.FC<WorldMapProps> = ({ nodesList, linksList }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersRef = useRef<L.LayerGroup | null>(null);
  const polylinesRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Initialize Map if not yet created
    if (!mapInstanceRef.current) {
      const defaultCenter: [number, number] = [20, 10];
      const map = L.map(mapContainerRef.current, {
        center: defaultCenter,
        zoom: 3,
        zoomControl: true,
        attributionControl: false,
      });

      // Dark Matter CartoDB Basemap
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd',
      }).addTo(map);

      mapInstanceRef.current = map;
      markersRef.current = L.layerGroup().addTo(map);
      polylinesRef.current = L.layerGroup().addTo(map);
    }

    const map = mapInstanceRef.current;
    const markersGroup = markersRef.current;
    const polylinesGroup = polylinesRef.current;

    if (!map || !markersGroup || !polylinesGroup) return;

    // Clear previous markers & lines
    markersGroup.clearLayers();
    polylinesGroup.clearLayers();

    const bounds: [number, number][] = [];

    // Render Markers for each site
    nodesList.forEach((node) => {
      const lat = node.latitude || 20.0;
      const lng = node.longitude || 0.0;
      bounds.push([lat, lng]);

      // Custom pulsing HTML marker
      const isLocal = node.is_local;
      const ringColor = isLocal ? 'var(--cyan)' : 'var(--cf-orange)';
      const markerHtml = `
        <div style="position: relative; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;">
          <div style="
            position: absolute; 
            width: 100%; 
            height: 100%; 
            border-radius: 50%; 
            background: ${ringColor}; 
            opacity: 0.35; 
            animation: radarWave 2s infinite ease-out;
          "></div>
          <div style="
            width: 14px; 
            height: 14px; 
            border-radius: 50%; 
            background: ${ringColor}; 
            border: 2px solid #fff; 
            box-shadow: 0 0 12px ${ringColor};
          "></div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: markerHtml,
        className: 'custom-mesh-pin',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([lat, lng], { icon: customIcon });

      const popupContent = `
        <div style="min-width: 220px; font-family: var(--font-sans); padding: 0.25rem;">
          <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #283e6b; padding-bottom: 0.4rem; margin-bottom: 0.5rem;">
            <strong style="color: #fff; font-size: 0.95rem;">${node.name}</strong>
            <span style="font-size: 0.7rem; color: ${node.status === 'healthy' ? 'var(--emerald)' : 'var(--amber)'}; font-weight: 700;">
              ● ${node.status.toUpperCase()}
            </span>
          </div>
          <div style="font-size: 0.78rem; line-height: 1.6; color: #cbd5e1;">
            <div>Subnet CIDR: <strong style="color: var(--emerald); font-family: var(--font-mono);">${node.lan_cidr}</strong></div>
            <div>Public WAN: <span style="font-family: var(--font-mono); color: #fff;">${node.wan_ip}</span></div>
            <div>Physical MAC: <span style="font-family: var(--font-mono); color: var(--purple); font-size: 0.72rem;">${node.mac}</span></div>
            <div>Edge Colocation: <span style="color: var(--cf-orange); font-weight: 700;">[${node.colo}]</span></div>
            <div>Region: <span>${node.city || 'Zero Trust'}, ${node.country || 'Global'}</span></div>
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);
      markersGroup.addLayer(marker);
    });

    // Render Curved Polylines between connected nodes
    linksList.forEach((link) => {
      const sourceNode = nodesList.find((n) => n.id === link.source);
      const targetNode = nodesList.find((n) => n.id === link.target);

      if (sourceNode && targetNode) {
        const p1: [number, number] = [sourceNode.latitude || 20, sourceNode.longitude || 0];
        const p2: [number, number] = [targetNode.latitude || 20, targetNode.longitude || 0];

        // Draw animated polyline
        const polyline = L.polyline([p1, p2], {
          color: 'var(--cyan)',
          weight: 2.5,
          opacity: 0.8,
          dashArray: '8, 6',
        });

        polyline.bindTooltip(
          `<strong>${link.rtt_ms} ms</strong> (Loss: ${link.packet_loss}%)`,
          { sticky: true, className: 'mesh-link-tooltip' }
        );

        polylinesGroup.addLayer(polyline);
      }
    });

    // Auto-fit bounds if we have points
    if (bounds.length > 0) {
      try {
        map.fitBounds(bounds, { padding: [60, 60], maxZoom: 6 });
      } catch (e) {
        // Fallback gracefully
      }
    }
  }, [nodesList, linksList]);

  return (
    <div style={{ width: '100%', height: 'calc(100vh - 160px)', position: 'relative', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

      {/* Map Legend Overlay */}
      <div
        className="glass-panel"
        style={{
          position: 'absolute',
          bottom: '1.5rem',
          left: '1.5rem',
          zIndex: 999,
          padding: '0.75rem 1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.4rem',
          fontSize: '0.75rem',
        }}
      >
        <div style={{ fontWeight: 700, color: '#fff', marginBottom: '0.2rem' }}>Mesh Map Legend</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--cyan)' }} />
          <span>Local Site Node</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--cf-orange)' }} />
          <span>Remote Branch / Cloud Gateway</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{ width: '16px', height: '2px', background: 'var(--cyan)', borderTop: '1px dashed #fff' }} />
          <span>Active Zero Trust QUIC Link</span>
        </div>
      </div>
    </div>
  );
};
