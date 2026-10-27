package com.delpalacio.picking;

import org.json.JSONObject;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import javax.net.ssl.HttpsURLConnection;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;

/** Explicit HTTPS requests. No credentials in URLs, logs or persistent storage. */
final class Api {
    final String base;
    String token = "";
    Api(String base) {
        URI uri = URI.create(base.trim());
        if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null || uri.getUserInfo() != null
            || uri.getQuery() != null || uri.getFragment() != null || !(uri.getPath().isEmpty() || uri.getPath().equals("/")))
            throw new IllegalArgumentException("Ingresá la dirección HTTPS del servidor, sin /api ni credenciales.");
        this.base = base.trim().replaceAll("/+$", "");
    }
    String request(String method, String path, JSONObject body) throws Exception {
        HttpsURLConnection connection = (HttpsURLConnection) URI.create(base + "/api" + path).toURL().openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(15000); connection.setReadTimeout(20000);
        connection.setRequestMethod(method);
        connection.setRequestProperty("Accept", "application/json");
        if (!token.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + token);
        try {
            if (body != null) {
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (var out = connection.getOutputStream()) { out.write(body.toString().getBytes(StandardCharsets.UTF_8)); }
            }
            int status = connection.getResponseCode();
            InputStream stream = status < 400 ? connection.getInputStream() : connection.getErrorStream();
            String text = "";
            if (stream != null) try (stream; ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192]; int count;
                while ((count = stream.read(buffer)) != -1) bytes.write(buffer, 0, count);
                text = new String(bytes.toByteArray(), StandardCharsets.UTF_8);
            }
            if (status < 200 || status >= 300) {
                String message = status == 401 ? "Sesión vencida. Salí e ingresá nuevamente." : "El servidor no pudo completar la operación (" + status + ").";
                if (status == 404 && path.equals("/load-control/my-courts")) message = "Este servidor todavía no tiene asignaciones para Android. Usá la demostración hasta habilitarlas.";
                try { message = new JSONObject(text).optString("error", message); } catch (Exception ignored) { }
                throw new Exception(message);
            }
            return text;
        } finally { connection.disconnect(); }
    }
}
