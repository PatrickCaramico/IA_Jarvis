package com.patrick.jarvis;

import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import android.graphics.Color;
import android.os.Build;
import android.widget.Toast;

/**
 * V5.1.1: resultado da atualização automática (PackageInstaller).
 * - Android pede confirmação (primeira vez, ou Android < 12): abre a tela "Atualizar o JARVIS?".
 * - Deu certo: o Android troca o app e o reabre; nada a fazer aqui.
 * - Falhou: avisa e libera tentar de novo.
 *
 * V6.5.7: no Android 14+ (e em celulares Xiaomi/HyperOS) a tela de confirmação aberta daqui era
 * bloqueada em silêncio ("abrir em segundo plano"), e a barra ficava parada em 100%. Agora quem abre a
 * confirmação é a própria tela do JARVIS (que está na frente) e, de reserva, aparece um aviso
 * "Concluir atualização do JARVIS" para tocar.
 */
public class InstallReceiver extends BroadcastReceiver {
    static final int ID_CONFIRM = 4242;

    @Override
    public void onReceive(Context context, Intent intent) {
        int status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE);
        if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {
            Intent confirm = intent.getParcelableExtra(Intent.EXTRA_INTENT);
            if (confirm == null) return;
            confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            postConfirmNotification(context, confirm);
            MainActivity activity = MainActivity.current();
            if (activity != null && MainActivity.visible) {
                activity.openInstallConfirm(confirm);
            } else {
                try {
                    context.startActivity(confirm);
                } catch (Exception ignored) {
                    // o aviso acima conclui a atualização
                }
            }
            return;
        }
        cancelConfirmNotification(context);
        MainActivity.updateInProgress = false;
        MainActivity activity = MainActivity.current();
        if (status == PackageInstaller.STATUS_SUCCESS) return;
        String message = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE);
        String text;
        if (status == PackageInstaller.STATUS_FAILURE_ABORTED) {
            text = "Atualização cancelada. Toque em ATUALIZAR APP para tentar de novo.";
        } else {
            text = "Não consegui atualizar o JARVIS" + (message != null ? ": " + message : ".");
        }
        if (activity != null) activity.updateFinished(false, text);
        Toast.makeText(context, text, Toast.LENGTH_LONG).show();
    }

    private static void postConfirmNotification(Context context, Intent confirm) {
        try {
            NotifyService.createChannels(context);
            PendingIntent pi = PendingIntent.getActivity(context, ID_CONFIRM, confirm,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            Notification.Builder b = Build.VERSION.SDK_INT >= 26
                    ? new Notification.Builder(context, NotifyService.CH_ALERTS)
                    : new Notification.Builder(context);
            b.setSmallIcon(R.mipmap.ic_launcher)
                    .setContentTitle("Concluir atualização do JARVIS")
                    .setContentText("Toque aqui e depois em Atualizar.")
                    .setColor(Color.parseColor("#22D3EE"))
                    .setAutoCancel(true)
                    .setContentIntent(pi);
            if (Build.VERSION.SDK_INT < 26) b.setPriority(Notification.PRIORITY_HIGH);
            NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) nm.notify(ID_CONFIRM, b.build());
        } catch (Exception ignored) {
            // sem permissão de avisos: a tela do JARVIS ainda abre a confirmação
        }
    }

    static void cancelConfirmNotification(Context context) {
        try {
            NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) nm.cancel(ID_CONFIRM);
        } catch (Exception ignored) {
        }
    }
}
