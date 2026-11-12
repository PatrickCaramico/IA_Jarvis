/**
 * V4.3: card do briefing "bom dia". Todos seguem o mesmo molde:
 * ícone + rótulo mono (ex.: "PANORAMA · CLIMA"), título, conteúdo e rodapé com a procedência.
 * kind: weather | agenda | email | news | health (manhã), tasks | water (fechamento do "boa noite")
 * e notifications | metrics | commands (telas por assunto: "notificações", "meus dados de saúde", "comandos")
 */

const ICONS = {
  weather: "☀", agenda: "▦", email: "✉", news: "◉", health: "♥", tasks: "☑", water: "◍",
  notifications: "◔", metrics: "♥", commands: "◎",
};

const num = (v, digits = 1) =>
  v === null || v === undefined ? "—" : Number(v).toFixed(digits).replace(".", ",");

function timeAgo(iso) {
  if (!iso) return "";
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (Number.isNaN(min)) return "";
  if (min < 60) return "AGORA";
  const h = Math.round(min / 60);
  return h < 24 ? `HÁ ${h} H` : `HÁ ${Math.round(h / 24)} D`;
}

// Como no vídeo: temperatura e mínima/máxima/sensação à esquerda, chuva e vento numa coluna à direita
function WeatherBody({ c }) {
  return (
    <div className="bf-weather-body">
      <div className="bf-weather-left">
        <div className="bf-weather-main">
          <span className="bf-weather-icon" aria-hidden="true">{c.icon || "☀"}</span>
          <span className="bf-weather-temp">{num(c.temperature)}°</span>
          <span className="bf-weather-desc">{c.description}</span>
        </div>
        <dl className="bf-grid bf-grid-3">
          <div><dt>Mínima</dt><dd>{num(c.minimum)}°</dd></div>
          <div><dt>Máxima</dt><dd>{num(c.maximum)}°</dd></div>
          {c.apparent != null && <div><dt>Sensação</dt><dd>{num(c.apparent, 0)}°</dd></div>}
        </dl>
      </div>
      <dl className="bf-weather-side">
        <div><dt>☂ Chuva</dt><dd>{c.rain_probability ?? "—"}%</dd></div>
        {c.wind != null && <div><dt>≋ Vento</dt><dd>{num(c.wind)} km/h</dd></div>}
      </dl>
      {/* V5.3: conselho prático (guarda-chuva, calor, frio, trovoada) */}
      {c.tip && <p className="bf-tip">{c.tip}</p>}
    </div>
  );
}

function AgendaBody({ c }) {
  if (!c.items?.length) {
    return (
      <div className="bf-empty">
        <strong>{c.empty_text}</strong>
        <small>{c.empty_sub}</small>
      </div>
    );
  }
  return (
    <ul className="bf-list">
      {/* V5.3: o próximo compromisso de hoje, se for nas próximas 2 horas */}
      {c.next_in != null && <li className="bf-next"><span className="bf-chip is-warn">PRÓXIMO EM {c.next_in < 60 ? `${c.next_in} MIN` : `${Math.floor(c.next_in / 60)}H${String(c.next_in % 60).padStart(2, "0")}`}</span></li>}
      {c.items.map((it, i) => (
        <li key={i}>
          <span className="bf-num">{it.time}</span>
          <span className="bf-li-text">
            <b>{it.title}</b>
            {it.location && <small>{it.location}</small>}
          </span>
        </li>
      ))}
      {c.more > 0 && <li className="bf-more">+{c.more} outros</li>}
    </ul>
  );
}

function EmailBody({ c }) {
  if (!c.connected) {
    return (
      <div className="bf-empty">
        <strong>Triagem desligada</strong>
        <small>Preencha EMAIL_IMAP_HOST, EMAIL_IMAP_USER e EMAIL_IMAP_PASSWORD no .env.</small>
      </div>
    );
  }
  return (
    <>
      <div className="bf-chips">
        <span className="bf-chip">{c.received} recebidos</span>
        <span className={`bf-chip${c.to_act ? " is-warn" : ""}`}>{c.to_act} para agir</span>
      </div>
      {c.items?.length > 0 && (
        <ul className="bf-list">
          {c.items.map((it, i) => (
            <li key={i}>
              <span className="bf-num">{String(i + 1).padStart(2, "0")}</span>
              <span className="bf-li-text">
                <b>{it.sender}</b>
                <small>{it.summary}</small>
              </span>
            </li>
          ))}
          {c.more > 0 && <li className="bf-more">+{c.more} outras mensagens</li>}
        </ul>
      )}
    </>
  );
}

