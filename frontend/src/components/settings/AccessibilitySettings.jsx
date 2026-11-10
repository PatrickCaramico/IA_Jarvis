import { Note, Section, SelectRow, Toggle } from "./SettingsControls.jsx";

// V4.5: Acessibilidade. Cada mudança é salva na hora e vale em todas as telas (inclusive no bloqueio).
export default function AccessibilitySettings({ prefs, onPatch }) {
  return (
    <div className="space-y-3">
      <Section title="LEITURA">
        <SelectRow
          label="TAMANHO DO TEXTO"
          value={String(prefs.a11y_text_scale ?? 100)}
          onChange={(v) => onPatch({ a11y_text_scale: Number(v) })}
          options={[["100", "Normal"], ["115", "Grande (115%)"], ["130", "Maior (130%)"]]}
        />
        <Toggle
          label="ALTO CONTRASTE"
          hint="Painéis bem mais escuros, bordas brancas e nenhum texto apagado. A planta azul fica mais escura."
          checked={prefs.a11y_high_contrast}
          onChange={(v) => onPatch({ a11y_high_contrast: v })}
        />
      </Section>

      <Section title="MOVIMENTO">
        <Toggle
          label="REDUZIR MOVIMENTO"
          hint="Para de girar o orbe, o brilho da planta e as comemorações animadas. Vale mesmo se o Windows não estiver com essa opção."
          checked={prefs.a11y_reduce_motion}
          onChange={(v) => onPatch({ a11y_reduce_motion: v })}
        />
      </Section>

      <Section title="TECLADO E VOZ">
        <Note>
          Tudo abre pelo teclado: Tab passa pelos botões (com um contorno amarelo bem visível), Espaço libera o
          bloqueio e P liga/desliga o microfone. O estado do JARVIS sempre aparece também em texto, não só na cor.
          Para respostas só em texto, ligue o modo silencioso na aba Geral.
        </Note>
      </Section>
    </div>
  );
}
