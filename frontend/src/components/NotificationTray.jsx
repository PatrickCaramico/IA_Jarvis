// Central de notificações na HUD (4.2, experimental). Só aparece com a opção ligada e algo novo.
export default function NotificationTray({ items, onDismiss }) {
  if (!items?.length) return null;
  return (
    <aside className="notif-tray" aria-label="Notificações do Windows" aria-live="polite">
      <header className="notif-tray-head">
        <span>NOTIFICAÇÕES</span>
        <button type="button" onClick={onDismiss} aria-label="Limpar notificações">limpar</button>
      </header>
      <ul>
        {items.slice(0, 5).map((n) => (
          <li key={n.id}>
            <strong>{n.app}</strong>
            {n.title && <span>{n.title}</span>}
          </li>
        ))}
      </ul>
    </aside>
  );
}
