"""Configurações centrais do JARVIS, lidas do arquivo .env na raiz do projeto."""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/config/settings.py -> raiz do projeto (jarvis_assistant/)
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

# Pasta para dados locais (foto de perfil, etc.). Fica fora de backend/ para não disparar o --reload.
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Pasta para logs com rotação
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "jarvis.log"

# --- Modo de rede e Autenticação ---
NETWORK_MODE = os.getenv("JARVIS_NETWORK_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
ACCESS_TOKEN_FILE = DATA_DIR / "access_token.txt"

# --- IA (LLM multimodal) ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()  # "openai" | "anthropic" | "gemini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_SEARCH_GROUNDING = os.getenv("GEMINI_SEARCH_GROUNDING", "true").strip().lower() in {"1", "true", "yes", "on"}
# "none" desliga o "raciocínio" do Gemini (respostas bem mais rápidas). Deixe vazio para desativar.
GEMINI_REASONING = os.getenv("GEMINI_REASONING", "none").strip()
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1000"))

# --- Voz ---
TTS_VOICE = os.getenv("TTS_VOICE", "pt-BR-AntonioNeural")
TTS_RATE = os.getenv("TTS_RATE", "+0%")

# --- Câmera ---
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

# --- Reconhecimento facial ---
FACE_THRESHOLD = float(os.getenv("FACE_THRESHOLD", "0.363"))  # similaridade mínima (cosseno)
FACE_TIMEOUT = float(os.getenv("FACE_TIMEOUT", "8"))          # segundos tentando reconhecer
# Câmera ao vivo durante a verificação (seção 16): limite de quadros, largura e qualidade do JPEG
FACE_STREAM_FPS = float(os.getenv("FACE_STREAM_FPS", "15"))  # vídeo e análise separados: 15 fps sem travar (4.2: era 10)
FACE_STREAM_WIDTH = int(os.getenv("FACE_STREAM_WIDTH", "400"))  # 4.2: era 480
FACE_STREAM_QUALITY = int(os.getenv("FACE_STREAM_QUALITY", "65"))  # 4.2: era 70

# --- Avisos falados enquanto processa ("só um minutinho...") ---
FILLER_FIRST_DELAY = float(os.getenv("FILLER_FIRST_DELAY", "4"))  # 0 = desligado
FILLER_INTERVAL = float(os.getenv("FILLER_INTERVAL", "20"))

# --- Notícias (Google News Brasil via RSS) ---
NEWS_RSS_URL = os.getenv(
    "NEWS_RSS_URL",
    "https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419",
)
NEWS_LIMIT = int(os.getenv("NEWS_LIMIT", "3"))

# --- Clima (cidade padrão quando você não disser uma) ---
WEATHER_CITY = os.getenv("WEATHER_CITY", "São Paulo").strip()

# --- Personalização (usado se nenhum nome for cadastrado no perfil) ---
USER_NAME = os.getenv("USER_NAME", "").strip()

# --- CORS: só a central (local ou a publicada no site) pode chamar o backend (ele controla webcam e voz) ---
# O site (botão "Abrir meu JARVIS") serve a mesma central em /app/, que fala com este backend em 127.0.0.1.
# Pedidos vindos de outra máquina continuam barrados pelo middleware de segurança (modo rede + token).
SITE_ORIGIN = os.getenv("JARVIS_SITE_ORIGIN", "https://projeto-jarvis-ia.netlify.app").strip()
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"] + ([SITE_ORIGIN] if SITE_ORIGIN else []) + [
    o.strip() for o in os.getenv("EXTRA_CORS_ORIGINS", "").split(",") if o.strip()
]

# --- Google Calendar OAuth 2.0 ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://127.0.0.1:8000/api/integrations/google-calendar/callback",
).strip()

# --- V4.3: triagem de e-mail no briefing (IMAP, somente leitura) ---
# Gmail: imap.gmail.com + "senha de app" (Conta Google > Segurança > Senhas de app). Vazio = desligado.
EMAIL_IMAP_HOST = os.getenv("EMAIL_IMAP_HOST", "").strip()
EMAIL_IMAP_USER = os.getenv("EMAIL_IMAP_USER", "").strip()
EMAIL_IMAP_PASSWORD = os.getenv("EMAIL_IMAP_PASSWORD", "").strip()
EMAIL_LOOKBACK_HOURS = int(os.getenv("EMAIL_LOOKBACK_HOURS", "24"))

# --- Spotify OAuth 2.0 ---
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
SPOTIFY_REDIRECT_URI = os.getenv(
    "SPOTIFY_REDIRECT_URI",
    "http://127.0.0.1:8000/api/integrations/spotify/callback",
).strip()
