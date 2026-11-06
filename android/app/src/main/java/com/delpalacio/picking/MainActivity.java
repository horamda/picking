package com.delpalacio.picking;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
import android.content.Intent;
import android.content.ComponentName;
import android.content.ServiceConnection;
import android.os.IBinder;
import android.os.Build;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.text.InputType;
import android.view.View;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.*;
import org.json.*;
import java.util.*;
import java.util.concurrent.*;

public final class MainActivity extends Activity {
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private LinearLayout content;
    private LinearLayout root, body;
    private TextView status;
    private TextView voiceStatus, heardView, clockView, bHint, uHint, shortageFeedback;
    private Button voiceButton;
    private EditText shortageB, shortageU;
    private String lastHeard="";
    private int INK=0xff0f172a, MUTED=0xff607493, BORDER=0xffdce5ef, BG=0xfff0f5f9, SURFACE=Color.WHITE;
    private static final int GREEN=0xff059669, RED=0xffb91c1c;
    private boolean dark;
    private void applyTheme(){
        dark=getPreferences(0).getBoolean("dark",false);
        setTheme(dark?android.R.style.Theme_Material_NoActionBar:android.R.style.Theme_Material_Light_NoActionBar);
        INK=dark?0xffe2e8f0:0xff0f172a;MUTED=dark?0xffadbed3:0xff607493;
        BORDER=dark?0xff3b4b63:0xffdce5ef;BG=dark?0xff0b1220:0xfff0f5f9;SURFACE=dark?0xff182235:Color.WHITE;
        getWindow().setStatusBarColor(SURFACE);getWindow().setNavigationBarColor(SURFACE);
        getWindow().getDecorView().setSystemUiVisibility(dark?0:View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
    }
    private void inputs(View v,List<EditText> fields){
        if(v instanceof EditText)fields.add((EditText)v);
        if(v instanceof android.view.ViewGroup){android.view.ViewGroup g=(android.view.ViewGroup)v;for(int i=0;i<g.getChildCount();i++)inputs(g.getChildAt(i),fields);}
    }
    private void toggleTheme(){
        List<EditText> fields=new ArrayList<>();inputs(root,fields);List<String> values=new ArrayList<>();for(EditText field:fields)values.add(field.getText().toString());
        getPreferences(0).edit().putBoolean("dark",!dark).apply();applyTheme();
        if(currentScreen.equals("login")){login();fields.clear();inputs(root,fields);for(int i=0;i<Math.min(fields.size(),values.size());i++)fields.get(i).setText(values.get(i));}
        else listLoads();
    }
    private final Runnable clockTick=new Runnable(){public void run(){updateClock();handler.postDelayed(this,1000);}};
    private Api api;
    private JSONObject user, load, court, check, activeTruck, controlTruck, pallet;
    private JSONObject voiceTemplates = new JSONObject();
    private JSONObject voiceSettings = new JSONObject();
    private JSONObject voiceCommands = new JSONObject();
    private float speechRate=1f;
    private int freshnessWarningDays=30;
    private JSONArray products = new JSONArray(), operators = new JSONArray();
    private Set<Integer> assigned = new HashSet<>();
    private final Set<String> automaticallySpokenProducts = new HashSet<>();
    private String filter = "Todos";
    private String currentScreen = "login";
    private int index = 0, requestVersion = 0, speechVersion = 0, currentStage = 0;
    private boolean demo = false, busy = false, voice = false, visible = false, ttsReady = false;
    private TextToSpeech tts;
    private VoiceSessionService voiceSession;
    private boolean voiceBound, enableAfterPermission;
    private boolean announceQueue;
    private Set<String> knownTasks;
    private String queueVersion="";
    private boolean refreshing;
    private int voiceNextLoadId,voiceNextCourt;
    private JSONObject voiceCourtCandidate;
    private boolean voiceConfirmFinish;
    private Runnable voiceShortageSubmit;
    private JSONObject fetchQueue() throws Exception {
        JSONObject response=obj("permissions",json("GET","/load-control/my-courts",null),"trucks",new JSONArray(api.request("GET","/load-control/trucks",null)));
        if(isController())response.put("operators",new JSONArray(api.request("GET","/load-control/operators",null)));
        try{JSONObject runtime=json("GET","/voice-templates/runtime",null);response.put("voice_templates",runtime.getJSONObject("templates"));response.put("voice_settings",runtime.optJSONObject("settings"));response.put("voice_commands",runtime.optJSONObject("commands"));response.put("speech_rate",runtime.optDouble("speech_rate",1));response.put("freshness_warning_days",runtime.optInt("freshness_warning_days",30));}catch(Exception ignored){ }
        return response;
    }
    private String queueVersion(JSONObject response) throws Exception {
        StringBuilder key=new StringBuilder(response.getJSONObject("permissions").toString());
        JSONArray trucks=response.getJSONArray("trucks");
        for(int i=0;i<trucks.length();i++){JSONObject truck=trucks.getJSONObject(i);key.append('|').append(truck.optInt("id")).append(':').append(truck.optInt("version")).append(':').append(truck.optString("planning_status"));}
        return key.toString();
    }
    private final Runnable syncQueue=new Runnable(){public void run(){
        handler.postDelayed(this,15000);
        if(!visible || busy || refreshing || user==null || demo || !currentScreen.equals("loads"))return;
        PushRegistration.sync(MainActivity.this,api);
        refreshing=true;int generation=requestVersion;
        network.execute(()->{try{
            String updated=queueVersion(fetchQueue());
            handler.post(()->{refreshing=false;if(!isDestroyed() && generation==requestVersion && visible && !busy && currentScreen.equals("loads") && !updated.equals(queueVersion))listLoads();});
        }catch(Exception e){handler.post(()->{refreshing=false;if(visible && currentScreen.equals("loads"))message("Sin actualizar: revisá la conexión. Los datos visibles pueden estar desactualizados.");});}});
    }};
    private final VoiceSessionService.Listener voiceListener=new VoiceSessionService.Listener(){
        public void onReady(){if(voice && !isDestroyed())activateVoice();}
        public void onText(String text){if(voice && !busy && !isDestroyed())command(text);}
        public void onState(String state){if(voice)updateVoiceUi(state);}
        public void onStopped(String reason){voice=false;stopAudio();updateVoiceUi("Voz detenida");message(reason);}
    };
    private final ServiceConnection voiceConnection=new ServiceConnection(){
        public void onServiceConnected(ComponentName name,IBinder binder){
            voiceSession=((VoiceSessionService.LocalBinder)binder).service();
            if(!voice || isDestroyed()){stopVoiceSession();return;}
            voiceSession.attach(voiceListener);
            voiceSession.configureGrammar(VoiceCommands.grammar(voiceCommands));
        }
        public void onServiceDisconnected(ComponentName name){
            voiceSession=null;voice=false;stopAudio();updateVoiceUi("Voz detenida");
            message("El servicio de voz se interrumpió. Tocá Activar voz para retomarlo.");
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        PickingMessagingService.createChannel(this);
        applyTheme();
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        tts = new TextToSpeech(this, result -> {
            if (result == TextToSpeech.SUCCESS) {
                int language = tts.setLanguage(new Locale("es", "AR"));
                ttsReady = language != TextToSpeech.LANG_MISSING_DATA && language != TextToSpeech.LANG_NOT_SUPPORTED;
            }
        });
        login();
    }
    private int dp(int n) { return Math.round(n * getResources().getDisplayMetrics().density); }
    private GradientDrawable shape(int color,int border,int radius) {
        if(dark){
            if(color==Color.WHITE)color=SURFACE;
            if(color==0xffd1fae5 || color==0xffecfdf5)color=0xff10382e;
            if(color==0xfffff1f2)color=0xff451c2b;
            if(color==0xfffffbeb)color=0xff3f2d12;
            if(border==0xffcbd5e1)border=BORDER;
        }
        GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));d.setStroke(dp(1),border);return d;
    }
    private TextView label(String value,int size,int color,boolean bold) {
        if(dark && color==0xff047857)color=0xff6ee7b7;
        TextView v=new TextView(this);v.setText(value);v.setTextSize(size);v.setTextColor(color);
        if(bold)v.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
        v.setIncludeFontPadding(false);v.setPadding(0,dp(3),0,dp(3));return v;
    }
    private LinearLayout column(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.VERTICAL);return v;}
    private LinearLayout disclosure(String title){
        LinearLayout panel=column();panel.setVisibility(View.GONE);
        button(title,()->panel.setVisibility(panel.getVisibility()==View.GONE?View.VISIBLE:View.GONE));
        content.addView(panel);return panel;
    }
    private LinearLayout row(){LinearLayout v=new LinearLayout(this);v.setGravity(Gravity.CENTER_VERTICAL);return v;}
    private void gap(int height){View v=new View(this);content.addView(v,new LinearLayout.LayoutParams(1,dp(height)));}
    private LinearLayout card(int border){
        LinearLayout v=column();v.setPadding(dp(12),dp(10),dp(12),dp(10));v.setBackground(shape(Color.WHITE,border,14));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(8);content.addView(v,lp);return v;
    }
    private void screen(String title) {
        voiceStatus=null;heardView=null;voiceButton=null;clockView=null;shortageB=null;shortageU=null;shortageFeedback=null;
        root=column();root.setBackgroundColor(BG);root.setFitsSystemWindows(true);
        boolean working=currentScreen.equals("product") || currentScreen.equals("shortage");
        LinearLayout header=column();header.setBackgroundColor(SURFACE);header.setPadding(dp(16),dp(8),dp(16),dp(10));root.addView(header);
        if(working){
            LinearLayout top=row();header.addView(top);
            top.addView(label("Camión "+load.optString("camion","Demo")+" · Cancha "+court.optInt("numero"),12,MUTED,false),new LinearLayout.LayoutParams(0,-2,1));
            TextView badge=label(stageLabel(),12,0xff047857,true);badge.setPadding(dp(12),dp(5),dp(12),dp(5));badge.setBackground(shape(0xffd1fae5,0xffd1fae5,20));top.addView(badge);
            LinearLayout second=row();header.addView(second);
            second.addView(label("Producto "+(index+1)+" de "+products.length(),12,MUTED,false),new LinearLayout.LayoutParams(0,-2,1));
            clockView=label("",12,MUTED,false);second.addView(clockView);updateClock();
            ProgressBar progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setMax(Math.max(1,products.length()));progress.setProgress(check.optJSONObject("answers").length());
            progress.setProgressTintList(android.content.res.ColorStateList.valueOf(GREEN));progress.setProgressBackgroundTintList(android.content.res.ColorStateList.valueOf(BORDER));header.addView(progress,new LinearLayout.LayoutParams(-1,dp(6)));
        }else{
            header.addView(label("DEL PALACIO",11,GREEN,true));header.addView(label(title,22,INK,true));
            header.addView(label(user==null?"Operación de depósito":"Usuario: "+user.optString("username")+" · "+roleLabel(),13,MUTED,false));
        }
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);body=column();content=body;
        content.setPadding(dp(12),dp(12),dp(12),dp(16));scroll.addView(content);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        status=label("",14,INK,false);status.setVisibility(View.GONE);content.addView(status);
        if(currentScreen.equals("login") || currentScreen.equals("loads"))button(dark?"Modo claro":"Modo oscuro",this::toggleTheme);
        setContentView(root);
        if(demo)message("Demostración · No guarda datos");
    }
    private TextView text(String value, int size) {
        TextView v=label(value,size,size>=18?INK:MUTED,size>=18);content.addView(v);return v;
    }
    private EditText input(String hint, int type) {
        EditText v = new EditText(this); v.setHint(hint);v.setContentDescription(hint); v.setTextSize(16); v.setInputType(type); v.setSingleLine(true);
        v.setTextColor(INK);v.setHintTextColor(MUTED);v.setPadding(dp(14),dp(12),dp(14),dp(12));v.setBackground(shape(Color.WHITE,0xffcbd5e1,12));v.setMinimumHeight(dp(52));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(4);lp.bottomMargin=dp(12);content.addView(v,lp); return v;
    }
    private void button(String title, Runnable action) {
        styledButton(title,Color.WHITE,INK,BORDER,action);
    }
    private Button styledButton(String title,int fill,int ink,int border,Runnable action){
        if(dark && fill==INK && ink==Color.WHITE)ink=BG;
        if(dark && fill==0xfffff1f2)ink=0xfffda4af;
        Button b=new Button(this);b.setText(title);b.setAllCaps(false);b.setTextSize(15);b.setTextColor(ink);b.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));b.setMinHeight(dp(48));b.setMinimumHeight(dp(48));
        b.setPadding(dp(10),dp(8),dp(10),dp(8));b.setBackground(shape(fill,border,12));b.setStateListAnimator(null);
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(8);content.addView(b,lp);b.setOnClickListener(v->{if(!busy)action.run();});return b;
    }
    private void message(String value) { if (status != null) {status.setText(value);status.setVisibility(value.isEmpty()?View.GONE:View.VISIBLE);} }
    private void updateClock(){
        if(clockView==null || check==null)return;
        long seconds=(long)check.optDouble("active_seconds",0);
        if(!check.isNull("timer_started_at"))try{seconds+=Math.max(0,java.time.Duration.between(java.time.Instant.parse(check.optString("timer_started_at")),java.time.Instant.now()).getSeconds());}catch(Exception ignored){}
        clockView.setText(String.format(Locale.ROOT,"%s %02d:%02d:%02d",check.isNull("timer_started_at")?"Pausado":"Tiempo activo",seconds/3600,(seconds/60)%60,seconds%60));
    }
    private void voicePanel(){
        LinearLayout parent=content;content=card(BORDER);
        LinearLayout controls=row();content.addView(controls);LinearLayout panel=content;content=controls;
        voiceButton=styledButton(voice?"Parar voz":"Activar voz",INK,Color.WHITE,INK,()->{
            if(voice){voice=false;stopAudio();updateVoiceUi("Voz desactivada");}else enableVoice();
        });voiceButton.setLayoutParams(new LinearLayout.LayoutParams(dp(112),-2));
        voiceStatus=label(voice?"Preparando…":"Voz desactivada",13,MUTED,false);voiceStatus.setPadding(dp(12),0,0,0);controls.addView(voiceStatus,new LinearLayout.LayoutParams(0,-2,1));content=panel;
        gap(10);heardView=text(lastHeard.isEmpty()?"Todavía no escuché un comando":"Escuché: “"+lastHeard+"”",14);heardView.setTextColor(dark?0xff6ee7b7:0xff047857);heardView.setPadding(dp(12),dp(10),dp(12),dp(10));heardView.setBackground(shape(0xffecfdf5,0xffa7f3d0,8));
        String guidance=currentScreen.equals("shortage")?"Decí, por ejemplo: un bulto y luego dos unidades.":
            currentScreen.equals("loads")?"Comandos: iniciar, continuar o actualizar tareas.":
            currentScreen.equals("courts")?"Comandos: iniciar cancha o cancelar.":
            "Comandos: correcto, faltante, anterior, siguiente y repetir.";
        text(guidance,12);content=parent;
    }
    private void updateVoiceUi(String state){if(voiceButton!=null)voiceButton.setText(voice?"Parar voz":"Activar voz");if(voiceStatus!=null)voiceStatus.setText(state);}
    private interface Work<T> { T run() throws Exception; }
    private interface Result<T> { void accept(T value) throws Exception; }
    private <T> void task(Work<T> work, Result<T> done) {
        if (busy) return;
        busy = true; int version = requestVersion; stopMic(); message("Procesando…");
        network.execute(() -> {
            try {
                T result = work.run();
                handler.post(() -> {
                    if (isDestroyed() || version != requestVersion) return;
                    busy = false;
                    try { done.accept(result); } catch (Exception e) { error(e); }
                });
            } catch (Exception e) { handler.post(() -> { if (!isDestroyed() && version == requestVersion) { busy = false; error(e); } }); }
        });
    }
    private void error(Exception error) {
        if(currentScreen.equals("shortage") && shortageFeedback!=null)shortageFeedback.setText(error.getMessage());
        if(!pendingAnswer() && currentScreen.equals("product"))product();
        if(pendingAnswer()) new AlertDialog.Builder(this)
            .setTitle("Registro por verificar")
            .setMessage("No repitas la respuesta. Primero consultá si quedó guardada en el servidor.\n\nMotivo: "+errorReason(error))
            .setNegativeButton("Más tarde",null)
            .setPositiveButton("Verificar guardado",(d,w)->recoverAnswer(false)).show();
        boolean recoverVoice=voice && !pendingAnswer() && (currentScreen.equals("product") || currentScreen.equals("shortage"));
        boolean announce=voice;
        if(voice && !recoverVoice){voice=false;stopAudio();updateVoiceUi("Voz detenida · Revisá el resultado antes de continuar");}
        else if(recoverVoice)stopMic();
        message(error.getMessage() == null ? "No se pudo completar. Revisá la conexión y reintentá." : error.getMessage());
        if(announce && ttsReady)speak(recoverVoice?"No pude completar la operación. Revisá la pantalla y repetí el comando.":"No pude completar la operación. Revisá la pantalla y el estado del producto antes de activar la voz nuevamente.");
    }
    private String errorReason(Exception error){
        if(error instanceof java.net.SocketTimeoutException)return "El servidor tardó demasiado en responder.";
        if(error instanceof java.net.UnknownHostException)return "No hay conexión a Internet o no se encuentra el servidor.";
        if(error instanceof java.net.ConnectException)return "No se pudo conectar con el servidor.";
        String value=error.getMessage();return value==null||value.trim().isEmpty()?"No se recibió una respuesta confirmable.":value;
    }
    private boolean definitiveFailure(Exception error){
        if(!(error instanceof Api.HttpError))return false;
        int status=((Api.HttpError)error).status;
        return status>=400&&status<500&&status!=408&&status!=429;
    }
    private JSONObject json(String method, String path, JSONObject body) throws Exception { return new JSONObject(api.request(method,path,body)); }
    private static JSONObject obj(Object... pairs) {
        JSONObject o = new JSONObject();
        try { for (int i=0;i<pairs.length;i+=2) o.put((String)pairs[i],pairs[i+1]); } catch (JSONException e) { throw new IllegalArgumentException(e); }
        return o;
    }
    private boolean isController(){return !demo && user!=null && user.optString("role").equals("controlador");}
    private boolean isPalletizer(){return !demo && user!=null && user.optString("role").equals("palletizador");}
    private int stage() { return isController()?currentStage:!demo && user != null && user.optString("role").equals("palletizador") ? 4 : 0; }
    private String stageLabel(){return stage()==4?"Pallets":stage()==2?"Control 2":stage()==1?"Control 1":"Picking";}
    private String roleLabel(){return isController()?"Control de cargas":stage()==4?"Pallets completos":"Picking";}
    private String path() {
        if(pallet!=null && (isController() || isPalletizer()))return "/load-control/loads/"+load.optInt("id")+"/pallets/"+pallet.optString("id")+"/checks/"+stage()+"/"+check.optString("id");
        return "/load-control/loads/" + load.optInt("id") + "/courts/" + court.optInt("numero") + "/checks/" + stage() + "/" + check.optString("id");
    }
    private String pendingKey(){return "pending_answer:"+api.base+":"+user.optInt("id");}
    private String voiceTemplatesKey(String base){return "voice_templates:"+base;}
    private void loadVoiceTemplates(String base){
        try{voiceTemplates=new JSONObject(getPreferences(0).getString(voiceTemplatesKey(base),"{}"));}
        catch(Exception ignored){voiceTemplates=new JSONObject();}
    }
    private String voiceText(String key,String fallback,Object... values){
        if(voiceTemplates.has(key) && voiceTemplates.isNull(key))return "";
        String result=voiceTemplates.optString(key,fallback);
        for(int i=0;i+1<values.length;i+=2)result=result.replace("{"+values[i]+"}",String.valueOf(values[i+1]));
        return result;
    }
    private boolean pendingAnswer(){return !demo && api!=null && user!=null && getPreferences(0).contains(pendingKey());}
    private void clearPendingAnswer(){if(api!=null&&user!=null)getPreferences(0).edit().remove(pendingKey()).commit();}
    private void recoverAnswer(boolean retry){
        if(!pendingAnswer())return;
        try {
            JSONObject pending=new JSONObject(getPreferences(0).getString(pendingKey(),""));
            String endpoint=pending.getString("path");JSONObject payload=pending.getJSONObject("payload");
            task(()->{
                JSONObject receipt=json("GET",endpoint+"/receipts/"+payload.getString("request_id"),null);
                if(!receipt.optBoolean("found") && retry)return obj("found",true,"check",json("POST",endpoint+"/answer",payload));
                return receipt;
            },receipt->{
                if(!receipt.optBoolean("found")){
                    String reason=pending.optString("last_error","La conexión se interrumpió antes de recibir la confirmación.");
                    new AlertDialog.Builder(this).setTitle("Confirmado: no se guardó")
                        .setMessage("El servidor no tiene este registro.\n\nMotivo original: "+reason+"\n\nPodés reenviar exactamente la misma respuesta o descartarla para corregir los datos.")
                        .setNegativeButton("Descartar y corregir",(d,w)->{clearPendingAnswer();product();message("Registro descartado. Revisá los datos y volvé a enviarlo.");})
                        .setPositiveButton("Reintentar ahora",(d,w)->recoverAnswer(true)).show();return;
                }
                clearPendingAnswer();
                if(receipt.optBoolean("superseded")){listLoads();message("El registro existió pero fue reemplazado. Revisá la tarea antes de continuar.");return;}
                if(currentScreen.equals("product") || currentScreen.equals("shortage")){
                    if(path().equals(endpoint) && products.optJSONObject(index).optString("sku").equals(payload.optString("sku"))){check=receipt.getJSONObject("check");afterAnswer();message("Guardado confirmado por el servidor.");return;}
                }
                listLoads();message("Guardado confirmado por el servidor.");
            });
        }catch(Exception e){error(e);}
    }
    private void pendingControls(){
        if(!pendingAnswer())return;
        text("Registro por verificar",18);
        text("No repitas la carga. Primero comprobá si el servidor la guardó. Mientras tanto no se puede finalizar el control.",14);
        button("Verificar guardado",()->recoverAnswer(false));
        button("Reintentar mismo registro",()->new AlertDialog.Builder(this).setTitle("Reintentar registro")
            .setMessage("Primero se consultará el comprobante. Solo si no existe se enviará el mismo registro.")
            .setNegativeButton("Cancelar",null).setPositiveButton("Verificar y reintentar",(d,w)->recoverAnswer(true)).show());
    }
    private void login() {
        PushRegistration.logout(this);
        requestVersion++; knownTasks=null;
        currentScreen = "login"; load = null; court = null; filter = "Todos";
        voice = false; stopAudio(); check = null; demo = false; api = null; user = null; screen("Picking por voz");
        content=card(BORDER);text("Tu jornada, paso a paso",22);text("Ingresá para ver tus cargas y preparar cada producto con asistencia por voz.",14);gap(10);
        LinearLayout loginForm=content, serverFields=column();content.addView(serverFields);content=serverFields;text("Dirección del servidor",13);
        EditText host = input("https://servidor", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        host.setText(getPreferences(0).getString("server", "https://picking-production.up.railway.app"));
        serverFields.setVisibility(View.GONE);content=loginForm;
        text("Usuario",13);
        EditText name = input("Usuario", InputType.TYPE_CLASS_TEXT);
        text("Contraseña",13);
        EditText password = input("Contraseña", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        styledButton("Ingresar →", GREEN,Color.WHITE,GREEN,() -> {
            try { api = new Api(host.getText().toString()); loadVoiceTemplates(api.base); } catch (Exception e) { error(e); return; }
            String username = name.getText().toString().trim(), secret = password.getText().toString();
            if (username.isEmpty() || secret.isEmpty()) { message("Completá usuario y contraseña."); return; }
            task(() -> {
                JSONObject auth = json("POST","/auth/login",obj("username",username,"password",secret));
                JSONObject person = auth.getJSONObject("user");
                if (!Arrays.asList("operador", "palletizador", "controlador").contains(person.getString("role"))) throw new Exception("Esta app está destinada a cuentas operativas.");
                api.token = auth.getString("token");
                // Fail closed: the native app cannot silently show every court.
                JSONObject permissions = json("GET","/load-control/my-courts",null);
                JSONArray courts = permissions.getJSONArray("courts");
                assigned.clear(); for (int i=0;i<courts.length();i++) assigned.add(courts.getInt(i));
                try{
                    JSONObject runtime=json("GET","/voice-templates/runtime",null);JSONObject downloaded=runtime.getJSONObject("templates");
                    getPreferences(0).edit().putString(voiceTemplatesKey(api.base),downloaded.toString()).apply();
                    voiceTemplates=downloaded;voiceSettings=runtime.optJSONObject("settings");if(voiceSettings==null)voiceSettings=new JSONObject();voiceCommands=runtime.optJSONObject("commands");if(voiceCommands==null)voiceCommands=new JSONObject();speechRate=(float)runtime.optDouble("speech_rate",1);freshnessWarningDays=runtime.optInt("freshness_warning_days",30);
                }catch(Exception ignored){ }
                return person;
            }, person -> {
                user = person; password.setText(""); getPreferences(0).edit().putString("server",api.base).apply(); listLoads();
            });
        });
        button("Configurar servidor",()->serverFields.setVisibility(serverFields.getVisibility()==View.GONE?View.VISIBLE:View.GONE));
        content=body;
        content=card(BORDER);text("Probá antes de empezar",18);text("Conocé los comandos y comprobá el audio sin modificar las cargas.",14);
        button("Probar voz sin guardar datos", this::demo);
        content=body;text("Versión 0.25.0 · Para guardar necesitás conexión.",12);
    }
    private void demo() {
        demo = true; user = obj("id",0,"username","Demostración"); load = obj("id",0,"reparto","DEMO","camion","12");lastHeard="";
        products = new JSONArray().put(obj("sku","DEMO-1","descripcion","Agua mineral de un litro","bultos",2,"unidades",3))
            .put(obj("sku","DEMO-2","descripcion","Gaseosa de dos litros","bultos",4,"unidades",0));
        court = obj("numero",1,"productos",products); check = obj("id","demo","answers",new JSONObject(),"timer_started_at",java.time.Instant.now().toString()); index=0;
        product();
    }
    private String processState(JSONObject c) {
        JSONArray checks = c.optJSONObject("status").optJSONArray("checks");
        if(isController()){
            JSONObject first=checkAt(checks,1),second=checkAt(checks,2);
            if(second!=null)return second.optString("status").equals("done")?"Finalizados":second.isNull("timer_started_at")?"Pausados":"En curso";
            if(first!=null && first.optString("status").equals("done"))return "Sin iniciar";
            if(first!=null)return first.isNull("timer_started_at")?"Pausados":"En curso";
            return "Sin iniciar";
        }
        for (int i=0;i<checks.length();i++) { JSONObject x=checks.optJSONObject(i); if (x.optInt("stage") == stage())
            return x.optString("status").equals("done") ? "Finalizados" : x.isNull("timer_started_at") ? "Pausados" : "En curso"; }
        return "Sin iniciar";
    }
    private JSONObject checkAt(JSONArray checks,int wanted){
        if(checks==null)return null;
        for(int i=0;i<checks.length();i++){JSONObject value=checks.optJSONObject(i);if(value!=null && value.optInt("stage")==wanted)return value;}
        return null;
    }
    private boolean canSeeCourt(JSONObject c) { return assigned.contains(c.optInt("numero")) || c.optBoolean("assistance", false); }
    private boolean matches(JSONObject c) { return canSeeCourt(c) && (filter.equals("Todos") || filter.equals(processState(c))); }
    private String amount(JSONObject data,String key) {
        if(data.isNull(key) || !data.has(key))return "Pendiente";
        return java.text.NumberFormat.getNumberInstance(new java.util.Locale("es","AR")).format(data.optDouble(key));
    }
    private String summarySpeech(JSONObject summary) {
        if(summary==null)return "El resumen del camión no está disponible. ";
        if(summary.isNull("pallets"))return "Plan de armado pendiente. Consultá al supervisor para conocer tus pallets y cantidades asignadas.";
        String speech="Carga total del camión: "+summary.optInt("loads")+" repartos, "+summary.optInt("courts")+" canchas. "+amount(summary,"pallets")+" pallets físicos previstos. ";
        JSONObject mine=summary.optJSONObject("mine");
        if(summary.optString("separation_policy").equals("reparto_v1"))speech+="Cada reparto se arma por separado. No mezcles repartos en un pallet. ";
        if(mine!=null){
            speech+="Tu trabajo: "+mine.optInt("loads")+" repartos y "+mine.optInt("courts")+" canchas. "+amount(mine,"bultos")+" bultos y "+amount(mine,"unidades")+" unidades. Participa en "+amount(mine,"pallets")+" pallets. ";
            if(!mine.isNull("hl"))speech+=amount(mine,"hl")+" hectolitros. ";
            if(stage()==0 && mine.optInt("full_pallets_info")>0)speech+=mine.optInt("full_pallets_info")+" pallets completos se preparan por separado. ";
        }
        return speech;
    }
    private String destinations(JSONObject product) {
        if(!demo && stage()==4 && !product.optString("pallet_group").isEmpty())return "Grupo de pallets completos "+product.optString("pallet_group")+". Reparto "+product.optString("reparto")+". ";
        if(demo || stage()!=0 || load==null || court==null)return "";
        JSONArray explicit=product.optJSONArray("pallet_destinations");
        if(explicit!=null && explicit.length()>0){
            StringBuilder instructions=new StringBuilder();
            for(int i=0;i<explicit.length();i++){
                JSONObject destination=explicit.optJSONObject(i);if(destination==null)continue;
                String placement=destination.optString("placement");
                if(placement.equals("base"))instructions.append("Ubicá como base. ");
                else if(placement.equals("arriba"))instructions.append("Ubicá arriba de la base. ");
                instructions.append(ProductSpeech.destination(destination.optString("pallet_id"),destination.optInt("bultos"),destination.optInt("unidades"),destination.optBoolean("shared")));
            }
            if(instructions.length()>0)return instructions.toString();
        }
        JSONObject summary=load.optJSONObject("truck_summary");
        JSONObject mine=summary==null?null:summary.optJSONObject("mine");
        JSONArray allocations=mine==null?null:mine.optJSONArray("allocations");
        StringBuilder result=new StringBuilder();
        if(allocations!=null)for(int i=0;i<allocations.length();i++){
            JSONObject pallet=allocations.optJSONObject(i);JSONArray items=pallet.optJSONArray("items");
            if(items==null)continue;
            for(int j=0;j<items.length();j++){
                JSONObject item=items.optJSONObject(j);
                if(item.optInt("load_id")==load.optInt("id") && item.optInt("court")==court.optInt("numero") && item.optString("sku").equals(product.optString("sku")))
                    result.append(item.optString("placement").equals("base")?"Ubicá como base. ":"Ubicá arriba de la base. ").append(ProductSpeech.destination(pallet.optString("id"),item.optInt("bultos"),item.optInt("unidades"),pallet.optBoolean("shared")));
            }
        }
        return result.length()==0?"Destino de pallet no disponible. Actualizá la tarea; si continúa, consultá al supervisor. ":result.toString();
    }
    private void truckSummary(JSONObject summary,boolean waiting) {
        if(summary==null)return;
        content=card(BORDER);text("Este camión · Carga seleccionada",20);
        if(summary.optString("separation_policy").equals("reparto_v1"))text("Cada reparto tiene sus propios pallets. No mezclar repartos ni camiones.",16);
        JSONArray groups=summary.optJSONArray("load_plans");
        if(groups!=null)for(int i=0;i<groups.length();i++){
            JSONObject group=groups.optJSONObject(i);
            text("Reparto "+group.optString("reparto")+": "+group.optInt("total_pallets")+" pallets estimados · "+(group.optString("assembly_mode").equals("compact")?"Supermercado / autoelevador":"Normal separado"),15);
        }
        if(!isController())button("Escuchar resumen del camión",()->speak(summarySpeech(summary)));
        if(summary.isNull("pallets")){
            text("Plan de armado pendiente",20);
            text("No hay un plan aprobado vigente para calcular tus pallets y cantidades asignadas. Consultá al supervisor.",15);
            text("Carga total: "+amount(summary,"bultos")+" bultos + "+amount(summary,"unidades")+" unidades",16);
            content=body;return;
        }
        text(summary.optInt("loads")+" repartos · "+summary.optInt("courts")+" canchas",15);
        text(amount(summary,"bultos")+" bultos + "+amount(summary,"unidades")+" unidades · "+amount(summary,"hl")+" HL",16);
        text("Pallets físicos previstos: "+amount(summary,"pallets")+" / "+amount(summary,"capacity")+" de capacidad",18);
        text(amount(summary,"full_pallets")+" completos + "+amount(summary,"picking_pallets")+" de picking",14);
        if(summary.isNull("hl"))text("Faltan factores de HL en el catálogo. El volumen está incompleto.",13);
        if(waiting){text("Esperando revisión y aprobación del supervisor para comenzar.",16);content=body;return;}
        JSONObject mine=summary.optJSONObject("mine");
        if(mine!=null){
            text("Tu trabajo en este camión",18);
            text(mine.optInt("loads")+" repartos · "+mine.optInt("courts")+" canchas · "+mine.optInt("finished_tasks")+" / "+mine.optInt("tasks")+" tareas terminadas",14);
            text(amount(mine,"bultos")+" bultos + "+amount(mine,"unidades")+" unidades · "+amount(mine,"hl")+" HL",16);
            text("Tu carga ocupa "+amount(mine,"pallets")+" pallets del plan.",15);
            if(stage()==0)text(mine.optInt("full_pallets_info")+" pallets completos de tus canchas se preparan por separado.",13);
            JSONArray allocations=mine.optJSONArray("allocations");
            if(stage()==0 && allocations!=null && allocations.length()>0){
                LinearLayout container=content,details=new LinearLayout(this);details.setOrientation(LinearLayout.VERTICAL);details.setVisibility(View.GONE);
                button("Ver / ocultar distribución en pallets",()->details.setVisibility(details.getVisibility()==View.GONE?View.VISIBLE:View.GONE));
                container.addView(details);content=details;
                text("Respetá los identificadores del plan. Un pallet compartido se cuenta una sola vez en el total del camión.",13);
                for(int i=0;i<allocations.length();i++){
                    JSONObject pallet=allocations.optJSONObject(i);text("Pallet "+pallet.optString("id")+(pallet.optBoolean("shared")?" · Compartido con otras canchas":""),16);
                    JSONArray items=pallet.optJSONArray("items");
                    if(items!=null)for(int j=0;j<items.length();j++){JSONObject p=items.optJSONObject(j);text("R. "+p.optString("reparto")+" · Cancha "+p.optInt("court")+" · "+p.optString("descripcion")+": "+p.optInt("bultos")+" b + "+p.optInt("unidades")+" u",13);}
                }
                content=container;
            }
        }
        content=body;
    }
    private void listLoads() {
        if(!demo && api!=null && user!=null)PushRegistration.sync(this,api);
        currentScreen = "loads"; check = null; court = null;voiceNextLoadId=0;voiceNextCourt=0;voiceCourtCandidate=null;voiceConfirmFinish=false;
        stopAudio(); check=null; screen("Tu próximo trabajo");
        content=card(BORDER);text("Hola, "+user.optString("username"),22);
        List<Integer> sortedCourts=new ArrayList<>(assigned);Collections.sort(sortedCourts);
        TextView assignments=text("Tus canchas: " + sortedCourts,14);content=body;
        if(!isController())voicePanel();
        pendingControls();
        task(this::fetchQueue, response -> {
            queueVersion=queueVersion(response);
            if(response.has("voice_templates")){
                voiceTemplates=response.getJSONObject("voice_templates");
                getPreferences(0).edit().putString(voiceTemplatesKey(api.base),voiceTemplates.toString()).apply();
            }
            if(response.has("voice_settings") && !response.isNull("voice_settings"))voiceSettings=response.getJSONObject("voice_settings");
            if(response.has("voice_commands") && !response.isNull("voice_commands")){voiceCommands=response.getJSONObject("voice_commands");if(voiceSession!=null)voiceSession.configureGrammar(VoiceCommands.grammar(voiceCommands));}
            speechRate=(float)response.optDouble("speech_rate",speechRate);
            freshnessWarningDays=response.optInt("freshness_warning_days",freshnessWarningDays);
            operators=response.optJSONArray("operators");if(operators==null)operators=new JSONArray();
            assigned.clear(); JSONArray permissions=response.getJSONObject("permissions").getJSONArray("courts");
            for(int i=0;i<permissions.length();i++) assigned.add(permissions.getInt(i));
            List<Integer> refreshed=new ArrayList<>(assigned);Collections.sort(refreshed);assignments.setText("Tus canchas: "+refreshed);
            JSONArray trucks=response.getJSONArray("trucks");
            if(isController()){
                List<JSONObject> ordered=new ArrayList<>();for(int i=0;i<trucks.length();i++)ordered.add(trucks.getJSONObject(i));
                ordered.sort(Comparator.comparing(item->{JSONObject progress=item.optJSONObject("control_progress");return progress!=null&&progress.optBoolean("completed");}));
                JSONArray sorted=new JSONArray();for(JSONObject item:ordered)sorted.put(item);trucks=sorted;
            }
            if(announceQueue){
                announceQueue=false;
                if(!isController()){
                    if(trucks.length()==0)speak("Cancha finalizada. No tenés más camiones habilitados pendientes.");
                    else {JSONObject next=trucks.getJSONObject(0);speak("Cancha finalizada. Tu camión actual es "+next.optString("truck")+". "+summarySpeech(next.optJSONObject("summary"))+"Elegí el reparto y la cancha para continuar.");}
                }
            }
            Set<String> availableTasks=new HashSet<>();
            for(int t=0;t<trucks.length();t++) {
                JSONObject truck=trucks.getJSONObject(t);
                if(truck.optString("planning_status").equals("pending"))continue;
                JSONArray items=truck.getJSONArray("loads");
                for(int l=0;l<items.length();l++) {
                    JSONObject item=items.getJSONObject(l); JSONArray courts=item.getJSONArray("canchas");
                    for(int c=0;c<courts.length();c++) {
                        JSONObject candidate=courts.getJSONObject(c);
                        if(canSeeCourt(candidate) && candidate.optInt("cantidad")>0
                            && (isController() || candidate.optBoolean("can_prepare",false)) && !processState(candidate).equals("Finalizados"))
                            availableTasks.add(item.optInt("id")+":"+candidate.optInt("numero"));
                    }
                }
            }
            Set<String> newTasks=new HashSet<>(availableTasks);
            if(knownTasks!=null)newTasks.removeAll(knownTasks);
            if(knownTasks!=null && !newTasks.isEmpty()) {
                text("Tenés nuevas tareas habilitadas. Revisá tu próximo trabajo.",18);
                if(!isController())speak(voiceText("new_tasks","Tenés nuevas tareas habilitadas. Revisá tu próximo trabajo."));
            }
            knownTasks=availableTasks;
            text("Actualización automática cada 15 segundos mientras estés en esta pantalla.",13);
            int found=0;
            for(int t=0;t<trucks.length();t++) { JSONObject truck=trucks.getJSONObject(t); JSONArray loads=truck.getJSONArray("loads");
                JSONObject controlProgress=truck.optJSONObject("control_progress");boolean controlDone=isController()&&controlProgress!=null&&controlProgress.optBoolean("completed");
                LinearLayout truckCard=card(controlDone?0xff64748b:BORDER);if(controlDone)truckCard.setAlpha(0.58f);content=truckCard;text("Camión "+truck.optString("truck"),19);
                text(truck.optString("load_date")+" · "+loads.length()+" cargas",13);
                JSONObject summary=truck.optJSONObject("summary"), mine=summary==null?null:summary.optJSONObject("mine");
                if(mine!=null && !summary.isNull("pallets"))text(mine.optInt("finished_tasks")+" de "+mine.optInt("tasks")+" tareas finalizadas",18);
                if(isController()){
                    if(controlProgress!=null)text(controlProgress.optString("label"),16);
                    text(controlDone?"Tu trabajo en este camión ya terminó. Podés consultar el resultado.":"Elegí este camión para ver sus pallets y el avance de ambos controles.",14);
                    styledButton(controlDone?"Ver resultado":"Ver pallets del camión →",controlDone?SURFACE:GREEN,controlDone?MUTED:Color.WHITE,controlDone?BORDER:GREEN,()->openControlTruck(truck));
                    content=body;
                    continue;
                }
                if(isPalletizer()){
                    text("Pallets completos de todos los repartos y canchas del camión.",14);
                    styledButton("Ver pallets completos →",GREEN,Color.WHITE,GREEN,()->openFullPalletTruck(truck));
                    content=body;
                    continue;
                }
                JSONObject nextLoad=null,nextCourt=null;int best=99;
                for(int l=0;l<loads.length();l++){
                    JSONObject candidate=loads.getJSONObject(l);JSONArray candidates=candidate.getJSONArray("canchas");
                    for(int c=0;c<candidates.length();c++){
                        JSONObject taskCourt=candidates.getJSONObject(c);
                        if(!canSeeCourt(taskCourt) || taskCourt.optInt("cantidad")==0 || (!isController() && !taskCourt.optBoolean("can_prepare",true)))continue;
                        String state=processState(taskCourt);int rank=state.equals("En curso")?0:state.equals("Pausados")?1:state.equals("Sin iniciar")?2:99;
                        if(rank<best){best=rank;nextLoad=candidate;nextCourt=taskCourt;}
                    }
                }
                if(nextLoad!=null && !truck.optString("planning_status").equals("pending")){
                    final int loadId=nextLoad.optInt("id"),courtNumber=nextCourt.optInt("numero");
                    if(voiceNextLoadId==0){voiceNextLoadId=loadId;voiceNextCourt=courtNumber;}
                    text("Próxima tarea: reparto "+nextLoad.optString("reparto")+" · Cancha "+courtNumber,16);
                    styledButton(isController()?"Continuar control →":"Continuar picking →",GREEN,Color.WHITE,GREEN,()->{filter="Todos";openLoad(loadId,courtNumber);});
                }else text(truck.optString("planning_status").equals("pending")?"Esperando aprobación del supervisor":"Sin tareas pendientes en este camión",16);
                content=body;
                content=disclosure("Ver resumen y pallets del camión");
                truckSummary(summary,truck.optString("planning_status").equals("pending"));
                content=body;LinearLayout tasksPanel=disclosure("Elegir tarea");content=tasksPanel;
                if(!filter.equals("Todos"))tasksPanel.setVisibility(View.VISIBLE);
                Spinner options=new Spinner(this);options.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"Todos","En curso","Sin iniciar","Pausados","Finalizados"}));
                content.addView(options);options.setSelection(Arrays.asList("Todos","En curso","Sin iniciar","Pausados","Finalizados").indexOf(filter));
                button("Aplicar filtro",()->{filter=options.getSelectedItem().toString();listLoads();});
                for(int l=0;l<loads.length();l++) { JSONObject item=loads.getJSONObject(l); JSONArray courts=item.getJSONArray("canchas"); boolean show=false;
                    for(int c=0;c<courts.length();c++) if(matches(courts.getJSONObject(c))) show=true;
                    if(show) {
                        found++;content=tasksPanel;LinearLayout loadPanel=disclosure("Reparto "+item.optString("reparto"));content=loadPanel;
                        int done=0,total=0;
                        for(int c=0;c<courts.length();c++){
                            JSONObject taskCourt=courts.getJSONObject(c);
                            if(!canSeeCourt(taskCourt))continue;
                            total++;if(processState(taskCourt).equals("Finalizados"))done++;
                        }
                        text("Tus canchas: "+done+" de "+total+" finalizadas",14);
                        for(int c=0;c<courts.length();c++){
                            JSONObject taskCourt=courts.getJSONObject(c);if(!matches(taskCourt))continue;
                            gap(8);text("Cancha "+taskCourt.optInt("numero")+" · "+processState(taskCourt),18);
                            if(taskCourt.optBoolean("assistance",false))text("Refuerzo de hoy · Solo los productos que te asignó el supervisor",14);
                            text(taskCourt.optInt("cantidad")+" productos",14);
                            button("Ver cancha "+taskCourt.optInt("numero")+" →",()->openLoad(item.optInt("id"),taskCourt.optInt("numero")));
                        }
                        content=tasksPanel;
                    }
                }
                if(isController()){
                    JSONObject truckStatus=truck.optJSONObject("status");
                    content=body;
                    if(truckStatus!=null && truckStatus.optBoolean("complete") && truckStatus.isNull("assets"))
                        styledButton("Registrar activos de salida",GREEN,Color.WHITE,GREEN,()->startAssets(truck));
                    else if(truckStatus!=null && !truckStatus.isNull("assets"))text("Activos de salida registrados",14);
                }
                content=body;
            }
            message(trucks.length()==0 ? "No tenés camiones habilitados pendientes. Actualizá o consultá al supervisor." : "");
            button("Actualizar trabajo",this::listLoads);
            content=disclosure("Mi sesión");if(!isController())button("Notificaciones · Probar Firebase", () -> PushDiagnostics.show(this));button("Cerrar sesión", this::login);text("Del Palacio · Android 0.25.0",12);content=body;
        });
    }
    private void openLoad(int id) {
        openLoad(id,0);
    }
    private void openControlTruck(JSONObject truck){
        controlTruck=truck;pallet=null;check=null;
        task(()->json("GET","/load-control/trucks/"+truck.optInt("id")+"/control-pallets",null),this::showControlPallets);
    }
    private void openFullPalletTruck(JSONObject truck){
        controlTruck=truck;pallet=null;check=null;currentStage=4;
        task(()->json("GET","/load-control/trucks/"+truck.optInt("id")+"/full-pallets",null),this::showFullPallets);
    }
    private void showFullPallets(JSONObject board){
        currentScreen="full_pallet_board";pallet=null;check=null;
        screen("Camión "+board.optString("truck"));button("Volver a camiones",this::listLoads);
        text("Pallets completos",20);text("Cada pallet es una tarea independiente. La cancha se muestra solo como origen informativo.",13);
        JSONArray rows=board.optJSONArray("pallets");if(rows==null)rows=new JSONArray();
        for(int i=0;i<rows.length();i++){
            JSONObject item=rows.optJSONObject(i),assembly=item.optJSONObject("assembly");
            String state=assembly==null||assembly.length()==0?(item.optBoolean("available")?"Disponible":"En espera"):
                "done".equals(assembly.optString("status"))?"Finalizado":assembly.has("timer_started_at")?"En curso":"Pausado";
            content=card("Finalizado".equals(state)?0xff64748b:item.optBoolean("available")?GREEN:BORDER);
            text("Pallet "+item.optString("id")+" · "+state,18);
            text("Reparto "+item.optString("reparto")+" · Origen cancha "+item.optInt("owner_court"),13);
            JSONArray items=item.optJSONArray("items");JSONObject product=items==null?null:items.optJSONObject(0);
            if(product!=null){text(product.optString("descripcion"),16);text(product.optInt("bultos")+" bultos · Frescura "+(freshnessText(product.optString("fecha_frescura")).isEmpty()?"no informada":freshnessText(product.optString("fecha_frescura"))),13);}
            if(item.optBoolean("available") || "En curso".equals(state) || "Pausado".equals(state))
                styledButton("Finalizado".equals(state)?"Finalizado":"Preparar pallet →",GREEN,Color.WHITE,GREEN,()->startFullPallet(item));
            else if(!"Finalizado".equals(state))text(item.optString("blocked_reason","Esperando picking del reparto"),13);
            content=body;
        }
        if(rows.length()==0)message("Este camión no tiene pallets completos en el plan aprobado.");
        else if(board.optBoolean("completed"))message("Todos los pallets completos de este camión están terminados.");
    }
    private void startFullPallet(JSONObject selected){
        currentStage=4;pallet=selected;court=obj("numero",selected.optInt("owner_court"));
        task(()->json("POST","/load-control/loads/"+selected.optInt("load_id")+"/pallets/"+selected.optString("id")+"/start/4",obj()),started->{
            check=started;products=started.optJSONArray("products");if(products==null)products=new JSONArray();
            load=obj("id",selected.optInt("load_id"),"reparto",selected.optString("reparto"),"camion",controlTruck.optString("truck"));
            automaticallySpokenProducts.clear();index=0;product();
        });
    }
    private String palletControlStatus(JSONObject control){
        if(control==null || control.length()==0)return "Sin iniciar";
        if(control.optString("status").equals("done"))return "Finalizado";
        return control.isNull("timer_started_at")?"Pausado":"En curso";
    }
    private void showControlPallets(JSONObject board){
        currentScreen="pallet_board";pallet=null;check=null;
        screen("Camión "+board.optString("truck"));button("Volver a camiones",this::listLoads);
        JSONObject assignments=board.optJSONObject("assignments");if(assignments==null)assignments=new JSONObject();
        JSONObject firstOwner=assignments.optJSONObject("1"),secondOwner=assignments.optJSONObject("2");
        int userId=user.optInt("id"),myStage=0;
        if(firstOwner!=null && firstOwner.optInt("user_id")==userId)myStage=1;
        else if(secondOwner!=null && secondOwner.optInt("user_id")==userId)myStage=2;
        else if(firstOwner==null)myStage=1;
        else if(secondOwner==null && firstOwner.optInt("user_id")!=userId)myStage=2;
        final int controlStage=myStage;
        text("Control 1: "+(firstOwner==null?"sin asignar":firstOwner.optString("username")),16);
        text("Control 2: "+(secondOwner==null?"sin asignar":secondOwner.optString("username")),16);
        if(board.optBoolean("control2_complete"))text("Camión finalizado en ambos controles",18);
        else if(board.optBoolean("control1_complete"))text("Control 1 del camión finalizado",18);
        else text("Los pallets se habilitan individualmente al finalizar la etapa anterior.",14);
        JSONObject truckStatus=board.optJSONObject("status");
        if(truckStatus!=null && truckStatus.optBoolean("complete") && truckStatus.isNull("assets"))
            styledButton("Registrar activos de salida",GREEN,Color.WHITE,GREEN,()->startAssets(controlTruck));
        else if(truckStatus!=null && !truckStatus.isNull("assets"))text("Activos de salida registrados",14);
        JSONArray pallets=board.optJSONArray("pallets");if(pallets==null)pallets=new JSONArray();
        for(int i=0;i<pallets.length();i++){
            JSONObject item=pallets.optJSONObject(i),controls=item.optJSONObject("controls");
            JSONObject first=controls==null?null:controls.optJSONObject("1"),second=controls==null?null:controls.optJSONObject("2");
            content=card(item.optBoolean("assembly_done")?BORDER:0xff64748b);
            text("Pallet "+item.optString("id")+" · Reparto "+item.optString("reparto"),18);
            text("Cancha "+item.optInt("owner_court")+" · "+item.optJSONArray("items").length()+" productos",13);
            text("Control 1: "+palletControlStatus(first)+(first!=null&&!first.optString("username").isEmpty()?" · "+first.optString("username"):""),13);
            text("Control 2: "+palletControlStatus(second)+(second!=null&&!second.optString("username").isEmpty()?" · "+second.optString("username"):""),13);
            if(!item.optBoolean("assembly_done"))text("Todavía en armado",14);
            else if(controlStage==1 && item.optBoolean("control1_available"))styledButton("Controlar pallet →",GREEN,Color.WHITE,GREEN,()->startPallet(item,1));
            else if(controlStage==2 && item.optBoolean("control2_available"))styledButton("Controlar pallet →",GREEN,Color.WHITE,GREEN,()->startPallet(item,2));
            else if(controlStage==0)text("Este camión ya está reservado por otros controladores.",13);
            else text(controlStage==2?"Esperando Control 1":"Sin trabajo pendiente en este pallet",13);
            content=body;
        }
        if(pallets.length()==0)message("Este camión no tiene pallets físicos en el plan aprobado.");
    }
    private void startPallet(JSONObject selected,int requestedStage){
        currentStage=requestedStage;pallet=selected;
        task(()->json("POST","/load-control/loads/"+selected.optInt("load_id")+"/pallets/"+selected.optString("id")+"/start/"+requestedStage,obj()),started->{
            check=started;products=started.optJSONArray("products");if(products==null)products=new JSONArray();
            load=obj("id",selected.optInt("load_id"),"reparto",selected.optString("reparto"));
            JSONObject startedPallet=started.optJSONObject("pallet");
            JSONArray shortages=startedPallet==null?new JSONArray():startedPallet.optJSONArray("shortages");
            if(shortages==null)shortages=new JSONArray();
            JSONArray alerts=started.optJSONArray("picking_alerts");if(alerts==null)alerts=new JSONArray();
            court=obj("numero",selected.optInt("owner_court"),"status",obj("shortages",shortages,"picking_alerts",alerts));
            index=0;JSONObject answers=check.optJSONObject("answers");
            while(index<products.length()-1 && answers!=null && answers.has(productKey(products.optJSONObject(index))))index++;
            automaticallySpokenProducts.clear();product();
        });
    }
    private void openLoad(int id,int selectedCourt) {
        task(() -> json("GET","/load-control/loads/"+id,null), result -> {
            currentScreen = "courts"; check = null; court = null;
            load=result; screen("Reparto " + load.optString("reparto")); button("Volver a cargas",this::listLoads);
            if(!isController())voicePanel();voiceCourtCandidate=null;
            if(load.optBoolean("separate_reparto"))text(ProductSpeech.separation(load.optString("reparto"),load.optString("assembly_mode").equals("compact"),true),17);
            JSONObject loadPlan=load.optJSONObject("load_plan");
            if(loadPlan!=null)text("Este reparto ocupa "+loadPlan.optInt("total_pallets")+" pallets: "+loadPlan.optInt("full_count")+" completos + "+loadPlan.optInt("mixed_count")+" de picking.",16);
            if(load.optString("planning_status").equals("legacy"))text("Carga anterior en control. No permite iniciar un armado nuevo; consultá al supervisor.",16);
            content=disclosure("Ver resumen del camión");truckSummary(load.optJSONObject("truck_summary"),false);
            JSONArray courts=load.getJSONArray("canchas"); int count=0;
            for(int i=0;i<courts.length();i++) { JSONObject c=courts.getJSONObject(i); if(!matches(c) || (selectedCourt>0 && selectedCourt!=c.optInt("numero"))) continue; count++;
                if(voiceCourtCandidate==null && !processState(c).equals("Finalizados") && c.optJSONArray("productos").length()>0 && c.optBoolean("can_prepare",true))voiceCourtCandidate=c;
                content=card(BORDER);String state=processState(c); text("Cancha " + c.optInt("numero"),19);text(state+" · "+c.optJSONArray("productos").length()+" productos",13);
                if(c.optBoolean("assistance",false))text("Refuerzo de hoy · Tu asignación semanal no cambia",14);
                if(stage()==0 && c.optInt("full_pallet_count")>0){
                    text("Pallets completos · Información",16);
                    JSONArray full=c.optJSONArray("full_pallets_info");
                    if(full!=null)for(int n=0;n<full.length();n++){JSONObject item=full.optJSONObject(n);text(item.optInt("pallets")+" pallets · "+item.optString("descripcion")+" ("+item.optInt("bultos")+" bultos)",13);}
                    text("Se registran por separado del picking de bultos y unidades sueltas.",12);
                }
                if(isController())controlActions(c);
                else if(!state.equals("Finalizados") && c.optJSONArray("productos").length()>0 && c.optBoolean("can_prepare",true)) styledButton("Iniciar / retomar cancha " + c.optInt("numero"),GREEN,Color.WHITE,GREEN, () -> startCourt(c,stage()));
                else if(c.optJSONArray("productos").length()==0)text("Esta cancha solo tiene pallets completos; no requiere picking de sueltos.",14);
                content=body;
            }
            if(count==0) message("No hay canchas asignadas que coincidan con el filtro.");
        });
    }
    private void controlActions(JSONObject c){
        JSONArray checks=c.optJSONObject("status").optJSONArray("checks");
        JSONObject first=checkAt(checks,1),second=checkAt(checks,2);
        int action=ControlWorkflow.action(first!=null,first!=null && first.optString("status").equals("done"),first==null?0:first.optInt("user_id"),
            second!=null,second!=null && second.optString("status").equals("done"),second==null?0:second.optInt("user_id"),user.optInt("id"));
        if(action==ControlWorkflow.FINISHED){text("Control 1 y Control 2 finalizados",14);return;}
        if(action==ControlWorkflow.START_FIRST){styledButton("Iniciar Control 1",GREEN,Color.WHITE,GREEN,()->startCourt(c,1));return;}
        if(action==ControlWorkflow.RESUME_FIRST){text("Tu Control 1 está "+(first.isNull("timer_started_at")?"pausado":"en curso"),14);styledButton("Retomar Control 1",GREEN,Color.WHITE,GREEN,()->startCourt(c,1));return;}
        if(action==ControlWorkflow.WAIT_FIRST){text("Control 1 reservado por "+first.optString("username")+".",14);return;}
        text("Control 1 finalizado por "+first.optString("username")+". Falta Control 2.",14);
        if(action==ControlWorkflow.NEED_OTHER_CONTROLLER){text("El Control 2 debe hacerlo otro controlador.",14);return;}
        if(action==ControlWorkflow.START_SECOND){styledButton("Iniciar Control 2",GREEN,Color.WHITE,GREEN,()->startCourt(c,2));return;}
        if(action==ControlWorkflow.RESUME_SECOND){styledButton("Retomar Control 2",GREEN,Color.WHITE,GREEN,()->startCourt(c,2));return;}
        text("Control 2 reservado por "+second.optString("username")+".",14);
    }
    private void startCourt(JSONObject c,int requestedStage) {
        currentStage=requestedStage;
        task(() -> {
            JSONObject started=json("POST","/load-control/loads/"+load.optInt("id")+"/courts/"+c.optInt("numero")+"/start/"+stage(),obj());
            return obj("check",started,"load",json("GET","/load-control/loads/"+load.optInt("id"),null));
        }, result -> {
            load=result.getJSONObject("load");court=c;check=result.getJSONObject("check");
            products=check.optJSONArray("products");if(products==null)products=c.optJSONArray("productos");if(products==null)products=new JSONArray();index=0;
            automaticallySpokenProducts.clear();
            if(c.optBoolean("assistance",false))speak(voiceText("assistance_start","Refuerzo en cancha {court}. Tenés {total} productos asignados. Prepará solamente los productos que indica la aplicación.","court",c.optInt("numero"),"total",products.length()));
            JSONObject answers=check.getJSONObject("answers"); while(index<products.length()-1 && answers.has(productKey(products.getJSONObject(index)))) index++;
            product();
        });
    }
    private String prompt() {
        JSONObject p=products.optJSONObject(index);
        String name=p.optString("descripcion_voz",p.optString("descripcion"));
        boolean readFreshness=stage()==4?voiceSettings.optBoolean("speak_freshness_full_pallets",true):voiceSettings.optBoolean("speak_freshness_picking",true);
        String spokenFreshness=readFreshness?freshnessText(p.optString("fecha_frescura")):"";
        String fallback=ProductSpeech.prompt(name,p.optInt("bultos"),p.optInt("unidades"),p.optInt("pallets"),stage(),index,products.length(),"");
        String configured=fallback;
        if(stage()==4 && p.optInt("pallets")>0){
            String pallets=p.optInt("pallets")==1?"un pallet completo":p.optInt("pallets")+" pallets completos";
            configured=voiceText("pallet_product",fallback,"position",index+1,"total",products.length(),"pallets",pallets,"product",name);
        }else if(p.optInt("bultos")==0 && p.optInt("unidades")==0){
            configured=voiceText("empty_product",fallback,"position",index+1,"total",products.length(),"product",name);
        }else if(stage()==0){
            List<String> quantities=new ArrayList<>();
            if(p.optInt("bultos")>0)quantities.add(p.optInt("bultos")==1?"un bulto":p.optInt("bultos")+" bultos");
            if(p.optInt("unidades")>0)quantities.add(p.optInt("unidades")==1?"una unidad":p.optInt("unidades")+" unidades");
            configured=voiceText("picking_product",fallback,"position",index+1,"total",products.length(),"quantity",String.join(" y ",quantities),"product",name);
        }
        if(!configured.isEmpty() && !spokenFreshness.isEmpty())configured+=" Frescura exacta "+spokenFreshness+".";
        return configured.isEmpty()?"":configured+" "+destinations(p);
    }
    private String freshnessText(String value){
        if(value==null||value.isEmpty()||value.equalsIgnoreCase("null")||value.equalsIgnoreCase("none"))return "";
        try{return java.time.LocalDate.parse(value).format(java.time.format.DateTimeFormatter.ofPattern("dd/MM/yyyy"));}
        catch(Exception ignored){return value;}
    }
    private java.time.LocalDate freshnessDate(JSONObject product){
        String value=product.optString("fecha_frescura","");
        if(value.isEmpty()||value.equalsIgnoreCase("null")||value.equalsIgnoreCase("none"))return null;
        try{return java.time.LocalDate.parse(value);}catch(Exception ignored){return null;}
    }
    private boolean freshnessExpired(JSONObject product){
        java.time.LocalDate date=freshnessDate(product);return date!=null&&date.isBefore(java.time.LocalDate.now());
    }
    private void freshnessBadge(JSONObject product){
        java.time.LocalDate date=freshnessDate(product);
        TextView badge;
        if(date==null){badge=text("Frescura no informada",14);badge.setTextColor(dark?0xfffcd34d:0xff92400e);badge.setBackground(shape(0xfffffbeb,0xfffcd34d,10));}
        else {long days=java.time.temporal.ChronoUnit.DAYS.between(java.time.LocalDate.now(),date);String label="Frescura "+freshnessText(date.toString());int fill=0xffecfdf5,border=0xff6ee7b7,color=0xff047857;
            if(days<0){label+=" · VENCIDA";fill=0xfffff1f2;border=0xfffda4af;color=RED;}
            else if(freshnessWarningDays>0&&days<=freshnessWarningDays){label+=" · vence en "+days+" días";fill=0xfffffbeb;border=0xfffcd34d;color=0xff92400e;}
            badge=text(label,14);badge.setTextColor(dark&&color==0xff047857?0xff6ee7b7:color);badge.setBackground(shape(fill,border,10));
        }
        badge.setPadding(dp(10),dp(8),dp(10),dp(8));
    }
    private String productKey(JSONObject product){
        if(product==null)return "";
        String sku=product.optString("sku","");
        if(!product.has("product_key")||product.isNull("product_key"))return sku;
        String value=product.optString("product_key",sku).trim();
        return value.isEmpty()||value.equalsIgnoreCase("null")||value.equalsIgnoreCase("none")?sku:value;
    }
    private String productSpeechKey(){
        JSONObject p=products.optJSONObject(index);
        return check.optString("id")+":"+productKey(p);
    }
    private void speakProductOnce(){
        String key=productSpeechKey();
        if(automaticallySpokenProducts.add(key) && !prompt().trim().isEmpty())speak(prompt());
        else startMic();
    }
    private void product() {
        currentScreen = "product";
        if(products.length()==0) { message("La cancha no tiene productos."); return; }
        JSONObject p=products.optJSONObject(index); screen(stageLabel() + (isController()&&pallet!=null?" · Pallet "+pallet.optString("id"):" · Cancha " + court.optInt("numero")));
        if(p.optBoolean("separate_reparto"))text(ProductSpeech.separation(p.optString("reparto"),p.optString("assembly_mode").equals("compact"),true),16);
        content=card(BORDER);
        text("SKU " + p.optString("sku")+(p.optString("almacen").isEmpty()?"":" · "+p.optString("almacen")),12);
        TextView productName=text(p.optString("descripcion"),21);productName.setMaxLines(2);productName.setEllipsize(android.text.TextUtils.TruncateAt.END);
        freshnessBadge(p);
        String destination=destinations(p);
        if(!destination.isEmpty())text(destination,17);
        if(stage() == 4) text(p.optInt("pallets") + " PALLETS COMPLETOS", 28);
        gap(8);LinearLayout amounts=row();content.addView(amounts);
        for(int i=0;i<2;i++){
            LinearLayout box=column();box.setGravity(Gravity.CENTER);box.setPadding(dp(8),dp(8),dp(8),dp(8));box.setBackground(shape(BG,BG,12));
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);if(i==0)lp.rightMargin=dp(10);amounts.addView(box,lp);
            TextView caption=label(i==0?"BULTOS DE LA\nPLANILLA":"UNIDADES DE LA\nPLANILLA",10,MUTED,false);caption.setGravity(Gravity.CENTER);box.addView(caption);
            TextView amount=label(String.valueOf(p.optInt(i==0?"bultos":"unidades")),34,INK,true);amount.setGravity(Gravity.CENTER);box.addView(amount);
        }
        gap(8);LinearLayout palletData=row();content.addView(palletData);
        String[] metricLabels={"Bultos por piso","Pisos","Bultos por pallet"};String[] metricKeys={"bultos_por_piso","pisos_por_pallet","bultos_por_pallet"};
        for(int i=0;i<metricKeys.length;i++){
            LinearLayout box=column();box.setGravity(Gravity.CENTER);box.setPadding(dp(4),dp(8),dp(4),dp(8));box.setBackground(shape(SURFACE,BORDER,10));
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);if(i>0)lp.leftMargin=dp(6);palletData.addView(box,lp);
            String value=p.isNull(metricKeys[i])?"—":String.valueOf(p.optInt(metricKeys[i]));TextView number=label(value,18,INK,true);number.setGravity(Gravity.CENTER);box.addView(number);
            TextView caption=label(metricLabels[i],10,MUTED,false);caption.setGravity(Gravity.CENTER);box.addView(caption);
        }
        if(!p.optBoolean("configuracion_pallet_completa"))text("Configuración logística incompleta o inconsistente.",12);
        if(check.optJSONObject("answers").has(productKey(p))) text("Este producto ya tiene una respuesta guardada.",16);
        if(isController()){
            JSONObject alert=existingAlert(productKey(p));
            if(alert!=null){
                String reason=alert.optString("shortage_reason","no_localizado").replace('_',' ');
                text("AVISO DE PICKING: "+reason.toUpperCase(),17);
                text("Se encontraron "+alert.optInt("physical_b")+" bultos y "+alert.optInt("physical_u")+" unidades. Informó: "+alert.optString("reported_username","operario")+".",14);
            }
        }
        if(stage()==0 && p.optInt("full_pallets_count")>0){
            gap(6);TextView full=text("Pallets completos: "+p.optInt("full_pallets_count")+" · "+p.optInt("full_pallets_bultos")+" bultos",14);full.setTextColor(dark?0xff7dd3fc:0xff0369a1);
            text("Informativo · Se registran por separado del picking indicado arriba.",12);
        }
        content=body;if(!isController())voicePanel();
        pendingControls();
        boolean paused=check.isNull("timer_started_at");
        if(paused) { message("Proceso pausado. Reanudalo antes de registrar."); button("Reanudar "+stageLabel(), () -> startCourt(court,stage())); }
        else if(freshnessExpired(p) && voiceSettings.optBoolean("block_expired_products",true)) {
            message("Producto bloqueado: la frescura está vencida. Informá al supervisor o registrá la diferencia correspondiente.");
            if(isController())styledButton("Registrar diferencia de frescura",0xfffffbeb,0xff92400e,0xfffcd34d,()->showIncident("corrected"));
            styledButton("Registrar faltante real",0xfffff1f2,RED,0xfffda4af,this::shortage);
        } else if(!pendingAnswer()) {
            styledButton("Correcto →",GREEN,Color.WHITE,GREEN, () -> answer(obj("result","ok")));
            if(isController())styledButton("Error corregido",0xfffffbeb,0xff92400e,0xfffcd34d,()->showIncident("corrected"));
            styledButton("Faltante real",0xfffff1f2,RED,0xfffda4af,this::shortage);
        }else message("Resolvé el registro pendiente para continuar con los productos.");
        LinearLayout navigation=row();content.addView(navigation);content=navigation;
        Button previous=styledButton("← Anterior",Color.WHITE,INK,BORDER,()->{if(index>0){index--;product();}});
        Button next=styledButton("Siguiente →",Color.WHITE,INK,BORDER,()->{if(index<products.length()-1){index++;product();}});
        LinearLayout.LayoutParams left=new LinearLayout.LayoutParams(0,-2,1);left.rightMargin=dp(10);previous.setLayoutParams(left);next.setLayoutParams(new LinearLayout.LayoutParams(0,-2,1));
        previous.setEnabled(index>0);previous.setAlpha(index>0?1:0.45f);next.setEnabled(index<products.length()-1);next.setAlpha(index<products.length()-1?1:0.45f);
        content=body;gap(10);text("Siguiente permite revisar sin confirmar el producto.",12);
        if(!isController())button("Escuchar / repetir producto", () -> speak(prompt()));
        button("Pausar y volver a canchas",this::pauseAndLeave);
        text("Reparto "+load.optString("reparto")+(pallet==null?"":" · Pallet "+pallet.optString("id"))+" · "+user.optString("username"),12);
        LinearLayout footer=column();footer.setPadding(dp(16),dp(10),dp(16),dp(4));footer.setBackgroundColor(SURFACE);root.addView(footer);content=footer;
        if(pendingAnswer())text("Finalización bloqueada · verificá el registro pendiente",16);
        else button(isController()?"Finalizar "+stageLabel():"Finalizar picking", () -> { stopAudio(); new AlertDialog.Builder(this).setTitle(isController()?"Finalizar "+stageLabel():"Finalizar picking")
            .setMessage(check.optJSONObject("answers").length()+" de "+products.length()+" productos registrados. ¿Finalizar?")
            .setNegativeButton("Seguir",(d,w)->product()).setOnCancelListener(d->product()).setPositiveButton("Finalizar",(d,w)->finishPicking()).show(); });
        content=body;
        if(voice && !paused && !isController()) speakProductOnce();
    }
    private void answer(JSONObject data) {
        if(busy || check==null || check.isNull("timer_started_at")) return;
        if(pendingAnswer()){message("Hay un registro por verificar. Volvé al producto o al inicio y usá Verificar guardado.");return;}
        stopAudio();
        try { JSONObject current=products.getJSONObject(index);data.put("sku",current.getString("sku"));data.put("product_key",productKey(current)); } catch(Exception e) {error(e);return;}
        if(demo) { try { check.getJSONObject("answers").put(data.getString("sku"),data); } catch(Exception e){error(e);} afterAnswer();return; }
        try{data.put("request_id",UUID.randomUUID().toString());}catch(Exception e){error(e);return;}
        String endpoint=path();
        if(!getPreferences(0).edit().putString(pendingKey(),obj("path",endpoint,"payload",data).toString()).commit()){
            message("No se pudo conservar el comprobante en este teléfono. No se envió el registro.");return;
        }
        message("Enviando registro…");
        task(() -> {
            try { return json("POST",endpoint+"/answer",data); }
            catch(Exception e) {
                if(definitiveFailure(e))clearPendingAnswer();
                else try{
                    JSONObject stored=new JSONObject(getPreferences(0).getString(pendingKey(),"{}"));
                    stored.put("last_error",errorReason(e));
                    getPreferences(0).edit().putString(pendingKey(),stored.toString()).commit();
                }catch(Exception ignored){ }
                throw e;
            }
        }, result -> {
            getPreferences(0).edit().remove(pendingKey()).commit();check=result;afterAnswer();message("Guardado en el servidor.");
        });
    }
    private void afterAnswer() {
        if(index<products.length()-1) {index++;product();}
        else {product();if(!isController())speak(voiceText("last_product","Último producto registrado. Revisá el avance y decí finalizar picking."));}
    }
    private void shortage() {
        stopAudio();
        if(isController()){showIncident("shortage");return;}
        showShortage();
    }
    private JSONObject existingShortage(String productKey){
        JSONArray values=court.optJSONObject("status").optJSONArray("shortages");
        if(values!=null)for(int i=0;i<values.length();i++){JSONObject value=values.optJSONObject(i);if(value!=null && productKey.equals(productKey(value)))return value;}
        return null;
    }
    private JSONObject existingAlert(String productKey){
        JSONArray values=court.optJSONObject("status").optJSONArray("picking_alerts");
        if(values!=null)for(int i=0;i<values.length();i++){JSONObject value=values.optJSONObject(i);if(value!=null && productKey.equals(productKey(value)))return value;}
        return null;
    }
    private void showIncident(String result){
        stopAudio();currentScreen="shortage";
        JSONObject p=products.optJSONObject(index),previous=existingShortage(productKey(p));
        boolean confirmation=stage()==2 && result.equals("shortage") && previous!=null;
        screen(result.equals("corrected")?"Error corregido":"Registrar faltante");
        content=card(result.equals("corrected")?0xfffcd34d:0xfffecaca);
        text(result.equals("corrected")?"Error corregido":"Faltante real",20);
        text(p.optString("descripcion")+" · planilla: "+p.optInt("bultos")+" bultos + "+p.optInt("unidades")+" unidades",13);gap(8);
        text(confirmation?"Confirmá las cantidades registradas en el Control 1":"Ingresá la cantidad encontrada antes de corregir",14);
        EditText foundB=input("Bultos encontrados",InputType.TYPE_CLASS_NUMBER),foundU=input("Unidades encontradas",InputType.TYPE_CLASS_NUMBER);
        foundB.setText(String.valueOf(confirmation?previous.optInt("actual_b"):0));foundU.setText(String.valueOf(confirmation?previous.optInt("actual_u"):0));
        foundB.setEnabled(!confirmation);foundU.setEnabled(!confirmation);
        final EditText physicalB=foundB,physicalU=foundU;
        Spinner origin=new Spinner(this);
        if(!confirmation){
            text("Causa de la diferencia",13);
            String[] causes=stage()==2?new String[]{"Menos cantidad","Más cantidad","Artículo equivocado","Frescura incorrecta","Diferencia de stock","Error del Control 1"}:new String[]{"Menos cantidad","Más cantidad","Artículo equivocado","Frescura incorrecta","Diferencia de stock"};
            origin.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,causes));content.addView(origin);
            JSONObject assembly=pallet==null?null:pallet.optJSONObject("assembly");
            text("Si es error de picking, responsable automático: "+(assembly!=null&&!assembly.optString("username").isEmpty()?assembly.optString("username"):"se determinará en el servidor")+". Las diferencias de stock no penalizan al operario.",13);
        }else text("Se conserva el responsable registrado por el primer controlador: "+previous.optJSONObject("incident").optString("responsible_username"),13);
        EditText foundSku=input("SKU encontrado (solo artículo equivocado)",InputType.TYPE_CLASS_TEXT);
        EditText actualFreshness=input("Frescura encontrada DD/MM/AAAA",InputType.TYPE_CLASS_DATETIME);
        gap(8);text("Observación"+(result.equals("corrected")?" obligatoria":" opcional"),13);
        EditText note=input("Describí qué ocurrió…",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE);note.setSingleLine(false);note.setMinLines(3);note.setGravity(Gravity.TOP);
        TextView feedback=text("",14);
        styledButton(result.equals("corrected")?"Registrar error corregido":"Registrar faltante",result.equals("corrected")?0xff92400e:RED,Color.WHITE,result.equals("corrected")?0xff92400e:RED,()->{
            try{
                if(result.equals("corrected") && note.getText().toString().trim().isEmpty()){feedback.setText("Describí la diferencia que fue corregida.");return;}
                JSONObject payload=obj("result",result,"note",note.getText().toString());
                int actualB=Integer.parseInt(physicalB.getText().toString()),actualU=Integer.parseInt(physicalU.getText().toString());
                if(actualB<0||actualU<0){feedback.setText("Ingresá cantidades no negativas.");return;}
                String[] types=stage()==2?new String[]{"less_quantity","more_quantity","wrong_product","freshness","stock","control"}:new String[]{"less_quantity","more_quantity","wrong_product","freshness","stock"};
                String errorType=confirmation?"quantity":types[origin.getSelectedItemPosition()];
                if(actualB==p.optInt("bultos")&&actualU==p.optInt("unidades")&&!errorType.equals("wrong_product")&&!errorType.equals("freshness")){feedback.setText("La cantidad encontrada debe ser diferente de la planificada.");return;}
                if(result.equals("shortage")&&(actualB>p.optInt("bultos")||actualU>p.optInt("unidades"))){feedback.setText("Un faltante no puede superar la cantidad planificada.");return;}
                payload.put("physical_b",actualB);payload.put("physical_u",actualU);
                if(!confirmation){
                    if(errorType.equals("wrong_product")&&foundSku.getText().toString().trim().isEmpty()){feedback.setText("Ingresá el SKU encontrado.");return;}
                    if(errorType.equals("freshness")&&actualFreshness.getText().toString().trim().isEmpty()){feedback.setText("Ingresá la frescura encontrada.");return;}
                    payload.put("error_type",errorType);payload.put("found_sku",foundSku.getText().toString().trim());payload.put("actual_freshness",actualFreshness.getText().toString().trim());
                }
                answer(payload);
            }catch(Exception e){error(e);}
        });
        button("Cancelar",this::product);content=body;
    }
    private void showShortage() {
        currentScreen = "shortage";
        JSONObject p=products.optJSONObject(index); screen("Registrar faltante");voicePanel();
        content=card(0xfffecaca);text("Registrar faltante",20);
        text("Cantidad que encontraste (no la cantidad que falta)",16);
        text(p.optString("descripcion")+" · planilla: "+p.optInt("bultos")+" bultos + "+p.optInt("unidades")+" unidades",13);gap(8);
        LinearLayout form=content, quantities=row();content.addView(quantities);
        for(int i=0;i<2;i++){
            LinearLayout field=column();LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);if(i==0)lp.rightMargin=dp(10);quantities.addView(field,lp);content=field;
            text(i==0?"Bultos encontrados":"Unidades encontradas",12);EditText value=input(i==0?"Bultos físicos":"Unidades físicas",InputType.TYPE_CLASS_NUMBER);value.setTextSize(22);value.setText("0");
            TextView hint=text("Tocá para corregir",11);
            if(i==0){shortageB=value;bHint=hint;}else{shortageU=value;uHint=hint;}
        }
        content=form;button("No encontré nada",()->{shortageB.setText("0");shortageU.setText("0");});
        gap(8);text("Proceso al que corresponde",13);TextView origin=text(stage()==4?"Pallets completos":"Picking",16);origin.setPadding(dp(14),dp(14),dp(14),dp(14));origin.setBackground(shape(Color.WHITE,0xffcbd5e1,12));
        text("Responsable: "+user.optString("username"),12);gap(4);
        text("Observación (opcional)",13); EditText note=input("Escribí qué pasó con el producto…",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE);note.setSingleLine(false);note.setMinLines(3);note.setGravity(Gravity.TOP);
        Spinner reason=new Spinner(this);
        String[] reasonLabels={"Falta de stock","Rotura","Producto no localizado","Frescura solicitada no disponible"};
        String[] reasonValues={"stock","rotura","no_localizado","frescura_no_disponible"};
        text("Motivo",13);reason.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,reasonLabels));content.addView(reason);
        shortageFeedback=text("",16);shortageFeedback.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        android.text.TextWatcher watcher=new android.text.TextWatcher(){
            public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            public void onTextChanged(CharSequence s,int start,int before,int count){shortageFeedback.setText(ShortageAmounts.summary(shortageB.getText().toString(),shortageU.getText().toString(),p.optInt("bultos"),p.optInt("unidades")));}
            public void afterTextChanged(android.text.Editable s){}
        };
        shortageB.addTextChangedListener(watcher);shortageU.addTextChangedListener(watcher);watcher.onTextChanged("",0,0,0);
        voiceShortageSubmit=() -> {
            try {
                String validation=ShortageAmounts.error(shortageB.getText().toString(),shortageU.getText().toString(),p.optInt("bultos"),p.optInt("unidades"));
                if(!validation.isEmpty()){shortageFeedback.setText(validation);return;}
                int physicalB=Integer.parseInt(shortageB.getText().toString()),physicalU=Integer.parseInt(shortageU.getText().toString());
                int responsible=demo?0:user.getInt("id");
                answer(obj("result","shortage","physical_b",physicalB,"physical_u",physicalU,"responsible_user_id",responsible,"origin","picking","shortage_reason",reasonValues[reason.getSelectedItemPosition()],"note",note.getText().toString()));
            } catch(Exception e) {error(e);}
        };
        styledButton("Registrar faltante",RED,Color.WHITE,RED,voiceShortageSubmit);
        button("Cancelar",()->{stopAudio();product();});content=body;
        text("Revisá las cantidades y tocá Registrar faltante o decí registrar faltante.",12);
        if(voice)speak(voiceText("shortage_quantities","Decí los bultos y unidades físicos. Revisá y decí registrar faltante."));
    }
    private void pauseAndLeave() {
        stopAudio();
        if(demo){login();return;}
        filter="Todos";
        if(check.isNull("timer_started_at")){if(isController()&&controlTruck!=null)openControlTruck(controlTruck);else if(isPalletizer()&&pallet!=null&&controlTruck!=null)openFullPalletTruck(controlTruck);else openLoad(load.optInt("id"));return;}
        task(() -> json("POST",path()+"/pause",obj()), result -> { check=result;if(isController()&&controlTruck!=null)openControlTruck(controlTruck);else if(isPalletizer()&&pallet!=null&&controlTruck!=null)openFullPalletTruck(controlTruck);else openLoad(load.optInt("id")); });
    }
    private void finishPicking() {
        stopAudio();voiceConfirmFinish=false;
        if(demo){login();message("Demostración finalizada. No se guardaron datos.");return;}
        task(() -> json("POST",path()+"/finish",obj()), result -> {filter="Todos";announceQueue=true;if(isController()&&controlTruck!=null)openControlTruck(controlTruck);else if(isPalletizer()&&pallet!=null&&controlTruck!=null)openFullPalletTruck(controlTruck);else listLoads();});
    }
    private void startAssets(JSONObject truck){
        task(()->obj("types",new JSONArray(api.request("GET","/load-control/asset-types",null)),
                "check",json("POST","/load-control/trucks/"+truck.optInt("id")+"/assets/start",obj())),result->{
            activeTruck=truck;showAssets(result.getJSONArray("types"));
        });
    }
    private void showAssets(JSONArray types){
        currentScreen="assets";screen("Activos de salida · Camión "+activeTruck.optString("truck"));
        text("Contá los activos físicos y completá todos los campos, incluido cero.",14);
        Map<String,EditText> fields=new LinkedHashMap<>();
        for(int i=0;i<types.length();i++){
            String name=types.optString(i);text(name,13);EditText field=input("Cantidad de "+name,InputType.TYPE_CLASS_NUMBER);fields.put(name,field);
        }
        styledButton("Confirmar activos",GREEN,Color.WHITE,GREEN,()->{
            try{
                JSONObject quantities=new JSONObject();
                for(Map.Entry<String,EditText> entry:fields.entrySet()){
                    String value=entry.getValue().getText().toString().trim();
                    if(value.isEmpty()){message("Completá todos los activos, incluido cero.");return;}
                    int amount=Integer.parseInt(value);if(amount<0){message("Las cantidades no pueden ser negativas.");return;}quantities.put(entry.getKey(),amount);
                }
                task(()->json("POST","/load-control/trucks/"+activeTruck.optInt("id")+"/assets",obj("quantities",quantities)),result->{activeTruck=null;listLoads();message("Activos registrados. La salida se libera cuando no quedan autorizaciones pendientes.");});
            }catch(Exception e){error(e);}
        });
        button("Cancelar y volver",this::listLoads);
    }
    private void enableVoice() {
        if(isController() || !visible || busy)return;
        boolean working=currentScreen.equals("product") || currentScreen.equals("shortage");
        if(!working && !currentScreen.equals("loads") && !currentScreen.equals("courts"))return;
        if(working && (check==null || check.isNull("timer_started_at")))return;
        if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED) {requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},10);return;}
        if(!ttsReady){message("Activá o instalá una voz en español en los ajustes de texto a voz de Android.");return;}
        if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED && !getPreferences(0).getBoolean("notificationAsked",false)){
            getPreferences(0).edit().putBoolean("notificationAsked",true).apply();
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},11);return;
        }
        if(voice)return;
        voice=true;getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        updateVoiceUi("Preparando voz…");
        try{
            Intent intent=new Intent(this,VoiceSessionService.class);
            startForegroundService(intent);
            voiceBound=bindService(intent,voiceConnection,BIND_AUTO_CREATE);
            if(!voiceBound)throw new IllegalStateException("No se pudo conectar el servicio de voz.");
        }catch(Exception e){voice=false;stopAudio();error(e);}
    }
    private void activateVoice(){
        updateVoiceUi("Leyendo…");
        if(currentScreen.equals("shortage"))speak(voiceText("shortage_quantities","Decí los bultos y unidades físicos. Revisá y decí registrar faltante."));
        else if(currentScreen.equals("loads"))speak(voiceNextLoadId>0?"Voz activa. Decí iniciar o continuar para abrir tu próxima tarea, o actualizar tareas.":"Voz activa. No hay tareas disponibles. Podés decir actualizar tareas.");
        else if(currentScreen.equals("courts"))speak(voiceCourtCandidate!=null?"Decí iniciar cancha para comenzar.":"No hay canchas disponibles en este reparto.");
        else speakProductOnce();
    }
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] grants) {
        super.onRequestPermissionsResult(request,permissions,grants);
        if(request==11){enableAfterPermission=true;if(grants.length==0 || grants[0]!=PackageManager.PERMISSION_GRANTED)message("Para ver el control de voz fuera de la app, habilitá las notificaciones en Android.");}
        else if(request==10 && grants.length>0 && grants[0]==PackageManager.PERMISSION_GRANTED) enableAfterPermission=true;
        else if(request==10)message("Sin permiso de micrófono. Podés continuar con los botones.");
        handler.post(this::resumeVoiceAfterPermission);
    }
    private void resumeVoiceAfterPermission(){if(visible && enableAfterPermission){enableAfterPermission=false;enableVoice();}}
    private void speechFailed(int generation){
        if(generation!=speechVersion || isDestroyed())return;
        voice=false;stopAudio();updateVoiceUi("Voz detenida");
        message("No se pudo leer el producto. Revisá Texto a voz y el volumen antes de activar la voz nuevamente.");
    }
    private void speak(String value) {
        stopAudio();
        if(!ttsReady){speechFailed(speechVersion);return;}
        tts.setSpeechRate(Math.max(0.6f,Math.min(1.6f,speechRate)));
        int generation=++speechVersion;
        updateVoiceUi("Leyendo…");
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener(){
            @Override public void onStart(String id){}
            @Override public void onDone(String id){if(!("product-"+generation).equals(id))return;handler.postDelayed(()->{if(generation==speechVersion && !isDestroyed() && !busy){if(voice)startMic();else updateVoiceUi("Voz desactivada");}},400);}
            @Override public void onError(String id){if(("product-"+generation).equals(id))handler.post(()->speechFailed(generation));}
        });
        if(tts.speak(value,TextToSpeech.QUEUE_FLUSH,null,"product-"+generation)==TextToSpeech.ERROR)speechFailed(generation);
    }
    private void startMic() {
        if(!voice || voiceSession==null)return;
        if((currentScreen.equals("product")||currentScreen.equals("shortage")) && (check==null||check.isNull("timer_started_at")))return;
        if(!currentScreen.equals("loads")&&!currentScreen.equals("courts")&&!currentScreen.equals("product")&&!currentScreen.equals("shortage"))return;
        voiceSession.listen();
    }
    private void command(String text) {
        if(text.trim().isEmpty())return;
        lastHeard=text;if(heardView!=null)heardView.setText("Escuché: “"+text+"”");
        String action=VoiceCommands.parse(text,voiceCommands);
        if(voiceConfirmFinish){
            if(action.equals("confirm")){voiceConfirmFinish=false;finishPicking();}
            else if(action.equals("cancel")){voiceConfirmFinish=false;speak("Finalización cancelada. Continuá con el picking.");}
            else speak("Decí confirmar para finalizar o cancelar para continuar.");
            return;
        }
        if(currentScreen.equals("loads")){
            if((action.equals("start") || action.equals("continue")) && voiceNextLoadId>0)openLoad(voiceNextLoadId,voiceNextCourt);
            else if(action.equals("refresh"))listLoads();
            else if((action.equals("start") || action.equals("continue")))invalidVoiceCommand("Todavía no hay una tarea habilitada. Decí actualizar tareas.");
            else invalidVoiceCommand("Decí iniciar, continuar o actualizar tareas.");
            return;
        }
        if(currentScreen.equals("courts")){
            if(action.equals("start") && voiceCourtCandidate!=null)startCourt(voiceCourtCandidate,stage());
            else if(action.equals("cancel"))listLoads();
            else invalidVoiceCommand("Decí iniciar cancha o cancelar.");
            return;
        }
        if(currentScreen.equals("shortage")){
            if(action.equals("register") && voiceShortageSubmit!=null){voiceShortageSubmit.run();return;}
            if(action.equals("cancel")){stopAudio();product();return;}
            Integer[] values=VoiceQuantities.parse(text);
            if(values==null){invalidVoiceCommand("Decí cantidades o registrar faltante.");return;}
            JSONObject p=products.optJSONObject(index);
            if((values[0]!=null && values[0]>p.optInt("bultos")) || (values[1]!=null && values[1]>p.optInt("unidades"))){message("La cantidad dictada supera la planilla. Repetila o corregila a mano.");return;}
            if(values[0]!=null){shortageB.setText(values[0].toString());shortageB.setBackground(shape(Color.WHITE,GREEN,12));bHint.setText("Completado por voz");bHint.setTextColor(GREEN);}
            if(values[1]!=null){shortageU.setText(values[1].toString());shortageU.setBackground(shape(Color.WHITE,GREEN,12));uHint.setText("Completado por voz");uHint.setTextColor(GREEN);}
            message("Revisá las cantidades y decí registrar faltante.");return;
        }
        if(!currentScreen.equals("product"))return;
        switch(action){
            case "ok" -> answer(obj("result","ok"));
            case "shortage" -> shortage();
            case "repeat" -> speak(prompt());
            case "next" -> {if(index<products.length()-1){index++;product();}}
            case "prev" -> {if(index>0){index--;product();}}
            case "finish" -> {voiceConfirmFinish=true;speak("¿Confirmás finalizar esta cancha? Decí confirmar o cancelar.");}
            default -> invalidVoiceCommand(voiceText("unknown_command","No entendí. Decí correcto, faltante o repetir."));
        }
    }
    private void invalidVoiceCommand(String guidance){
        message(guidance);updateVoiceUi("Comando no reconocido · sigo escuchando");
        speak(guidance);
    }
    private void stopMic(){if(voiceSession!=null)voiceSession.suspendListening();}
    private void stopVoiceSession(){
        if(voiceSession!=null){voiceSession.detach();voiceSession.suspendListening();voiceSession=null;}
        if(voiceBound){voiceBound=false;unbindService(voiceConnection);}
        stopService(new Intent(this,VoiceSessionService.class));
        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }
    private void stopAudio(){speechVersion++;stopMic();if(tts!=null)tts.stop();if(!voice)stopVoiceSession();}
    @Override protected void onResume(){super.onResume();visible=true;handler.removeCallbacks(clockTick);handler.post(clockTick);handler.removeCallbacks(syncQueue);handler.post(syncQueue);resumeVoiceAfterPermission();}
    @Override protected void onPause(){visible=false;handler.removeCallbacks(syncQueue);handler.removeCallbacks(clockTick);super.onPause();}
    @Override public void onBackPressed(){
        if(busy){message("Esperá a que termine la operación.");return;}
        if(currentScreen.equals("shortage")){stopAudio();product();return;}
        if(currentScreen.equals("product")){pauseAndLeave();return;}
        if(currentScreen.equals("assets")){activeTruck=null;listLoads();return;}
        if(currentScreen.equals("pallet_board")){controlTruck=null;pallet=null;listLoads();return;}
        if(currentScreen.equals("full_pallet_board")){controlTruck=null;pallet=null;listLoads();return;}
        if(currentScreen.equals("courts")){listLoads();return;}
        new AlertDialog.Builder(this).setTitle("Salir de la app")
            .setMessage("¿Querés salir de Del Palacio Picking?")
            .setNegativeButton("Quedarme",null).setPositiveButton("Salir",(d,w)->finish()).show();
    }
    @Override protected void onDestroy(){requestVersion++;voice=false;stopAudio();if(tts!=null)tts.shutdown();handler.removeCallbacksAndMessages(null);network.shutdown();super.onDestroy();}
}
