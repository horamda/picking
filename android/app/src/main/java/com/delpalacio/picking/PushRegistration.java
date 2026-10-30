package com.delpalacio.picking;

import android.content.Context;
import com.google.android.gms.tasks.Tasks;
import com.google.firebase.messaging.FirebaseMessaging;
import org.json.JSONObject;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/** Isolated queue: notification failures never delay picking writes. */
final class PushRegistration {
    private static final java.util.concurrent.ExecutorService io = Executors.newSingleThreadExecutor();
    private static volatile Api session;
    private static long lastAttempt;

    static synchronized void sync(Context context, Api api) {
        long now = android.os.SystemClock.elapsedRealtime();
        Context app = context.getApplicationContext();
        boolean pending = app.getSharedPreferences("push", Context.MODE_PRIVATE).getBoolean("registration_pending", true);
        if (session == api && now - lastAttempt < (pending ? 60000 : 3600000)) return;
        session = api; lastAttempt = now;
        io.execute(() -> {
            if (session != api) return;
            try {
                String token = Tasks.await(FirebaseMessaging.getInstance().getToken(), 15, TimeUnit.SECONDS);
                if (session != api) return;
                api.request("POST", "/load-control/push/device", new JSONObject().put("token", token));
                if (session == api) app.getSharedPreferences("push", Context.MODE_PRIVATE).edit()
                    .putBoolean("registration_pending", false).putString("server_status", "Teléfono registrado para avisos automáticos.").apply();
            } catch (Exception error) {
                if (session == api) app.getSharedPreferences("push", Context.MODE_PRIVATE).edit()
                    .putBoolean("registration_pending", true).putString("server_status",
                        error instanceof Api.HttpError && ((Api.HttpError)error).status == 503
                        ? "Railway todavía no habilitó los avisos automáticos."
                        : "No se pudo registrar el teléfono. Se reintentará al actualizar el inicio.").apply();
            }
        });
    }

    static void refresh(Context context) {
        Api api = session;
        if (api != null) sync(context, api);
    }

    static synchronized void logout(Context context) {
        Api previous = session;
        session = null; lastAttempt = 0;
        Context app = context.getApplicationContext();
        app.getSharedPreferences("push", Context.MODE_PRIVATE).edit()
            .putBoolean("registration_pending", true).putString("server_status", "Sin sesión de operario registrada.").apply();
        if (previous == null) return;
        io.execute(() -> {
            try {
                String token = Tasks.await(FirebaseMessaging.getInstance().getToken(), 15, TimeUnit.SECONDS);
                previous.request("DELETE", "/load-control/push/device", new JSONObject().put("token", token));
            } catch (Exception ignored) { /* No credentials or tokens in logs. */ }
            try { Tasks.await(FirebaseMessaging.getInstance().deleteToken(), 15, TimeUnit.SECONDS); }
            catch (Exception ignored) { /* Offline logout cannot guarantee remote revocation. */ }
        });
    }
}
