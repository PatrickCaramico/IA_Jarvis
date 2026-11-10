import { Suspense, lazy } from "react";

// Carrega um componente só quando ele aparece pela primeira vez (otimização 4.2).
// Telas e janelas pouco usadas (Configurações, modais, monitores) saem do pacote inicial,
// então a central abre mais rápido. Cada uma tem o seu próprio Suspense: enquanto o código
// chega (milissegundos, é local), só aquele pedaço fica vazio, nunca a tela inteira.
export default function lazyComponent(load) {
  const Lazy = lazy(load);
  function LazyComponent(props) {
    return (
      <Suspense fallback={null}>
        <Lazy {...props} />
      </Suspense>
    );
  }
  return LazyComponent;
}
