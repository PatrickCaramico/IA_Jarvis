package com.patrick.jarvis;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * V4.5: avisos do JARVIS no celular (lembretes, água, gatilhos, Modo Torcedor).
 *
 * Serviço em primeiro plano com uma notificação discreta ("JARVIS conectado"). A cada 30 s consulta
 * GET http://PC:8000/api/mobile/notifications?since=N com a chave de pareamento, na Wi-Fi de casa.
 * Sem servidor na nuvem: se o celular sair de casa, os avisos esperam até ele voltar a alcançar o PC.
 */
public class NotifyService extends Service {
    static final String CH_ALERTS = "jarvis_avisos";
    static final String CH_LINK = "jarvis_conexao";
    static final String KEY_ENABLED = "notify_enabled";
    private static final String KEY_SINCE = "notify_since";
    private static final int ID_FOREGROUND = 1;
    private static final long INTERVAL_MS = 30_000;

    private HandlerThread thread;
    private Handler handler;
    private SharedPreferences prefs;
    private int nextId = 100;
    private boolean lastOk = true;

    static void start(Context ctx) {
        Intent i = new Intent(ctx, NotifyService.class);
        if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(i);
        else ctx.startService(i);
    }

    static void stop(Context ctx) {
        ctx.stopService(new Intent(ctx, NotifyService.class));
    }

    static void createChannels(Context ctx) {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager nm = ctx.getSystemService(NotificationManager.class);
        NotificationChannel alerts = new NotificationChannel(CH_ALERTS, "Avisos do JARVIS", NotificationManager.IMPORTANCE_HIGH);
        alerts.setDescription("Lembretes, água, avisos e Modo Torcedor");
        alerts.enableLights(true);
        alerts.setLightColor(Color.parseColor("#22D3EE"));
        NotificationChannel link = new NotificationChannel(CH_LINK, "Conexão com o PC", NotificationManager.IMPORTANCE_MIN);
        link.setDescription("Mantém o JARVIS ouvindo os avisos do PC");
        link.setShowBadge(false);
        nm.createNotificationChannel(alerts);
        nm.createNotificationChannel(link);
    }

    @Override
    public void onCreate() {
        super.onCreate();
        prefs = getSharedPreferences("jarvis", MODE_PRIVATE);
        createChannels(this);
        Notification fg = linkNotification("Conectado ao PC · avisos ligados");
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(ID_FOREGROUND, fg, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        } else {
            startForeground(ID_FOREGROUND, fg);
        }
        thread = new HandlerThread("jarvis-avisos");
        thread.start();
        handler = new Handler(thread.getLooper());
        handler.post(poll);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    private final Runnable poll = new Runnable() {
        @Override
        public void run() {
            try {
                check();
            } catch (Exception e) {
                setLink(false);
            }
            handler.postDelayed(this, INTERVAL_MS);
        }
    };

    /** http://IP:5173/?token=X  ->  http://IP:8000/api/mobile/notifications?since=N&token=X */
    private String feedUrl(long since) {
        String saved = prefs.getString("url", "");
        if (saved.isEmpty()) return null;
        Uri u = Uri.parse(saved);
        String token = u.getQueryParameter("token");
        String base = PcAddress.base(u); // V6.5: Wi-Fi de casa (IP:8000) ou túnel (https)
        if (base == null || token == null) return null;
        return base + "/api/mobile/notifications?since=" + since + "&token=" + Uri.encode(token);
    }

    private void check() throws Exception {
        long since = prefs.getLong(KEY_SINCE, -1);
        String url = feedUrl(since);
        if (url == null) return;
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(5000);
        c.setReadTimeout(8000);
        c.setRequestProperty("Accept", "application/json");
        int code = c.getResponseCode();
        if (code != 200) {
            c.disconnect();
            setLink(false);
            return;
        }
        StringBuilder sb = new StringBuilder();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(c.getInputStream(), "UTF-8"))) {
            String line;
            while ((line = r.readLine()) != null) sb.append(line);
        }
        c.disconnect();
        setLink(true);
        JSONObject json = new JSONObject(sb.toString());
        long latest = json.optLong("latest", 0);
        // O PC reiniciou (a fila recomeçou do zero): volta a contar dali
        if (since > latest) since = 0;
        JSONArray items = json.optJSONArray("items");
        if (items != null && since >= 0) {
            for (int i = 0; i < items.length(); i++) {
                JSONObject n = items.getJSONObject(i);
                if (!MainActivity.visible) show(n.optString("title", "JARVIS"), n.optString("body", ""), n.optString("kind", ""));
            }
        }
        prefs.edit().putLong(KEY_SINCE, latest).apply();
    }

    private void show(String title, String body, String kind) {
        Intent open = new Intent(this, MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        // V6.5: aviso de notícia abre a janela de notícias
        if ("news".equals(kind)) open.setAction(Intent.ACTION_VIEW).setData(Uri.parse("jarvis://news"));
        PendingIntent pi = PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26 ? new Notification.Builder(this, CH_ALERTS) : new Notification.Builder(this);
        b.setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(new Notification.BigTextStyle().bigText(body))
                .setColor(Color.parseColor("#22D3EE"))
                .setAutoCancel(true)
                .setContentIntent(pi);
        if (Build.VERSION.SDK_INT < 26) b.setPriority(Notification.PRIORITY_HIGH).setDefaults(Notification.DEFAULT_ALL);
        getSystemService(NotificationManager.class).notify(nextId++, b.build());
    }

    private Notification linkNotification(String text) {
        Intent open = new Intent(this, MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pi = PendingIntent.getActivity(this, 1, open, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26 ? new Notification.Builder(this, CH_LINK) : new Notification.Builder(this);
        return b.setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle("JARVIS")
                .setContentText(text)
                .setOngoing(true)
                .setColor(Color.parseColor("#174A95"))
                .setContentIntent(pi)
                .build();
    }

    private void setLink(boolean ok) {
        if (ok == lastOk) return;
        lastOk = ok;
        getSystemService(NotificationManager.class).notify(ID_FOREGROUND,
                linkNotification(ok ? "Conectado ao PC · avisos ligados" : "Sem conexão com o PC · tentando de novo"));
    }

    @Override
    public void onDestroy() {
        if (handler != null) handler.removeCallbacksAndMessages(null);
        if (thread != null) thread.quitSafely();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
