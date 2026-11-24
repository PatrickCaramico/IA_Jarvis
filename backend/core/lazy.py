"""V9.4.1: importação preguiçosa das bibliotecas pesadas (OpenCV, numpy, pygame).

Antes: o backend importava o OpenCV (câmera e rosto) e o pygame (som) antes de abrir a porta 8000. Com o cache do
disco frio (logo depois de ligar o PC, com o antivírus examinando cada arquivo), só isso levava de 5 a dezenas de
segundos, e a central ficava em "RECONECTANDO AO SEU JARVIS" esse tempo todo sem ninguém precisar de câmera ou som.

Agora o módulo usa `cv2 = LazyModule("cv2")` no lugar de `import cv2`: o nome existe desde o começo, mas a
biblioteca só é carregada no primeiro uso (`cv2.imdecode(...)`) ou pelo `warm()`, que o main chama em segundo
plano logo depois que o servidor já está respondendo.
"""
from __future__ import annotations

import importlib
import threading
from types import ModuleType
from typing import Any


class LazyModule:
    """Um módulo que só é importado no primeiro acesso a um atributo."""

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_module", None)
        object.__setattr__(self, "_lock", threading.Lock())

    def _load(self) -> ModuleType:
        module = object.__getattribute__(self, "_module")
        if module is None:
            with object.__getattribute__(self, "_lock"):
                module = object.__getattribute__(self, "_module")
                if module is None:
                    module = importlib.import_module(object.__getattribute__(self, "_name"))
                    object.__setattr__(self, "_module", module)
        return module

    @property
    def loaded(self) -> bool:
        return object.__getattribute__(self, "_module") is not None

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._load(), attr)

    def __repr__(self) -> str:
        state = "carregado" if self.loaded else "ainda não carregado"
        return f"<LazyModule {object.__getattribute__(self, '_name')} ({state})>"


def warm(*modules: LazyModule) -> None:
    """Carrega agora (numa thread, pelo chamador) para o primeiro uso de verdade não esperar."""
    for m in modules:
        m._load()  # noqa: SLF001
