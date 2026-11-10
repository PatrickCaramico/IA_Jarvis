import WaterPanel from "./WaterPanel.jsx";

// Widget "Hidratação" (painel flutuante e Central de Widgets): agora usa o recipiente animado
// da seção 18. Mantido com o mesmo nome e as mesmas props para não quebrar quem o importa.
export default function WaterWidget({ api, onInteract }) {
  return <WaterPanel api={api} size="full" onInteract={onInteract} />;
}