function NewsBody({ c }) {
  // V6.2: tema com várias manchetes (ex.: Marvel, as 3 principais): lista numerada
  if (c.items?.length > 1) {
    return (
      <ol className="bf-news-list">
        {c.items.map((it, i) => (
          <li key={i}>
            <span className="bf-num">{String(i + 1).padStart(2, "0")}</span>
            <span className="bf-li-text">
              <b>{it.title}</b>
              {it.source && <small>{it.source}</small>}
            </span>
          </li>
        ))}
      </ol>
    );
  }
  const logo = c.domain ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(c.domain)}&sz=128` : "";
  return (
    <>
      <div className="bf-news-media">
        {logo ? (
          <img src={logo} alt="" loading="lazy" onError={(e) => { e.currentTarget.style.display = "none"; }} />
        ) : null}
        <span className="bf-news-mono">{(c.source || "N").slice(0, 1)}</span>
        <span className="bf-badge">{timeAgo(c.published) || "AGORA"}</span>
      </div>
      <p className="bf-headline">{c.headline}</p>
      <div className="bf-news-foot">
        <small>{c.source}</small>
        {c.link && (
          <a className="bf-link" href={c.link} target="_blank" rel="noopener noreferrer">
            Abrir matéria ↗
          </a>
        )}
      </div>
    </>
  );
}

function HealthBody({ c }) {
  return (
    <>
      <div className="bf-chips"><span className="bf-chip">{c.chip}</span></div>
      <p className="bf-text">{c.text}</p>
    </>
  );
}

function TasksBody({ c }) {
  if (!c.items?.length) return <AgendaBody c={c} />;
  return (
    <ul className="bf-list">
      {c.items.map((it, i) => (
        <li key={i}>
          <span className="bf-num">{String(i + 1).padStart(2, "0")}</span>
          <span className="bf-li-text"><b>{it.text}</b></span>
        </li>
      ))}
      {c.more > 0 && <li className="bf-more">+{c.more} outras</li>}
    </ul>
  );
}

function WaterBody({ c }) {
  const pct = Math.max(0, Math.min(100, Number(c.percentage) || 0));
  return (
    <>
      <div className="bf-chips">
        <span className={`bf-chip${c.goal_reached ? "" : " is-warn"}`}>
          {c.goal_reached ? "meta batida" : `${pct}% da meta`}
        </span>
      </div>
      <span className="bf-bar is-static"><i style={{ width: `${pct}%` }} /></span>
    </>
  );
}

function NotificationsBody({ c }) {
  if (!c.items?.length) return <AgendaBody c={c} />;
  return (
    <>
      {c.count > 0 && <div className="bf-chips"><span className="bf-chip">{c.count} notificaç{c.count === 1 ? "ão" : "ões"}</span></div>}
      <ul className="bf-list">
        {c.items.map((it, i) => (
          <li key={i}>
            <span className="bf-num">{String(i + 1).padStart(2, "0")}</span>
            <span className="bf-li-text">
              <b>{it.title || "(sem título)"}</b>
              {it.body && <small>{it.body}</small>}
            </span>
          </li>
        ))}
        {c.more > 0 && <li className="bf-more">+{c.more} outras</li>}
      </ul>
    </>
  );
}

function MetricsBody({ c }) {
  return (
    <dl className="bf-grid">
      {(c.items || []).map((m) => (
        <div key={m.label}><dt>{m.label}</dt><dd>{m.value}</dd></div>
      ))}
    </dl>
  );
}

function CommandsBody({ c }) {
  return (
    <ul className="bf-list">
      {(c.items || []).map((it) => (
        <li key={it.say}>
          <span className="bf-say">"{it.say}"</span>
          <span className="bf-li-text"><small>{it.does}</small></span>
        </li>
      ))}
    </ul>
  );
}

const BODIES = {
  weather: WeatherBody, agenda: AgendaBody, email: EmailBody, news: NewsBody, health: HealthBody,
  tasks: TasksBody, water: WaterBody, notifications: NotificationsBody, metrics: MetricsBody,
  commands: CommandsBody,
};

/**
 * compact: só rótulo e título (Canal Ativo). mini: card pequeno de altura fixa (fileiras).
 * wide: card largo em destaque, o assunto falado agora (como no vídeo).
 */
export default function BriefingCard({ card, compact = false, mini = false, wide = false, entering = false }) {
  if (!card || !BODIES[card.kind]) return null;
  const Body = BODIES[card.kind];
  const size = compact ? " is-compact" : mini ? " is-mini" : wide ? " is-wide" : "";
  return (
    <article className={`bf-card bf-${card.kind}${size}${entering ? " is-entering" : ""}`}>
      <header className="bf-card-head">
        <span className="bf-icon" aria-hidden="true">{card.badge || ICONS[card.kind]}</span>
        <span className="bf-label">{card.label}</span>
      </header>
      <h3 className="bf-title">{card.title}</h3>
      {!compact && <Body c={card} />}
      {card.footer && <footer className="bf-foot">{card.footer}</footer>}
    </article>
  );
}

export function ReadinessPanel({ data }) {
  if (!data) return null;
  const pct = Math.max(0, Math.min(100, Number(data.recovery) || 0));
  return (
    <aside className="bf-readiness" aria-label="Prontidão fisiológica">
      <span className="bf-label">PRONTIDÃO FISIOLÓGICA</span>
      <div className="bf-ring" style={{ "--pct": pct }}>
        <strong>{pct}%</strong>
        <small>Recuperação do dia</small>
      </div>
      <dl className="bf-grid">
        {data.metrics.map((m) => (
          <div key={m.label}><dt>{m.label}</dt><dd>{m.value}</dd></div>
        ))}
      </dl>
      {data.footer && <footer className="bf-foot">{data.footer}</footer>}
    </aside>
  );
}
