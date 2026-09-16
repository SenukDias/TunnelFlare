export interface InterfaceInfo {
  name: string;
  mac: string;
  state: string;
  is_up: boolean;
  ipv4: string[];
  primary_ip: string | null;
}

export interface NodeStatus {
  status: string;
  hostname: string;
  site_name: string;
  os: string;
  arch: string;
  public_ip: string;
  colo: string;
  isp: string;
  country: string;
  city: string;
  latitude: number;
  longitude: number;
  ip_forwarding: boolean;
  interfaces: InterfaceInfo[];
  primary_ip: string | null;
  primary_mac: string | null;
  account_linked: boolean;
  account_id: string | null;
  account_name: string | null;
}

export interface MeshNode {
  id: string;
  name: string;
  role: string;
  status: "healthy" | "warning" | "offline";
  wan_ip: string;
  lan_cidr: string;
  mac: string;
  colo: string;
  latitude: number;
  longitude: number;
  city: string;
  country: string;
  is_local: boolean;
  routes: string[];
}

export interface MeshLink {
  source: string;
  target: string;
  rtt_ms: number;
  packet_loss: number;
  status: string;
}

export interface MeshRoute {
  id: string;
  network: string;
  tunnel_id: string;
  tunnel_name?: string;
  comment?: string;
  virtual_network_id?: string;
  created_at?: string;
}

export interface TelemetryData {
  timestamp: number;
  rtt_ms: number;
  rtt_min: number;
  rtt_avg: number;
  rtt_max: number;
  jitter_ms: number;
  packet_loss: number;
  bandwidth_up_mbps: number;
  bandwidth_down_mbps: number;
  active_streams: number;
  edge_status: string;
}
