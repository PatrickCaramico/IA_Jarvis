package com.patrick.jarvis;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
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

    private WebView web;
    private SharedPreferences prefs;
    private PermissionRequest pendingPermission;
    private volatile String currentUrl = "";
    private SpeechRecognizer recognizer;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
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
                    String h = savedHostValue();
                    view.loadUrl(SETUP + "#erro" + (h.isEmpty() ? "" : "&host=" + h));
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
    }

    @Override
    protected void onResume() {
        super.onResume();
        visible = true;
    }

    @Override
    protected void onPause() {
        visible = false;
        super.onPause();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    private boolean handleIntent(Intent intent) {
        if (intent == null || intent.getData() == null) return false;
        return handleUri(intent.getData());
    }

    /** jarvis://connect?url=http://IP:5173/?token=...  |  jarvis://open */
    private boolean handleUri(Uri uri) {
        if (!"jarvis".equals(uri.getScheme())) return false;
        if ("connect".equals(uri.getHost())) {
            String url = uri.getQueryParameter("url");
            if (isHttp(url)) {
                connect(url);
                return true;
            }
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
        Uri paired = Uri.parse(appUrl);
        String host = paired.getHost();
        if (!isHttp(appUrl) || host == null || host.isEmpty()) return;

        new Thread(() -> {
            try {
                java.net.HttpURLConnection connection = (java.net.HttpURLConnection)
                        new java.net.URL("http://" + host + ":8000/api/mobile/info").openConnection();
                connection.setConnectTimeout(5000);
                connection.setReadTimeout(7000);
                connection.setRequestMethod("GET");
                String token = paired.getQueryParameter("token");
                if (token != null && !token.isEmpty()) connection.setRequestProperty("X-Jarvis-Token", token);
                int status = connection.getResponseCode();
                if (status != 200) {
                    connection.disconnect();
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
                String pcVersion = info.optString("version", "");
                String phoneVersion = installedVersion();
                if (info.optBoolean("available") && compareVersions(pcVersion, phoneVersion) > 0) {
                    runOnUiThread(() -> showUpdateDialog(host, pcVersion, phoneVersion));
                }
            } catch (Exception ignored) {
                // Sem conexão ou sem APK novo: não interrompe a abertura do JARVIS.
            }
        }, "jarvis-update-check").start();
    }

    private void showUpdateDialog(String host, String pcVersion, String phoneVersion) {
        if (isFinishing()) return;
        new AlertDialog.Builder(this)
                .setTitle("Atualização do JARVIS disponível")
                .setMessage("O PC tem a versão " + pcVersion + ". A versão instalada é " + phoneVersion + ".")
                .setPositiveButton("Baixar APK", (dialog, which) -> downloadApk(host))
                .setNegativeButton("Agora não", null)
                .show();
    }

    private void downloadApk(String host) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse("http://" + host + ":8000/api/mobile/app.apk"));
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
        return saved != null && uri.getHost() != null && uri.getHost().equals(saved.getHost());
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
                    } else if (which == 2) web.loadUrl(SETUP);
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
            if (fromSetup()) runOnUiThread(MainActivity.this::loadSavedOrSetup);
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

        @JavascriptInterface
        public String version() {
            return installedVersion();
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
        if (recognizer != null) recognizer.destroy();
        if (web != null) {
            web.setVisibility(View.GONE);
            web.destroy();
        }
        super.onDestroy();
    }
}
