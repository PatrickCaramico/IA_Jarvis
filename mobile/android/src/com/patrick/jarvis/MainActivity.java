package com.patrick.jarvis;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.Color;
import android.graphics.drawable.Icon;
import android.hardware.biometrics.BiometricPrompt;
import android.os.CancellationSignal;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import org.json.JSONObject;

import java.util.ArrayList;

/**
 * JARVIS para Android (V4.5).
 *
 * Mostra a central do JARVIS que roda no PC (modo rede, mesma Wi-Fi) em tela cheia. O endereço
 * (com a chave de acesso) chega pelo pareamento: a página do PC abre jarvis://connect?url=...
 * Também: avisos no celular (NotifyService) e microfone nativo do Android para falar com a central
 * (o WebView não tem o reconhecimento de voz do Chrome).
 */
public class MainActivity extends Activity {
    private static final String PREFS = "jarvis";
    private static final String KEY_URL = "url";
    private static final String SETUP = "file:///android_asset/setup.html";
    private static final int REQ_MIC = 7;
    private static final int REQ_NOTIFY = 8;
    private static final int REQ_MIC_SPEECH = 9;

    static volatile boolean visible = false;
    // V5.1.1: atualização automática (o app baixa o APK do PC e se instala pelo PackageInstaller)
    static volatile boolean updateInProgress = false;
    // V6.5.7: a tela viva (o InstallReceiver pede para ELA abrir a confirmação da instalação)
    private static java.lang.ref.WeakReference<MainActivity> live = new java.lang.ref.WeakReference<>(null);

    static MainActivity current() {
        return live.get();
    }

    /** Abre a tela "Atualizar o JARVIS?" do Android a partir da tela que está na frente. */
    void openInstallConfirm(Intent confirm) {
        runOnUiThread(() -> {
            try {
                startActivity(confirm);
                reportUpdate(true, "confirm", "Toque em Atualizar na janela do Android.");
            } catch (Exception e) {
                reportUpdate(true, "confirm", "Toque no aviso \"Concluir atualização do JARVIS\" para terminar.");
            }
        });
    }

    /** Fim da instalação (falhou ou foi cancelada): a barra some e o botão volta a funcionar. */
    void updateFinished(boolean ok, String message) {
        retryHandler.removeCallbacks(updateWatchdog);
        updateInProgress = false;
        reportUpdate(true, ok ? "latest" : "error", message);
    }

    // Se nada acontecer em 2 minutos (confirmação nunca apareceu), destrava o botão
    private final Runnable updateWatchdog = () -> {
        if (!updateInProgress) return;
        updateInProgress = false;
        reportUpdate(true, "error", "A instalação não terminou. Toque no aviso \"Concluir atualização do JARVIS\" ou em ATUALIZAR APP de novo.");
    };
    private volatile long lastUpdateCheck = 0;
    private volatile String pendingUpdateHost = null; // esperando a permissão "instalar apps"

    private WebView web;
    private SharedPreferences prefs;
    private PermissionRequest pendingPermission;
    private volatile String currentUrl = "";
    private SpeechRecognizer recognizer;

    // V5.2: PC fora do ar com o celular já pareado: tenta de novo sozinho (3 s, 5 s, 8 s… até 30 s),
    // na hora em que a Wi-Fi volta e quando o app volta para a frente. Não pede o PIN de novo.
    private static final int[] RETRY_SECONDS = {3, 5, 8, 12, 20, 30};
    private final Handler retryHandler = new Handler(Looper.getMainLooper());
    private final Runnable retryRunnable = this::retrySaved;
    private int retryAttempt = 0;
    private volatile boolean mainFrameFailed = false;
    private boolean offlineScreen = false;
    private ConnectivityManager.NetworkCallback networkCallback;
    private long pausedAt = 0; // V6.4: para avisar a rede só quando o app é "aberto" de novo

    // V6.0: acesso fora de casa (Tailscale): endereço do PC que o PC informa em /api/mobile/info
    private static final String KEY_REMOTE = "remote_host";
    // V6.0: chave do aparelho para entrar com a digital (o PC guarda só o hash)
    private static final String KEY_DEVICE_SECRET = "device_secret";
    // V6.0: comandos para a central (atalhos, botão da cortina, compartilhar) esperando a página abrir
    private final ArrayList<String> pendingJs = new ArrayList<>();
    private volatile boolean pageReady = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        live = new java.lang.ref.WeakReference<>(this);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        NotifyService.createChannels(this);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setStatusBarColor(Color.parseColor("#0D3170"));
        getWindow().setNavigationBarColor(Color.parseColor("#0D3170"));

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#174A95"));
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        s.setUserAgentString(s.getUserAgentString() + " JarvisApp/" + installedVersion());
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setTextZoom(100); // o tamanho do texto é controlado pela acessibilidade do JARVIS

