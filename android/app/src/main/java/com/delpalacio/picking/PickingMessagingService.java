package com.delpalacio.picking;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Build;
import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

/** Push is an invitation to refresh, never an instruction to mutate a task. */
public final class PickingMessagingService extends FirebaseMessagingService {
    static final String CHANNEL = "picking_tasks";

    static void createChannel(Context context) {
        NotificationChannel channel = new NotificationChannel(CHANNEL, "Avisos de trabajo", NotificationManager.IMPORTANCE_DEFAULT);
        channel.setDescription("Avisos para consultar las tareas habilitadas en el depósito");
        context.getSystemService(NotificationManager.class).createNotificationChannel(channel);
    }

    @Override public void onNewToken(String token) {
        // Do not log tokens or attach them to an unauthenticated user.
        getSharedPreferences("push", MODE_PRIVATE).edit().putBoolean("registration_pending", true).apply();
        PushRegistration.refresh(this);
    }

    @Override public void onMessageReceived(RemoteMessage message) {
        createChannel(this);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return;
        // Generic wording avoids displaying warehouse data on the lock screen.
        Intent open = new Intent(this, MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent action = PendingIntent.getActivity(this, 20, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification notification = new Notification.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Del Palacio · Picking")
            .setContentText("Hay un aviso de trabajo. Abrí la app y actualizá tus tareas.")
            .setContentIntent(action).setAutoCancel(true)
            .setVisibility(Notification.VISIBILITY_PRIVATE).build();
        getSystemService(NotificationManager.class).notify(20, notification);
    }
}
