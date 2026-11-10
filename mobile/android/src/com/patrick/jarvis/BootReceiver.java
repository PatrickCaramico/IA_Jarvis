package com.patrick.jarvis;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** V4.5: religa os avisos do JARVIS depois que o celular reinicia (se estiverem ligados). */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        if (!Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) return;
        boolean on = ctx.getSharedPreferences("jarvis", Context.MODE_PRIVATE).getBoolean(NotifyService.KEY_ENABLED, false);
        String url = ctx.getSharedPreferences("jarvis", Context.MODE_PRIVATE).getString("url", "");
        if (on && !url.isEmpty()) {
            try {
                NotifyService.start(ctx);
            } catch (Exception ignored) {
                // Alguns aparelhos bloqueiam serviço no boot; o app religa ao ser aberto.
            }
        }
    }
}