        web.addJavascriptInterface(new Bridge(), "JarvisApp");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                currentUrl = url;
                pageReady = false;
                if (isHttp(url)) mainFrameFailed = false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                // A central do PC abriu de verdade: zera as tentativas
                if (isHttp(url) && !mainFrameFailed) {
                    retryAttempt = 0;
                    offlineScreen = false;
                    retryHandler.removeCallbacks(retryRunnable);
                    pageReady = true;
                    // a central (React) precisa de um instante para montar antes de receber comandos
                    retryHandler.postDelayed(MainActivity.this::flushJs, 1800);
                }
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if ("jarvis".equals(uri.getScheme())) {
                    handleUri(uri);
                    return true;
                }
                if (sameHost(uri) || "file".equals(uri.getScheme())) return false;
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri)); // links de fora no navegador
                } catch (Exception ignored) {
                }
                return true;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame() && !request.getUrl().toString().startsWith(SETUP)) {
                    mainFrameFailed = true;
                    // V6.0: a Wi-Fi de casa não respondeu: tenta o endereço do Tailscale antes de "reconectando"
                    Uri saved0 = savedUri();
                    String remote = prefs.getString(KEY_REMOTE, "");
                    String failedHost = request.getUrl().getHost();
                    if (saved0 != null && !remote.isEmpty() && failedHost != null && failedHost.equals(saved0.getHost())) {
                        int port = saved0.getPort();
                        view.loadUrl(saved0.buildUpon().encodedAuthority(remote + (port > 0 ? ":" + port : "")).build().toString());
                        return;
                    }
                    String h = savedHostValue();
                    if (savedUri() != null) {
                        // Já pareado: tela "reconectando" e nova tentativa sozinha
                        int wait = RETRY_SECONDS[Math.min(retryAttempt, RETRY_SECONDS.length - 1)];
                        retryAttempt++;
                        offlineScreen = true;
                        view.loadUrl(SETUP + "#offline&wait=" + wait + "&n=" + retryAttempt + (h.isEmpty() ? "" : "&host=" + h));
                        retryHandler.removeCallbacks(retryRunnable);
                        retryHandler.postDelayed(retryRunnable, wait * 1000L);
                    } else {
                        view.loadUrl(SETUP + "#erro" + (h.isEmpty() ? "" : "&host=" + h));
                    }
                }
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> {
                    if (hasMic()) {
                        request.grant(request.getResources());
                    } else {
                        pendingPermission = request;
                        requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_MIC);
                    }
                });
            }
        });

        if (!handleIntent(getIntent())) loadSavedOrSetup();
        if (savedUri() != null && prefs.getBoolean(NotifyService.KEY_ENABLED, true)) enableNotifications(false);
        watchNetwork();
        setupShortcuts();
    }

    // ------------------------------------------------------------------ V6.0: atalhos e comandos
    /** Toque longo no ícone: Falar com o JARVIS, Bom dia, Lista de compras. */
    private void setupShortcuts() {
        if (Build.VERSION.SDK_INT < 25) return;
        try {
            ShortcutManager sm = getSystemService(ShortcutManager.class);
            if (sm == null) return;
            ArrayList<ShortcutInfo> list = new ArrayList<>();
            list.add(shortcut("falar", "Falar com o JARVIS", "jarvis://listen"));
            list.add(shortcut("bomdia", "Bom dia", "jarvis://say?text=" + Uri.encode("bom dia")));
            list.add(shortcut("lista", "Lista de compras", "jarvis://say?text=" + Uri.encode("o que tem na lista de compras")));
            sm.setDynamicShortcuts(list);
        } catch (Exception ignored) {
            // atalhos são extra: sem eles o app funciona igual
        }
    }

    /** V6.5.5: põe um comando ("bom dia", "notícias"...) como ícone na tela inicial. O Android confirma. */
    private boolean pinCommand(String label, String text) {
        if (Build.VERSION.SDK_INT < 26 || label == null || text == null) return false;
        String l = label.trim();
        String t = text.trim();
        if (l.isEmpty() || t.isEmpty() || l.length() > 24 || t.length() > 120) return false;
        try {
            ShortcutManager sm = getSystemService(ShortcutManager.class);
            if (sm == null || !sm.isRequestPinShortcutSupported()) return false;
            String id = "cmd_" + Integer.toHexString(t.toLowerCase().hashCode());
            // "notícias" abre a janela de notícias; os outros rodam o comando como se fosse falado
            String uri = "notícias".equals(t) ? "jarvis://news" : "jarvis://say?text=" + Uri.encode(t);
            return sm.requestPinShortcut(shortcut(id, l, uri), null);
        } catch (Exception e) {
            return false;
        }
    }

    private boolean canPinCommands() {
        if (Build.VERSION.SDK_INT < 26) return false;
        try {
            ShortcutManager sm = getSystemService(ShortcutManager.class);
            return sm != null && sm.isRequestPinShortcutSupported();
        } catch (Exception e) {
            return false;
        }
    }

    private ShortcutInfo shortcut(String id, String label, String uri) {
        Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(uri)).setPackage(getPackageName());
        return new ShortcutInfo.Builder(this, id).setShortLabel(label).setLongLabel(label)
                .setIcon(Icon.createWithResource(this, R.mipmap.ic_launcher)).setIntent(i).build();
    }

    /** Roda um comando na central assim que ela estiver aberta (abre a central se precisar). */
    private void queueJs(String js) {
        synchronized (pendingJs) {
            pendingJs.add(js);
        }
        if (pageReady && isHttp(currentUrl) && sameHost(Uri.parse(currentUrl))) {
            runOnUiThread(this::flushJs);
        }
    }

    private void flushJs() {
        if (!pageReady) return;
        ArrayList<String> now;
        synchronized (pendingJs) {
            now = new ArrayList<>(pendingJs);
            pendingJs.clear();
        }
        for (String js : now) web.evaluateJavascript(js, null);
    }

    private static String event(String name, JSONObject detail) {
        return "window.dispatchEvent(new CustomEvent('" + name + "',{detail:" + (detail == null ? "{}" : detail.toString()) + "}))";
    }

    // ------------------------------------------------------------------ V6.0: digital (biometria do Android)
    private boolean biometricAvailable() {
        if (Build.VERSION.SDK_INT < 28) return false;
        if (Build.VERSION.SDK_INT >= 29) {
            try {
                android.hardware.biometrics.BiometricManager bm = getSystemService(android.hardware.biometrics.BiometricManager.class);
                return bm != null && bm.canAuthenticate() == android.hardware.biometrics.BiometricManager.BIOMETRIC_SUCCESS;
            } catch (Exception e) {
                return false;
            }
        }
        return getPackageManager().hasSystemFeature(PackageManager.FEATURE_FINGERPRINT);
    }

    /** Pede a digital; ok=true roda onSuccess, senão avisa a central (jarvis-app-biometric, action=error). */
    private void askBiometric(String title, String subtitle, Runnable onSuccess) {
        if (Build.VERSION.SDK_INT < 28) return;
        try {
            BiometricPrompt prompt = new BiometricPrompt.Builder(this)
                    .setTitle(title)
                    .setSubtitle(subtitle)
                    .setNegativeButton("Usar PIN", getMainExecutor(), (dialog, which) -> sendBiometric("cancel", null, null))
                    .build();
            prompt.authenticate(new CancellationSignal(), getMainExecutor(), new BiometricPrompt.AuthenticationCallback() {
                @Override
                public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result) {
                    onSuccess.run();
                }

                @Override
                public void onAuthenticationError(int code, CharSequence msg) {
                    sendBiometric("error", null, msg == null ? "" : msg.toString());
                }
            });
        } catch (Exception e) {
            sendBiometric("error", null, "A digital não está disponível neste celular.");
        }
    }

    private void sendBiometric(String action, String secret, String message) {
        try {
            JSONObject d = new JSONObject().put("action", action);
            if (secret != null) d.put("secret", secret);
            if (message != null) d.put("message", message);
            String js = event("jarvis-app-biometric", d);
            runOnUiThread(() -> web.evaluateJavascript(js, null));
        } catch (Exception ignored) {
        }
    }

    // ------------------------------------------------------------------ reconexão (V5.2)
    /** Nova tentativa com o endereço salvo, só se a tela "reconectando" estiver aberta. */
    private void retrySaved() {
        retryHandler.removeCallbacks(retryRunnable);
        if (!offlineScreen || savedUri() == null) return;
        web.loadUrl(prefs.getString(KEY_URL, ""));
    }

    /** Wi-Fi voltou (ou trocou de rede): tenta na hora em vez de esperar o próximo intervalo. */
    private void watchNetwork() {
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            if (cm == null) return;
            networkCallback = new ConnectivityManager.NetworkCallback() {
                @Override
                public void onCapabilitiesChanged(Network network, NetworkCapabilities caps) {
                    netCheckSoon(); // V6.4: trocou Wi-Fi <-> dados móveis
                }

                @Override
                public void onLost(Network network) {
                    netCheckSoon();
                }

                @Override
                public void onAvailable(Network network) {
                    netCheckSoon();
                    retryHandler.postDelayed(() -> {
                        if (offlineScreen) {
                            retryAttempt = 0;
                            retrySaved();
                        }
                    }, 1500); // dá tempo de a rede pegar o IP
                }
            };
            cm.registerDefaultNetworkCallback(networkCallback);
        } catch (Exception ignored) {
            // sem permissão ou aparelho antigo: as tentativas por tempo continuam valendo
        }
    }

    // ------------------------------------------------------------------ V6.4: Wi-Fi ou dados móveis
    private String lastNetEmitted = null;
    private final Runnable netCheck = () -> {
        String now = currentNetType();
        if (now.equals(lastNetEmitted)) return;
        lastNetEmitted = now;
        emitNetwork("change");
    };

    /** Espera a rede assentar (a troca dispara vários avisos seguidos) e confere uma vez só. */
    private void netCheckSoon() {
        retryHandler.removeCallbacks(netCheck);
        retryHandler.postDelayed(netCheck, 2500);
    }

    /** "wifi", "cellular", "ethernet", "none" ou "other". Com VPN (Tailscale), olha a rede por baixo dela. */
    private String currentNetType() {
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            if (cm == null) return "other";
            String t = netTypeOf(cm.getNetworkCapabilities(cm.getActiveNetwork()));
            if (!"vpn".equals(t)) return t;
            String best = "other";
            for (Network n : cm.getAllNetworks()) {
                String u = netTypeOf(cm.getNetworkCapabilities(n));
                if ("wifi".equals(u) || "ethernet".equals(u)) return u;
                if ("cellular".equals(u)) best = u;
            }
            return best;
        } catch (Exception e) {
            return "other";
        }
    }

    private static String netTypeOf(NetworkCapabilities c) {
        if (c == null) return "none";
        if (c.hasTransport(NetworkCapabilities.TRANSPORT_VPN)) return "vpn";
        if (c.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) return "wifi";
        if (c.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)) return "ethernet";
        if (c.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) return "cellular";
        return "other";
    }

    private void emitNetwork(String reason) {
        try {
            String js = event("jarvis-app-network", new JSONObject().put("reason", reason).put("type", currentNetType()));
            runOnUiThread(() -> web.evaluateJavascript(js, null));
        } catch (Exception ignored) {
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        visible = true;
        // V6.4: abriu o app de novo: a central confere a rede (avisa dados móveis ou a troca de rede)
        if (pausedAt > 0 && System.currentTimeMillis() - pausedAt > 60_000L) emitNetwork("open");
        // V5.2: voltou para o app com a tela "reconectando": tenta na hora
        if (offlineScreen) {
            retryAttempt = 0;
            retrySaved();
        }
        // V5.1.1: voltou da tela "permitir instalar apps" ou reabriu o app: confere de novo se há versão nova
        String url = prefs.getString(KEY_URL, "");
        if (isHttp(url) && System.currentTimeMillis() - lastUpdateCheck > (pendingUpdateHost != null ? 0 : 30 * 60 * 1000L)) {
            checkForUpdate(url);
        }
    }

    @Override
    protected void onPause() {
        visible = false;
        pausedAt = System.currentTimeMillis();
        super.onPause();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    private boolean handleIntent(Intent intent) {
        if (intent == null) return false;
        // V6.0: "Compartilhar -> JARVIS" de qualquer app (texto ou link)
        if (Intent.ACTION_SEND.equals(intent.getAction())) {
            String text = intent.getStringExtra(Intent.EXTRA_TEXT);
            if (text != null && !text.trim().isEmpty() && savedUri() != null) {
                try {
                    String subject = intent.getStringExtra(Intent.EXTRA_SUBJECT);
                    JSONObject d = new JSONObject().put("text", text.trim()).put("subject", subject == null ? "" : subject);
                    queueJs(event("jarvis-app-share", d));
                } catch (Exception ignored) {
                }
            }
            setIntent(new Intent(this, MainActivity.class)); // não repete ao girar a tela
            return false;
        }
        if (intent.getData() == null) return false;
        return handleUri(intent.getData());
    }

    /** jarvis://connect?url=http://IP:5173/?token=...  |  jarvis://open */
    private boolean handleUri(Uri uri) {
        if (!"jarvis".equals(uri.getScheme())) return false;
        // V6.0: atalhos do ícone e botão da cortina
        if ("listen".equals(uri.getHost()) && savedUri() != null) {
            queueJs(event("jarvis-app-listen", null));
            if (!isHttp(currentUrl)) loadSavedOrSetup();
            return true;
        }
        // V6.5: tocou no aviso de notícia: abre a janela de notícias
        if ("news".equals(uri.getHost()) && savedUri() != null) {
            queueJs(event("jarvis-open-news", null));
            if (!isHttp(currentUrl)) loadSavedOrSetup();
            return true;
        }
        if ("say".equals(uri.getHost()) && savedUri() != null) {
            String text = uri.getQueryParameter("text");
            if (text != null && !text.trim().isEmpty() && text.length() <= 300) {
                try {
                    queueJs(event("jarvis-app-say", new JSONObject().put("text", text.trim())));
                } catch (Exception ignored) {
                }
            }
            if (!isHttp(currentUrl)) loadSavedOrSetup();
            return true;
        }
        if ("connect".equals(uri.getHost())) {
            String url = uri.getQueryParameter("url");
            if (isHttp(url)) {
                connect(url);
                return true;
            }
        }
        // V5.1.1: jarvis://open?host=IP (QR do PC com o app já instalado): abre o JARVIS já pareado
        // (e ele se atualiza sozinho, se o PC tiver versão nova); sem pareamento, cai na tela do PIN.
        if ("open".equals(uri.getHost())) {
            String host = uri.getQueryParameter("host");
            Uri saved = savedUri();
            boolean validHost = host != null && host.matches("[\\w.-]+");
            if (saved != null && validHost && !host.equals(saved.getHost())) {
                // O roteador trocou o IP do PC: troca só o endereço, mantém a chave e reconecta
                int port = saved.getPort();
                connect(saved.buildUpon().encodedAuthority(host + (port > 0 ? ":" + port : "")).build().toString());
                Toast.makeText(this, "Endereço do PC atualizado para " + host + ".", Toast.LENGTH_SHORT).show();
            } else if (saved != null) {
                loadSavedOrSetup();
            } else {
                web.loadUrl(SETUP + (host != null && host.matches("[\\w.-]+") ? "#host=" + host : ""));
            }
            return true;
        }
        // V4.5: jarvis://setup?host=IP (botão "ABRIR O JARVIS" da página de download): pede só o PIN
        if ("setup".equals(uri.getHost())) {
            String host = uri.getQueryParameter("host");
            web.loadUrl(SETUP + (host != null && host.matches("[\\w.-]+") ? "#host=" + host : ""));
            return true;
        }
        loadSavedOrSetup();
        return true;
    }

    private String savedHostValue() {
        Uri u = savedUri();
        return u != null && u.getHost() != null ? u.getHost() : "";
    }

    /** POST http://host:8000/api/mobile/pair-pin {pin} -> {url}. Roda fora da tela (rede). */
    private void pairWithPin(String host, String pin) {
        new Thread(() -> {
            String error;
            try {
                java.net.HttpURLConnection c = (java.net.HttpURLConnection)
                        new java.net.URL("http://" + host + ":8000/api/mobile/pair-pin").openConnection();
                c.setConnectTimeout(6000);
                c.setReadTimeout(10000);
                c.setRequestMethod("POST");
                c.setDoOutput(true);
                c.setRequestProperty("Content-Type", "application/json");
                byte[] body = new JSONObject().put("pin", pin).toString().getBytes("UTF-8");
                try (java.io.OutputStream os = c.getOutputStream()) { os.write(body); }
                int code = c.getResponseCode();
                java.io.InputStream in = code < 400 ? c.getInputStream() : c.getErrorStream();
                StringBuilder sb = new StringBuilder();
                if (in != null) {
                    try (java.io.BufferedReader r = new java.io.BufferedReader(new java.io.InputStreamReader(in, "UTF-8"))) {
                        String line;
                        while ((line = r.readLine()) != null) sb.append(line);
                    }
                }
                c.disconnect();
                JSONObject json = sb.length() > 0 ? new JSONObject(sb.toString()) : new JSONObject();
                if (code == 200 && isHttp(json.optString("url"))) {
                    String url = json.getString("url");
                    runOnUiThread(() -> connect(url));
                    return;
                }
                error = json.optString("detail", "O PC recusou a conexão (código " + code + ").");
            } catch (java.net.SocketTimeoutException | java.net.ConnectException e) {
                error = "Não achei o JARVIS em " + host + ". O PC está com o JARVIS aberto e na mesma Wi-Fi?";
            } catch (Exception e) {
                error = "Falha ao conectar: " + e.getMessage();
            }
            String msg = error;
            runOnUiThread(() -> {
                try {
                    web.evaluateJavascript("window.__pairResult && window.__pairResult(false, " + JSONObject.quote(msg) + ")", null);
                } catch (Exception ignored) {
                }
            });
        }).start();
    }

    private void connect(String url) {
        prefs.edit().putString(KEY_URL, url.trim()).putLong("notify_since", -1).apply();
        web.loadUrl(url.trim());
        enableNotifications(true);
        checkForUpdate(url.trim());
    }

    private String installedVersion() {
        try {
            String version = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
            return version == null ? "0.0.0" : version;
        } catch (PackageManager.NameNotFoundException ignored) {
            return "0.0.0";
        }
    }

    private static int compareVersions(String left, String right) {
        String[] leftParts = left.replaceFirst("^[vV]", "").split("[.+-]");
        String[] rightParts = right.replaceFirst("^[vV]", "").split("[.+-]");
        try {
            for (int index = 0; index < 3; index++) {
                int leftPart = index < leftParts.length ? Integer.parseInt(leftParts[index]) : 0;
                int rightPart = index < rightParts.length ? Integer.parseInt(rightParts[index]) : 0;
                if (leftPart != rightPart) return Integer.compare(leftPart, rightPart);
            }
        } catch (NumberFormatException ignored) {
            return 0;
        }
        return 0;
    }

    private void checkForUpdate(String appUrl) {
        checkForUpdate(appUrl, false);
    }

    /** V5.7.1: resposta do botão ATUALIZAR APP para a tela (latest | updating | error). */
    private void reportUpdate(boolean manual, String status, String message) {
        if (!manual) return;
        try {
            JSONObject d = new JSONObject().put("status", status).put("message", message).put("version", installedVersion());
            String js = "window.dispatchEvent(new CustomEvent('jarvis-app-update',{detail:" + d + "}))";
            runOnUiThread(() -> web.evaluateJavascript(js, null));
        } catch (Exception ignored) {
        }
    }

    /** V6.1: progresso do download da atualização (a tela de bloqueio desenha a barra 0–100%). */
    private void updateProgress(int pct, String message) {
        try {
            JSONObject d = new JSONObject().put("status", "downloading").put("pct", pct).put("message", message);
            String js = "window.dispatchEvent(new CustomEvent('jarvis-app-update',{detail:" + d + "}))";
            runOnUiThread(() -> web.evaluateJavascript(js, null));
        } catch (Exception ignored) {
        }
    }

    private void checkForUpdate(String appUrl, boolean manual) {
        Uri paired = Uri.parse(appUrl);
        String base = PcAddress.base(paired); // V6.5: Wi-Fi de casa ou túnel
        if (updateInProgress) {
            reportUpdate(manual, "updating", "A atualização já está em andamento.");
            return;
        }
        if (!isHttp(appUrl) || base == null) {
            reportUpdate(manual, "error", "Este celular ainda não está conectado a um PC.");
            return;
        }
        lastUpdateCheck = System.currentTimeMillis();

        new Thread(() -> {
            try {
                java.net.HttpURLConnection connection = (java.net.HttpURLConnection)
                        new java.net.URL(base + "/api/mobile/info").openConnection();
                connection.setConnectTimeout(5000);
                connection.setReadTimeout(7000);
                connection.setRequestMethod("GET");
                String token = paired.getQueryParameter("token");
                if (token != null && !token.isEmpty()) connection.setRequestProperty("X-Jarvis-Token", token);
                int status = connection.getResponseCode();
                if (status != 200) {
                    connection.disconnect();
                    reportUpdate(manual, "error", "O PC não respondeu agora. Tente de novo.");
                    return;
                }
                StringBuilder body = new StringBuilder();
                try (java.io.BufferedReader reader = new java.io.BufferedReader(
                        new java.io.InputStreamReader(connection.getInputStream(), "UTF-8"))) {
                    String line;
                    while ((line = reader.readLine()) != null) body.append(line);
                }
                connection.disconnect();
                JSONObject info = new JSONObject(body.toString());
                String remoteHost = info.optString("remote_host", "");
                if (remoteHost.matches("[\\w.-]+")) prefs.edit().putString(KEY_REMOTE, remoteHost).apply();
                String pcVersion = info.optString("version", "");
                String phoneVersion = installedVersion();
                if (info.optBoolean("available") && compareVersions(pcVersion, phoneVersion) > 0) {
                    reportUpdate(manual, "updating", "Atualizando o app para a versão " + pcVersion + "…");
                    String apkUrl = base + "/api/mobile/app.apk" + PcAddress.tokenQuery(paired);
                    runOnUiThread(() -> startSelfUpdate(apkUrl, pcVersion));
                } else {
                    pendingUpdateHost = null;
                    reportUpdate(manual, "latest", "O app já está na versão mais nova (" + phoneVersion + ").");
                }
            } catch (Exception e) {
                // Sem conexão ou sem APK novo: não interrompe a abertura do JARVIS.
                reportUpdate(manual, "error", "Não consegui falar com o PC agora. Confira a Wi-Fi.");
            }
        }, "jarvis-update-check").start();
    }

    /**
     * V5.1.1: atualização automática. O app baixa o APK novo do PC e se instala pelo PackageInstaller.
     * - Na primeira vez, o Android pede "permitir instalar apps" para o JARVIS (uma vez só) e confirma a troca.
     * - Android 12+: depois que o próprio JARVIS instalou uma versão, as próximas entram sem perguntar.
     */
    private void startSelfUpdate(String apkUrl, String pcVersion) {
        if (isFinishing() || updateInProgress) return;
        if (Build.VERSION.SDK_INT >= 26 && !getPackageManager().canRequestPackageInstalls()) {
            if (apkUrl.equals(pendingUpdateHost)) return; // já pediu a permissão nesta abertura
            pendingUpdateHost = apkUrl;
            new AlertDialog.Builder(this)
                    .setTitle("Atualizar o JARVIS sozinho")
                    .setMessage("O PC tem a versão " + pcVersion + ". Para o JARVIS se atualizar sozinho daqui para frente, "
                            + "permita uma vez \"instalar apps desconhecidos\" para ele.")
                    .setPositiveButton("Permitir", (d, w) -> {
                        try {
                            startActivity(new Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                                    Uri.parse("package:" + getPackageName())));
                        } catch (Exception e) {
                            downloadApk(apkUrl);
                        }
                    })
                    .setNegativeButton("Agora não", null)
                    .show();
            return;
        }
        pendingUpdateHost = null;
        updateInProgress = true;
        Toast.makeText(this, "Atualizando o JARVIS para a versão " + pcVersion + "…", Toast.LENGTH_LONG).show();
        new Thread(() -> {
            try {
                java.io.File apk = new java.io.File(getCacheDir(), "jarvis-update.apk");
                java.net.HttpURLConnection c = (java.net.HttpURLConnection)
                        new java.net.URL(apkUrl).openConnection();
                c.setConnectTimeout(8000);
                c.setReadTimeout(30000);
                if (c.getResponseCode() != 200) throw new java.io.IOException("HTTP " + c.getResponseCode());
                // V6.1: progresso real do download (0–100%) para a barra da tela de bloqueio
                long total = c.getContentLength();
                long done = 0;
                int lastPct = -1;
                updateProgress(0, "Baixando a versão " + pcVersion + "…");
                try (java.io.InputStream in = c.getInputStream();
                     java.io.OutputStream out = new java.io.FileOutputStream(apk)) {
                    byte[] buf = new byte[16384];
                    int n;
                    while ((n = in.read(buf)) > 0) {
                        out.write(buf, 0, n);
                        done += n;
                        if (total > 0) {
                            int pct = (int) Math.min(99, done * 100 / total);
                            if (pct >= lastPct + 2) {
                                lastPct = pct;
                                updateProgress(pct, "Baixando a versão " + pcVersion + "… " + pct + "%");
                            }
                        }
                    }
                } finally {
                    c.disconnect();
                }
                updateProgress(100, "Instalando… se o Android pedir, toque em Atualizar.");
                // V6.5.9: com a tela aberta, usa o instalador padrão do Android (funciona até no Xiaomi);
                // em segundo plano, a instalação por sessão (silenciosa no Android 12+).
                if (visible && openSystemInstaller()) {
                    updateInProgress = false;
                    reportUpdate(true, "confirm", "Toque em Atualizar (ou Instalar) na tela do Android.");
                } else {
                    installApk(apk);
                    retryHandler.removeCallbacks(updateWatchdog);
                    retryHandler.postDelayed(updateWatchdog, 120_000L);
                }
            } catch (Exception e) {
                // V5.6: nunca mais abre o navegador para baixar: tenta de novo sozinho na próxima abertura
                updateInProgress = false;
                lastUpdateCheck = System.currentTimeMillis();
                reportUpdate(true, "error", "Não consegui atualizar agora. Tento de novo sozinho mais tarde.");
                runOnUiThread(() -> Toast.makeText(this,
                        "Não consegui atualizar agora. Tento de novo sozinho mais tarde.", Toast.LENGTH_SHORT).show());
            }
        }, "jarvis-self-update").start();
    }

    /** V6.5.9: abre o instalador do sistema com o APK baixado (tela "Deseja atualizar este app?"). */
    private boolean openSystemInstaller() {
        final boolean[] ok = {false};
        final java.util.concurrent.CountDownLatch done = new java.util.concurrent.CountDownLatch(1);
        runOnUiThread(() -> {
            try {
                Intent i = new Intent(Intent.ACTION_VIEW)
                        .setDataAndType(ApkProvider.uri(), "application/vnd.android.package-archive")
                        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(i);
                ok[0] = true;
            } catch (Exception e) {
                ok[0] = false;
            } finally {
                done.countDown();
            }
        });
        try {
            done.await(5, java.util.concurrent.TimeUnit.SECONDS);
        } catch (InterruptedException ignored) {
            Thread.currentThread().interrupt();
        }
        return ok[0];
    }

    private void installApk(java.io.File apk) throws java.io.IOException {
        android.content.pm.PackageInstaller installer = getPackageManager().getPackageInstaller();
        android.content.pm.PackageInstaller.SessionParams params = new android.content.pm.PackageInstaller.SessionParams(
                android.content.pm.PackageInstaller.SessionParams.MODE_FULL_INSTALL);
        params.setAppPackageName(getPackageName());
        if (Build.VERSION.SDK_INT >= 31) {
            params.setRequireUserAction(android.content.pm.PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED);
        }
        int sessionId = installer.createSession(params);
        android.content.pm.PackageInstaller.Session session = installer.openSession(sessionId);
        try {
            try (java.io.OutputStream out = session.openWrite("jarvis.apk", 0, apk.length());
                 java.io.InputStream in = new java.io.FileInputStream(apk)) {
                byte[] buf = new byte[16384];
                int n;
                while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                session.fsync(out);
            }
            int flags = android.app.PendingIntent.FLAG_UPDATE_CURRENT
                    | (Build.VERSION.SDK_INT >= 31 ? android.app.PendingIntent.FLAG_MUTABLE : 0);
            android.app.PendingIntent done = android.app.PendingIntent.getBroadcast(
                    this, sessionId, new Intent(this, InstallReceiver.class), flags);
            session.commit(done.getIntentSender());
        } catch (java.io.IOException | RuntimeException e) {
            session.abandon();
            throw e;
        } finally {
            session.close();
        }
    }

    private void downloadApk(String apkUrl) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(apkUrl));
            intent.addCategory(Intent.CATEGORY_BROWSABLE);
            startActivity(intent);
        } catch (Exception ignored) {
            Toast.makeText(this, "Não consegui abrir o download do APK.", Toast.LENGTH_LONG).show();
        }
    }

    // ------------------------------------------------------------------ avisos
    private void enableNotifications(boolean ask) {
        prefs.edit().putBoolean(NotifyService.KEY_ENABLED, true).apply();
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            if (ask) requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQ_NOTIFY);
            return; // sem permissão não dá para avisar; religa quando o usuário permitir
        }
        try {
            NotifyService.start(this);
        } catch (Exception ignored) {
        }
    }

    private void disableNotifications() {
        prefs.edit().putBoolean(NotifyService.KEY_ENABLED, false).apply();
        NotifyService.stop(this);
    }

    private boolean notificationsOn() {
        return prefs.getBoolean(NotifyService.KEY_ENABLED, true);
    }

    // ------------------------------------------------------------------ microfone nativo
    private void emitSpeech(String type, String text) {
        try {
            JSONObject d = new JSONObject().put("type", type).put("text", text == null ? "" : text);
            String js = "window.dispatchEvent(new CustomEvent('jarvis-native-speech',{detail:" + d + "}))";
            runOnUiThread(() -> web.evaluateJavascript(js, null));
        } catch (Exception ignored) {
        }
    }

    private void startListening() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            emitSpeech("error", "Este celular não tem reconhecimento de voz disponível (instale o app Google).");
            emitSpeech("end", "");
            return;
        }
        if (!hasMic()) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_MIC_SPEECH);
            return;
        }
        if (recognizer == null) {
            recognizer = SpeechRecognizer.createSpeechRecognizer(this);
            recognizer.setRecognitionListener(new RecognitionListener() {
                public void onReadyForSpeech(Bundle params) { emitSpeech("start", ""); }
                public void onBeginningOfSpeech() { }
                public void onRmsChanged(float rmsdB) { }
                public void onBufferReceived(byte[] buffer) { }
                public void onEndOfSpeech() { }
                public void onError(int error) {
                    if (error != SpeechRecognizer.ERROR_NO_MATCH && error != SpeechRecognizer.ERROR_SPEECH_TIMEOUT) {
                        emitSpeech("error", "Não consegui ouvir (erro " + error + "). Tente de novo.");
                    }
                    emitSpeech("end", "");
                }
                public void onResults(Bundle results) {
                    ArrayList<String> r = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    emitSpeech("final", r != null && !r.isEmpty() ? r.get(0) : "");
                    emitSpeech("end", "");
                }
                public void onPartialResults(Bundle partial) {
                    ArrayList<String> r = partial.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    if (r != null && !r.isEmpty()) emitSpeech("partial", r.get(0));
                }
                public void onEvent(int eventType, Bundle params) { }
            });
        }
        Intent i = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        i.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR");
        i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        recognizer.startListening(i);
    }

    private void stopListening(boolean cancel) {
        if (recognizer == null) return;
        if (cancel) recognizer.cancel();
        else recognizer.stopListening();
    }

    // ------------------------------------------------------------------ navegação
    private void loadSavedOrSetup() {
        String url = prefs.getString(KEY_URL, "");
        if (isHttp(url)) {
            web.loadUrl(url);
            checkForUpdate(url);
        } else {
            web.loadUrl(SETUP);
        }
    }

    private Uri savedUri() {
        String url = prefs.getString(KEY_URL, "");
        return isHttp(url) ? Uri.parse(url) : null;
    }

    private boolean sameHost(Uri uri) {
        Uri saved = savedUri();
        if (saved == null || uri.getHost() == null) return false;
        String remote = prefs.getString(KEY_REMOTE, "");
        return uri.getHost().equals(saved.getHost()) || (!remote.isEmpty() && uri.getHost().equals(remote));
    }

    private static boolean isHttp(String url) {
        return url != null && (url.startsWith("http://") || url.startsWith("https://"));
    }

    private boolean hasMic() {
        return checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        if (requestCode == REQ_MIC && pendingPermission != null) {
            if (hasMic()) pendingPermission.grant(pendingPermission.getResources());
            else pendingPermission.deny();
            pendingPermission = null;
        } else if (requestCode == REQ_MIC_SPEECH) {
            if (hasMic()) startListening();
            else {
                emitSpeech("error", "Permita o microfone para falar com o JARVIS.");
                emitSpeech("end", "");
            }
        } else if (requestCode == REQ_NOTIFY) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) enableNotifications(false);
        }
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) {
            web.goBack();
            return;
        }
        CharSequence notif = notificationsOn() ? "Desligar avisos no celular" : "Ligar avisos no celular";
        new AlertDialog.Builder(this)
                .setTitle("JARVIS")
                .setItems(new CharSequence[]{"Recarregar", notif, "Trocar conexão com o PC", "Sair"}, (d, which) -> {
                    if (which == 0) loadSavedOrSetup();
                    else if (which == 1) {
                        if (notificationsOn()) disableNotifications();
                        else enableNotifications(true);
                    } else if (which == 2) {
                        offlineScreen = false;
                        retryHandler.removeCallbacks(retryRunnable);
                        web.loadUrl(SETUP);
                    }
                    else finish();
                })
                .show();
    }

    /** Ponte JS. Tela de ajuda: salvar/repetir. Central do PC (mesmo endereço pareado): microfone e avisos. */
    private class Bridge {
        private boolean fromSetup() {
            return currentUrl != null && currentUrl.startsWith(SETUP);
        }

        private boolean fromJarvis() {
            return currentUrl != null && isHttp(currentUrl) && sameHost(Uri.parse(currentUrl));
        }

        @JavascriptInterface
        public boolean save(String url) {
            if (!fromSetup() || !isHttp(url)) return false;
            runOnUiThread(() -> connect(url));
            return true;
        }

        @JavascriptInterface
        public void retry() {
            if (fromSetup()) runOnUiThread(() -> {
                retryAttempt = 0;
                retryHandler.removeCallbacks(retryRunnable);
                loadSavedOrSetup();
            });
        }

        /** "Parear de novo / trocar de PC": para as tentativas automáticas e mostra o formulário. */
        @JavascriptInterface
        public void stopRetry() {
            if (fromSetup()) runOnUiThread(() -> {
                offlineScreen = false;
                retryHandler.removeCallbacks(retryRunnable);
            });
        }

        @JavascriptInterface
        public String savedUrl() {
            if (!fromSetup()) return "";
            String url = prefs.getString(KEY_URL, "");
            int q = url.indexOf("token=");
            return q > 0 ? url.substring(0, q) + "token=…" : url; // sem a chave
        }

        @JavascriptInterface
        public String savedHost() {
            return fromSetup() ? savedHostValue() : "";
        }

        @JavascriptInterface
        public void pairWithPin(String host, String pin) {
            if (fromSetup() && host != null && host.matches("[\\w.-]+") && pin != null && pin.matches("\\d{4,8}")) {
                MainActivity.this.pairWithPin(host, pin);
            }
        }

        /** V6.4: rede de agora e a da última vez que a central perguntou ("wifi" -> "cellular"...).
         *  Fica no app (não na página), então vale mesmo quando a página troca de endereço com a rede. */
        /** V6.5.5: a faixa DIGA pergunta se dá para fixar comandos na tela inicial. */
        @JavascriptInterface
        public boolean canPinShortcut() {
            return canPinCommands();
        }

        @JavascriptInterface
        public boolean pinShortcut(String label, String text) {
            return pinCommand(label, text);
        }

        @JavascriptInterface
        public String networkNotice() {
            String now = currentNetType();
            String prev = prefs.getString("net_seen", "");
            if (!"none".equals(now) && !"other".equals(now)) prefs.edit().putString("net_seen", now).apply();
            lastNetEmitted = now;
            try {
                return new JSONObject().put("type", now).put("prev", prev).toString();
            } catch (Exception e) {
                return "{}";
            }
        }

        @JavascriptInterface
        public String version() {
            return installedVersion();
        }

        /** V6.0: o celular tem digital e ela já foi ativada para o JARVIS? */
        @JavascriptInterface
        public boolean hasBiometric() {
            return fromJarvis() && biometricAvailable() && !prefs.getString(KEY_DEVICE_SECRET, "").isEmpty();
        }

        /** V6.0: dá para usar a digital neste celular (para oferecer ativar)? */
        @JavascriptInterface
        public boolean canUseBiometric() {
            return fromJarvis() && biometricAvailable();
        }

        /** V6.0: guarda a chave do aparelho depois de confirmar a digital (ativar). */
        @JavascriptInterface
        public void saveDeviceSecret(String secret) {
            if (!fromJarvis() || secret == null || secret.length() < 20 || secret.length() > 200) return;
            runOnUiThread(() -> askBiometric("Ativar a digital no JARVIS", "Confirme com a sua digital",
                    () -> {
                        prefs.edit().putString(KEY_DEVICE_SECRET, secret).apply();
                        sendBiometric("saved", null, "Digital ativada. Na próxima vez, é só encostar o dedo.");
                    }));
        }

        /** V6.0: entrar com a digital: confirmada, devolve a chave para a central liberar no PC. */
        @JavascriptInterface
        public void biometricUnlock() {
            String secret = prefs.getString(KEY_DEVICE_SECRET, "");
            if (!fromJarvis() || secret.isEmpty()) return;
            runOnUiThread(() -> askBiometric("Entrar no JARVIS", "Encoste o dedo para liberar a central",
                    () -> sendBiometric("unlock", secret, null)));
        }

        /** V6.0: esquece a digital neste celular. */
        @JavascriptInterface
        public void forgetBiometric() {
            if (fromJarvis()) prefs.edit().remove(KEY_DEVICE_SECRET).apply();
        }

        /** V5.7.1: botão ATUALIZAR APP (tela de bloqueio): procura versão nova no PC agora e responde à tela. */
        @JavascriptInterface
        public void checkUpdate() {
            if (!fromJarvis()) return;
            runOnUiThread(() -> checkForUpdate(prefs.getString(KEY_URL, ""), true));
        }

        @JavascriptInterface
        public boolean hasNativeSpeech() {
            return fromJarvis() && SpeechRecognizer.isRecognitionAvailable(MainActivity.this);
        }

        @JavascriptInterface
        public void listen() {
            if (fromJarvis()) runOnUiThread(MainActivity.this::startListening);
        }

        @JavascriptInterface
        public void stopListen(boolean cancel) {
            if (fromJarvis()) runOnUiThread(() -> stopListening(cancel));
        }

        @JavascriptInterface
        public boolean notificationsEnabled() {
            return (fromJarvis() || fromSetup()) && notificationsOn();
        }

        @JavascriptInterface
        public void setNotifications(boolean on) {
            if (!fromJarvis() && !fromSetup()) return;
            runOnUiThread(() -> {
                if (on) enableNotifications(true);
                else disableNotifications();
            });
        }
    }

    @Override
    protected void onDestroy() {
        retryHandler.removeCallbacksAndMessages(null);
        if (networkCallback != null) {
            try {
                ((ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE)).unregisterNetworkCallback(networkCallback);
            } catch (Exception ignored) {
            }
        }
        if (recognizer != null) recognizer.destroy();
        if (web != null) {
            web.setVisibility(View.GONE);
            web.destroy();
        }
        super.onDestroy();
    }
}
