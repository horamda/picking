package com.delpalacio.picking;

import android.Manifest;
import android.app.*;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.os.*;
import org.json.JSONObject;
import org.vosk.*;
import org.vosk.android.*;

/** Owns the microphone while a user-initiated picking session is active. */
public final class VoiceSessionService extends Service {
    static final String STOP="com.delpalacio.picking.STOP_VOICE";
    private static final String CHANNEL="picking_voice";
    interface Listener {
        void onReady();
        void onText(String text);
        void onState(String state);
        void onStopped(String reason);
    }
    final class LocalBinder extends Binder { VoiceSessionService service(){return VoiceSessionService.this;} }
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final MicRecovery recovery=new MicRecovery();
    private Listener listener;
    private Model model;
    private Recognizer recognizer;
    private SpeechService microphone;
    private PowerManager.WakeLock wakeLock;
    private boolean active, loading, wanted, destroyed;
    private int generation;
    private long lastEvent;
    private String state="Preparando voz…";
    private final Runnable watchdog=new Runnable(){public void run(){
        if(!active || !wanted || microphone==null)return;
        // Vosk emits partial callbacks even during silence. Only a stalled recorder is restarted.
        if(SystemClock.elapsedRealtime()-lastEvent>20000)recover(generation,"La captura dejó de responder.");
        else handler.postDelayed(this,5000);
    }};

    @Override public IBinder onBind(Intent intent){return new LocalBinder();}
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent!=null && STOP.equals(intent.getAction())){end("Voz detenida desde la notificación.");return START_NOT_STICKY;}
        if(active)return START_NOT_STICKY;
        try{
            if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)throw new SecurityException("Falta permiso de micrófono.");
            NotificationManager notifications=getSystemService(NotificationManager.class);
            notifications.createNotificationChannel(new NotificationChannel(CHANNEL,"Picking por voz",NotificationManager.IMPORTANCE_LOW));
            Notification notification=notification("Preparando voz…");
            if(Build.VERSION.SDK_INT>=29)startForeground(41,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
            else startForeground(41,notification);
            active=true;
            wakeLock=getSystemService(PowerManager.class).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"DelPalacio:VoicePicking");
            wakeLock.acquire();
            loadModel();
        }catch(Exception e){end("No se pudo activar el micrófono: "+e.getMessage());}
        return START_NOT_STICKY;
    }
    private Notification notification(String text){
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,VoiceSessionService.class).setAction(STOP),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this,CHANNEL).setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("Del Palacio · Voz activa").setContentText(text).setContentIntent(open)
            .setOngoing(true).setOnlyAlertOnce(true).setVisibility(Notification.VISIBILITY_PRIVATE)
            .addAction(new Notification.Action.Builder(null,"Parar voz",stop).build()).build();
    }
    private void state(String value){state=value;if(active)getSystemService(NotificationManager.class).notify(41,notification(value));if(listener!=null)listener.onState(value);}
    String state(){return state;}
    boolean isActive(){return active;}
    void attach(Listener value){listener=value;if(!active){value.onStopped("No se pudo iniciar la voz. Volvé a activarla desde la app.");return;}value.onState(state);if(model!=null)value.onReady();}
    void detach(){listener=null;}
    private void loadModel(){
        if(loading || model!=null)return;loading=true;
        StorageService.unpack(this,"model-es","voice-model",ready->{
            loading=false;if(destroyed || !active){ready.close();return;}model=ready;
            state("Voz preparada");if(listener!=null)listener.onReady();
        },error->{loading=false;if(!destroyed)end("No se pudo cargar el modelo de voz. "+error.getMessage());});
    }
    void listen(){
        if(!active || model==null)return;
        if(wanted && microphone!=null)return;
        wanted=true;openMicrophone();
    }
    void suspendListening(){
        wanted=false;closeMicrophone();if(active)state("Voz activa · Esperando indicación");
    }
    private void closeMicrophone(){
        generation++;handler.removeCallbacksAndMessages(null);
        if(microphone!=null){microphone.cancel();microphone.shutdown();microphone=null;}
        if(recognizer!=null){recognizer.close();recognizer=null;}
    }
    private void openMicrophone(){
        if(!active || !wanted || model==null)return;
        closeMicrophone();int attempt=generation;
        try{
            if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)throw new SecurityException("Permiso de micrófono revocado.");
            recognizer=new Recognizer(model,16000,VoiceCommands.grammar());microphone=new SpeechService(recognizer,16000);
            boolean started=microphone.startListening(new RecognitionListener(){
                @Override public void onPartialResult(String json){handler.post(()->{if(attempt==generation)lastEvent=SystemClock.elapsedRealtime();});}
                @Override public void onResult(String json){handler.post(()->{
                    if(!active || !wanted || attempt!=generation)return;lastEvent=SystemClock.elapsedRealtime();
                    try{String text=new JSONObject(json).optString("text");if(listener!=null && !text.trim().isEmpty())listener.onText(text);}catch(Exception e){recover(attempt,"No se pudo interpretar el audio.");}
                });}
                @Override public void onFinalResult(String json){handler.post(()->recover(attempt,"La captura terminó."));}
                @Override public void onError(Exception error){handler.post(()->recover(attempt,error.getMessage()));}
                @Override public void onTimeout(){handler.post(()->recover(attempt,"La captura se interrumpió."));}
            });
            if(!started)throw new IllegalStateException("El micrófono no inició.");
            lastEvent=SystemClock.elapsedRealtime();state("Escuchando…");handler.postDelayed(watchdog,5000);
            handler.postDelayed(()->{if(active && wanted && attempt==generation)recovery.stable();},30000);
        }catch(SecurityException e){end("Revisá el permiso de micrófono y activá la voz nuevamente.");}
        catch(Exception e){recover(attempt,e.getMessage());}
    }
    private void recover(int attempt,String reason){
        if(!active || !wanted || attempt!=generation)return;
        closeMicrophone();long delay=recovery.nextDelayMillis();
        if(delay<0){end("No pude recuperar el micrófono. Cerrá otras apps que lo usen y tocá Activar voz.");return;}
        state("Reconectando micrófono…");int next=generation;
        handler.postDelayed(()->{if(active && wanted && next==generation)openMicrophone();},delay);
    }
    private void end(String reason){
        active=false;wanted=false;closeMicrophone();
        if(wakeLock!=null && wakeLock.isHeld())wakeLock.release();
        Listener callback=listener;listener=null;if(callback!=null)callback.onStopped(reason);
        stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();
    }
    @Override public void onTaskRemoved(Intent rootIntent){end("Voz detenida al cerrar la app.");}
    @Override public void onDestroy(){destroyed=true;end("Voz detenida.");if(model!=null){model.close();model=null;}super.onDestroy();}
}
