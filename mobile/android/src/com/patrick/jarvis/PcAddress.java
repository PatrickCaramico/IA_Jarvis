package com.patrick.jarvis;

import android.net.Uri;

/**
 * V6.5: onde está o backend do PC a partir do endereço salvo do app.
 * - Rede de casa: http://IP:5173/?token=X           -> http://IP:8000
 * - De longe (túnel): https://site/app/?api=https://xxx.trycloudflare.com&token=X -> https://xxx.trycloudflare.com
 */
final class PcAddress {
    private PcAddress() {
    }

    static String base(Uri saved) {
        if (saved == null) return null;
        String api = saved.getQueryParameter("api");
        if (api != null && api.matches("https://[A-Za-z0-9-]+\\.trycloudflare\\.com/?")) {
            return api.endsWith("/") ? api.substring(0, api.length() - 1) : api;
        }
        String host = saved.getHost();
        if (host == null || host.isEmpty()) return null;
        return "http://" + host + ":8000";
    }

    /** "?token=X" (ou "") para as rotas que pelo túnel exigem a chave. */
    static String tokenQuery(Uri saved) {
        String token = saved == null ? null : saved.getQueryParameter("token");
        return token == null || token.isEmpty() ? "" : "?token=" + Uri.encode(token);
    }
}
