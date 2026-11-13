export const GODS_EYE_CATEGORIES = [
  // V6.9: trânsito ao vivo da sua cidade (mapa do Waze); é a categoria que abre primeiro
  { id: "traffic", label: "Trânsito", icon: "🚦", live: true, layers: [] },
  {
    id: "movement",
    label: "Movimento",
    icon: "✈",
    layers: [
      { id: "flights", label: "Voos", value: "—", color: "#facc15" },
      { id: "ships", label: "Navios", value: "—", color: "#38bdf8" },
    ],
  },
  {
    id: "space",
    label: "Espaço",
    icon: "🛰",
    layers: [
      { id: "satellites", label: "Satélites", value: "—", color: "#e879f9" },
      { id: "starlink", label: "Starlink", value: "—", color: "#c084fc" },
      { id: "missions", label: "Missões espaciais", value: "—", color: "#f0abfc" },
    ],
  },
  {
    id: "events",
    label: "Eventos",
    icon: "⚠",
    layers: [
      { id: "earthquakes", label: "Terremotos 24h", value: "—", color: "#fb7185" },
      { id: "cyclones", label: "Ciclones", value: "—", color: "#60a5fa" },
      { id: "fires", label: "Queimadas 24h", value: "—", color: "#fb923c" },
      { id: "us-fires", label: "Incêndios (EUA)", value: "—", color: "#f97316" },
    ],
  },
  {
    id: "weather",
    label: "Clima",
    icon: "☁",
    layers: [
      { id: "wind", label: "Vento", value: "—", color: "#67e8f9" },
      { id: "clouds", label: "Nuvens", value: "—", color: "#cbd5e1" },
      { id: "rain", label: "Radar de chuva", value: "—", color: "#60a5fa" },
    ],
  },
  {
    id: "city",
    label: "Cidade",
    icon: "🏙",
    layers: [
      { id: "traffic", label: "Trânsito", value: "—", color: "#facc15" },
      { id: "transit", label: "Transporte público", value: "—", color: "#4ade80" },
      { id: "radio", label: "Rádios", value: "—", color: "#f472b6" },
    ],
  },
  {
    id: "cameras",
    label: "Câmeras",
    icon: "📷",
    layers: [
      { id: "traffic-cameras", label: "Câmeras de trânsito", value: "—", color: "#22d3ee" },
      { id: "plate-readers", label: "Leitores de placa (pontos)", value: "—", color: "#a78bfa" },
    ],
  },
  {
    id: "infrastructure",
    label: "Infra",
    icon: "🏭",
    layers: [
      { id: "datacenters", label: "Datacenters", value: "—", color: "#2dd4bf" },
      { id: "power-plants", label: "Represas e usinas", value: "—", color: "#facc15" },
      { id: "military", label: "Instalações militares", value: "—", color: "#94a3b8" },
    ],
  },
  {
    id: "map",
    label: "Mapa",
    icon: "🗺",
    layers: [
      { id: "imagery", label: "Imagens recentes", value: "—", color: "#4ade80" },
      { id: "cities-3d", label: "Cidades em 3D", value: "—", color: "#fbbf24" },
    ],
  },
  {
    id: "personal",
    label: "Pessoal",
    icon: "👤",
    layers: [
      { id: "location", label: "Minha localização", value: "—", color: "#22d3ee" },
      { id: "reminders", label: "Lembretes", value: "—", color: "#f472b6" },
    ],
  },
];
