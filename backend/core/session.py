"""Estado mutável da conversa (ocupado, turno atual, histórico). Acesse sempre como session.<nome>."""

import asyncio


busy = False  # impede duas solicitações simultâneas (câmera e voz são únicas)


auth_lock = asyncio.Lock()  # impede chamadas simultâneas à webcam sem travar a autenticação


turn_id = 0  # sobe a cada cancelamento: respostas "velhas" (de antes do cancelar) são descartadas


current_stop: asyncio.Event | None = None  # para os avisos "só um minutinho"


history: list[dict] = []


pending_deep_search_query: str | None = None


last_search_query: str = ""


speaking = 0  # quantas falas estão tocando agora (usado pela música de abertura)


pending_action: dict | None = None  # 4.2: ação esperando "sim" (sugestão da rotina, organizar pasta)
