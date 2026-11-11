package com.patrick.jarvis;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import android.widget.Toast;

/**
 * V5.1.1: resultado da atualização automática (PackageInstaller).
 * - Android pede confirmação (primeira vez, ou Android < 12): abre a tela "Atualizar o JARVIS?".
 * - Deu certo: o Android troca o app e o reabre; nada a fazer aqui.
 * - Falhou: avisa e libera tentar de novo na próxima abertura.
 */
public class InstallReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        int status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE);
        if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {
            Intent confirm = intent.getParcelableExtra(Intent.EXTRA_INTENT);
            if (confirm != null) {
                confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                try {
                    context.startActivity(confirm);
                } catch (Exception ignored) {
                    Toast.makeText(context, "Toque na notificação do Android para concluir a atualização.", Toast.LENGTH_LONG).show();
                }
            }
            return;
        }
        if (status == PackageInstaller.STATUS_SUCCESS) return;
        MainActivity.updateInProgress = false;
        String message = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE);
        if (status == PackageInstaller.STATUS_FAILURE_ABORTED) {
            Toast.makeText(context, "Atualização do JARVIS cancelada. Ela volta a ser oferecida na próxima abertura.", Toast.LENGTH_LONG).show();
        } else {
            Toast.makeText(context, "Não consegui atualizar o JARVIS" + (message != null ? ": " + message : "."), Toast.LENGTH_LONG).show();
        }
    }
}
