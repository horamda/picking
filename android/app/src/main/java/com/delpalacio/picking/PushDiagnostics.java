package com.delpalacio.picking;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;
import com.google.firebase.FirebaseApp;
import com.google.firebase.messaging.FirebaseMessaging;

final class PushDiagnostics {
    static void show(Activity activity) {
        PickingMessagingService.createChannel(activity);
        if (Build.VERSION.SDK_INT >= 33 && activity.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            new AlertDialog.Builder(activity).setTitle("Permitir avisos de trabajo")
                .setMessage("Android necesita tu permiso para mostrar avisos. Podés seguir trabajando si no lo aceptás.")
                .setNegativeButton("Ahora no", null)
                .setPositiveButton("Permitir", (d,w) -> activity.requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 21)).show();
            return;
        }
        FirebaseMessaging.getInstance().getToken().addOnCompleteListener(activity, task -> {
            if (activity.isFinishing() || activity.isDestroyed()) return;
            if (!task.isSuccessful()) {
                new AlertDialog.Builder(activity).setTitle("Firebase sin conexión")
                    .setMessage("No se pudo obtener el identificador del teléfono. Revisá Internet y los servicios de Google Play, y volvé a intentar.")
                    .setPositiveButton("Cerrar", null).show();
                return;
            }
            String token = task.getResult();
            new AlertDialog.Builder(activity).setTitle("Firebase disponible")
                .setMessage("Proyecto: " + FirebaseApp.getInstance().getOptions().getProjectId()
                    + "\nEste teléfono obtuvo su token FCM. Podés copiarlo para enviar un mensaje de prueba desde Firebase."
                    + "\n\n" + activity.getSharedPreferences("push", Context.MODE_PRIVATE).getString("server_status", "Registro en Railway pendiente."))
                .setNegativeButton("Cerrar", null)
                .setPositiveButton("Copiar token de prueba", (d,w) -> {
                    activity.getSystemService(ClipboardManager.class).setPrimaryClip(ClipData.newPlainText("Token FCM de prueba", token));
                    android.widget.Toast.makeText(activity, "Token copiado para la prueba en Firebase", android.widget.Toast.LENGTH_LONG).show();
                }).show();
        });
    }
}
