package com.patrick.jarvis;

import android.app.PendingIntent;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/**
 * V6.0: botão "JARVIS" nas configurações rápidas do Android (a cortina que desce do topo).
 * Um toque abre a central já ouvindo (jarvis://listen), mesmo com o app fechado.
 * Para colocar: puxe a cortina, toque no lápis (editar) e arraste o "JARVIS" para os botões.
 */
public class JarvisTile extends TileService {
    @Override
    public void onStartListening() {
        Tile tile = getQsTile();
        if (tile == null) return;
        tile.setLabel("JARVIS");
        if (Build.VERSION.SDK_INT >= 29) tile.setSubtitle("Falar");
        tile.setState(Tile.STATE_INACTIVE);
        tile.updateTile();
    }

    @Override
    public void onClick() {
        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse("jarvis://listen"))
                .setPackage(getPackageName())
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        if (Build.VERSION.SDK_INT >= 34) {
            PendingIntent pi = PendingIntent.getActivity(this, 0, intent,
                    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
            startActivityAndCollapse(pi);
        } else {
            startActivityAndCollapseCompat(intent);
        }
    }

    @SuppressWarnings("deprecation")
    private void startActivityAndCollapseCompat(Intent intent) {
        startActivityAndCollapse(intent);
    }
}
