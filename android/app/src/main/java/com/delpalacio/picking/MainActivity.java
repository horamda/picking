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
    private JSONObject user, load, court, check;
    private JSONArray products = new JSONArray(), operators = new JSONArray();
    private Set<Integer> assigned = new HashSet<>();
    private String filter = "Todos";
    private String currentScreen = "login";
    private int index = 0, requestVersion = 0, speechVersion = 0;
    private boolean demo = false, busy = false, voice = false, visible = false, ttsReady = false;
    private TextToSpeech tts;
    private VoiceSessionService voiceSession;
    private boolean voiceBound, enableAfterPermission;
    private boolean announceQueue;
    private String queueVersion="";
    private boolean refreshing;
    private JSONObject fetchQueue() throws Exception {
        return obj("permissions",json("GET","/load-control/my-courts",null),"trucks",new JSONArray(api.request("GET","/load-control/trucks",null)));
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
        }
        public void onServiceDisconnected(ComponentName name){
            voiceSession=null;voice=false;stopAudio();updateVoiceUi("Voz detenida");
            message("El servicio de voz se interrumpió. Tocá Activar voz para retomarlo.");
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
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
        LinearLayout v=column();v.setPadding(dp(14),dp(12),dp(14),dp(12));v.setBackground(shape(Color.WHITE,border,16));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(12);content.addView(v,lp);return v;
    }
    private void screen(String title) {
        voiceStatus=null;heardView=null;voiceButton=null;clockView=null;shortageB=null;shortageU=null;shortageFeedback=null;
        root=column();root.setBackgroundColor(BG);root.setFitsSystemWindows(true);
        boolean working=currentScreen.equals("product") || currentScreen.equals("shortage");
        LinearLayout header=column();header.setBackgroundColor(SURFACE);header.setPadding(dp(16),dp(8),dp(16),dp(10));root.addView(header);
        if(working){
            LinearLayout top=row();header.addView(top);
            top.addView(label("Camión "+load.optString("camion","Demo")+" · Cancha "+court.optInt("numero"),12,MUTED,false),new LinearLayout.LayoutParams(0,-2,1));
            TextView badge=label(stage()==4?"Pallets":"Picking",12,0xff047857,true);badge.setPadding(dp(12),dp(5),dp(12),dp(5));badge.setBackground(shape(0xffd1fae5,0xffd1fae5,20));top.addView(badge);
            LinearLayout second=row();header.addView(second);
            second.addView(label("Producto "+(index+1)+" de "+products.length(),12,MUTED,false),new LinearLayout.LayoutParams(0,-2,1));
            clockView=label("",12,MUTED,false);second.addView(clockView);updateClock();
            ProgressBar progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setMax(Math.max(1,products.length()));progress.setProgress(check.optJSONObject("answers").length());
            progress.setProgressTintList(android.content.res.ColorStateList.valueOf(GREEN));progress.setProgressBackgroundTintList(android.content.res.ColorStateList.valueOf(BORDER));header.addView(progress,new LinearLayout.LayoutParams(-1,dp(6)));
        }else{
            header.addView(label("DEL PALACIO",12,GREEN,true));header.addView(label(title,26,INK,true));
            header.addView(label(user==null?"Operación de depósito":"Usuario: "+user.optString("username")+" · "+(stage()==4?"Pallets completos":"Picking"),13,MUTED,false));
        }
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);body=column();content=body;
        content.setPadding(dp(16),dp(16),dp(16),dp(20));scroll.addView(content);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
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
        Button b=new Button(this);b.setText(title);b.setAllCaps(false);b.setTextSize(16);b.setTextColor(ink);b.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));b.setMinHeight(dp(52));b.setMinimumHeight(dp(52));
        b.setPadding(dp(12),dp(12),dp(12),dp(12));b.setBackground(shape(fill,border,12));b.setStateListAnimator(null);
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(10);content.addView(b,lp);b.setOnClickListener(v->{if(!busy)action.run();});return b;
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
        text(currentScreen.equals("shortage")?"Decí, por ejemplo: un bulto y luego dos unidades.":"Decí correcto o faltante. La app lee cada producto en voz alta.",12);content=parent;
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
        boolean announce=voice;
        if(voice){voice=false;stopAudio();updateVoiceUi("Voz detenida · Revisá el resultado antes de continuar");}
        message(error.getMessage() == null ? "No se pudo completar. Revisá la conexión y reintentá." : error.getMessage());
        if(announce && ttsReady)speak("No pude completar la operación. Revisá la pantalla y el estado del producto antes de activar la voz nuevamente.");
    }
    private JSONObject json(String method, String path, JSONObject body) throws Exception { return new JSONObject(api.request(method,path,body)); }
    private static JSONObject obj(Object... pairs) {
        JSONObject o = new JSONObject();
        try { for (int i=0;i<pairs.length;i+=2) o.put((String)pairs[i],pairs[i+1]); } catch (JSONException e) { throw new IllegalArgumentException(e); }
        return o;
    }
    private int stage() { return !demo && user != null && user.optString("role").equals("palletizador") ? 4 : 0; }
    private String path() { return "/load-control/loads/" + load.optInt("id") + "/courts/" + court.optInt("numero") + "/checks/" + stage() + "/" + check.optString("id"); }
    private void login() {
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
            try { api = new Api(host.getText().toString()); } catch (Exception e) { error(e); return; }
            String username = name.getText().toString().trim(), secret = password.getText().toString();
            if (username.isEmpty() || secret.isEmpty()) { message("Completá usuario y contraseña."); return; }
            task(() -> {
                JSONObject auth = json("POST","/auth/login",obj("username",username,"password",secret));
                JSONObject person = auth.getJSONObject("user");
                if (!Arrays.asList("operador", "palletizador").contains(person.getString("role"))) throw new Exception("Esta app está destinada a cuentas de operador.");
                api.token = auth.getString("token");
                // Fail closed: the native app cannot silently show every court.
                JSONObject permissions = json("GET","/load-control/my-courts",null);
                JSONArray courts = permissions.getJSONArray("courts");
                assigned.clear(); for (int i=0;i<courts.length();i++) assigned.add(courts.getInt(i));
                if (assigned.isEmpty()) throw new Exception("No tenés canchas asignadas. Pedile la asignación al supervisor.");
                return person;
            }, person -> {
                user = person; password.setText(""); getPreferences(0).edit().putString("server",api.base).apply(); listLoads();
            });
        });
        button("Configurar servidor",()->serverFields.setVisibility(serverFields.getVisibility()==View.GONE?View.VISIBLE:View.GONE));
        content=body;
        content=card(BORDER);text("Probá antes de empezar",18);text("Conocé los comandos y comprobá el audio sin modificar las cargas.",14);
        button("Probar voz sin guardar datos", this::demo);
        content=body;text("Versión 0.7.0 · Para guardar necesitás conexión.",12);
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
        for (int i=0;i<checks.length();i++) { JSONObject x=checks.optJSONObject(i); if (x.optInt("stage") == stage())
            return x.optString("status").equals("done") ? "Finalizados" : x.isNull("timer_started_at") ? "Pausados" : "En curso"; }
        return "Sin iniciar";
    }
    private boolean matches(JSONObject c) { return assigned.contains(c.optInt("numero")) && (filter.equals("Todos") || filter.equals(processState(c))); }
    private String amount(JSONObject data,String key) {
        if(data.isNull(key) || !data.has(key))return "Pendiente";
        return java.text.NumberFormat.getNumberInstance(new java.util.Locale("es","AR")).format(data.optDouble(key));
    }
    private String summarySpeech(JSONObject summary) {
        if(summary==null)return "El resumen del camión no está disponible. ";
        if(summary.isNull("pallets"))return "Plan de armado pendiente. Consultá al supervisor para conocer tus pallets y cantidades asignadas.";
        String speech="Carga total del camión: "+summary.optInt("loads")+" repartos, "+summary.optInt("courts")+" canchas. "+amount(summary,"pallets")+" pallets físicos previstos. ";
        JSONObject mine=summary.optJSONObject("mine");
        if(mine!=null){
            speech+="Tu trabajo: "+mine.optInt("loads")+" repartos y "+mine.optInt("courts")+" canchas. "+amount(mine,"bultos")+" bultos y "+amount(mine,"unidades")+" unidades. Participa en "+amount(mine,"pallets")+" pallets. ";
            if(!mine.isNull("hl"))speech+=amount(mine,"hl")+" hectolitros. ";
            if(stage()==0 && mine.optInt("full_pallets_info")>0)speech+=mine.optInt("full_pallets_info")+" pallets completos se preparan por separado. ";
        }
        return speech;
    }
    private String destinations(JSONObject product) {
        if(demo || stage()!=0 || load==null || court==null)return "";
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
                    result.append(ProductSpeech.destination(pallet.optString("id"),item.optInt("bultos"),item.optInt("unidades"),pallet.optBoolean("shared")));
            }
        }
        return result.length()==0?"Destino de pallet no disponible. Consultá al supervisor. ":result.toString();
    }
    private void truckSummary(JSONObject summary,boolean waiting) {
        if(summary==null)return;
        content=card(BORDER);text("Este camión · Carga seleccionada",20);
        button("Escuchar resumen del camión",()->speak(summarySpeech(summary)));
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
        currentScreen = "loads"; voice=false; check = null; court = null;
        stopAudio(); check=null; screen("Tu próximo trabajo");
        content=card(BORDER);text("Hola, "+user.optString("username"),22);
        List<Integer> sortedCourts=new ArrayList<>(assigned);Collections.sort(sortedCourts);
        TextView assignments=text("Tus canchas: " + sortedCourts,14);content=body;
        task(this::fetchQueue, response -> {
            queueVersion=queueVersion(response);
            assigned.clear(); JSONArray permissions=response.getJSONObject("permissions").getJSONArray("courts");
            for(int i=0;i<permissions.length();i++) assigned.add(permissions.getInt(i));
            List<Integer> refreshed=new ArrayList<>(assigned);Collections.sort(refreshed);assignments.setText("Tus canchas: "+refreshed);
            JSONArray trucks=response.getJSONArray("trucks");
            if(announceQueue){
                announceQueue=false;
                if(trucks.length()==0)speak("Cancha finalizada. No tenés más camiones habilitados pendientes.");
                else {JSONObject next=trucks.getJSONObject(0);speak("Cancha finalizada. Tu camión actual es "+next.optString("truck")+". "+summarySpeech(next.optJSONObject("summary"))+"Elegí el reparto y la cancha para continuar.");}
            }
            int found=0;
            for(int t=0;t<trucks.length();t++) { JSONObject truck=trucks.getJSONObject(t); JSONArray loads=truck.getJSONArray("loads");
                content=card(BORDER);text("Camión actual: "+truck.optString("truck"),22);
                text(truck.optString("load_date")+" · "+loads.length()+" cargas",15);
                JSONObject summary=truck.optJSONObject("summary"), mine=summary==null?null:summary.optJSONObject("mine");
                if(mine!=null && !summary.isNull("pallets"))text(mine.optInt("finished_tasks")+" de "+mine.optInt("tasks")+" tareas finalizadas",18);
                JSONObject nextLoad=null,nextCourt=null;int best=99;
                for(int l=0;l<loads.length();l++){
                    JSONObject candidate=loads.getJSONObject(l);JSONArray candidates=candidate.getJSONArray("canchas");
                    for(int c=0;c<candidates.length();c++){
                        JSONObject taskCourt=candidates.getJSONObject(c);
                        if(!assigned.contains(taskCourt.optInt("numero")) || taskCourt.optInt("cantidad")==0 || !taskCourt.optBoolean("can_prepare",true))continue;
                        String state=processState(taskCourt);int rank=state.equals("En curso")?0:state.equals("Pausados")?1:state.equals("Sin iniciar")?2:99;
                        if(rank<best){best=rank;nextLoad=candidate;nextCourt=taskCourt;}
                    }
                }
                if(nextLoad!=null && !truck.optString("planning_status").equals("pending")){
                    final int loadId=nextLoad.optInt("id"),courtNumber=nextCourt.optInt("numero");
                    text("Próxima tarea: reparto "+nextLoad.optString("reparto")+" · Cancha "+courtNumber,16);
                    styledButton("Continuar picking →",GREEN,Color.WHITE,GREEN,()->{filter="Todos";openLoad(loadId,courtNumber);});
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
                            if(!assigned.contains(taskCourt.optInt("numero")))continue;
                            total++;if(processState(taskCourt).equals("Finalizados"))done++;
                        }
                        text("Tus canchas: "+done+" de "+total+" finalizadas",14);
                        for(int c=0;c<courts.length();c++){
                            JSONObject taskCourt=courts.getJSONObject(c);if(!matches(taskCourt))continue;
                            gap(8);text("Cancha "+taskCourt.optInt("numero")+" · "+processState(taskCourt),18);
                            text(taskCourt.optInt("cantidad")+" productos",14);
                            button("Ver cancha "+taskCourt.optInt("numero")+" →",()->openLoad(item.optInt("id"),taskCourt.optInt("numero")));
                        }
                        content=tasksPanel;
                    }
                }
                content=body;
            }
            message(trucks.length()==0 ? "No tenés camiones habilitados pendientes. Actualizá o consultá al supervisor." : "");
            button("Actualizar trabajo",this::listLoads);
            content=disclosure("Mi sesión");button("Cerrar sesión", this::login);text("Del Palacio · Android 0.13.0",12);content=body;
        });
    }
    private void openLoad(int id) {
        openLoad(id,0);
    }
    private void openLoad(int id,int selectedCourt) {
        task(() -> json("GET","/load-control/loads/"+id,null), result -> {
            currentScreen = "courts"; check = null; court = null;
            load=result; screen("Reparto " + load.optString("reparto")); button("Volver a cargas",this::listLoads);
            if(load.optString("planning_status").equals("legacy"))text("Carga anterior en control. No permite iniciar un armado nuevo; consultá al supervisor.",16);
            content=disclosure("Ver resumen del camión");truckSummary(load.optJSONObject("truck_summary"),false);
            JSONArray courts=load.getJSONArray("canchas"); int count=0;
            for(int i=0;i<courts.length();i++) { JSONObject c=courts.getJSONObject(i); if(!matches(c) || (selectedCourt>0 && selectedCourt!=c.optInt("numero"))) continue; count++;
                content=card(BORDER);String state=processState(c); text("Cancha " + c.optInt("numero"),22);text(state+" · "+c.optJSONArray("productos").length()+" productos",14);
                if(stage()==0 && c.optInt("full_pallet_count")>0){
                    text("Pallets completos · Información",16);
                    JSONArray full=c.optJSONArray("full_pallets_info");
                    if(full!=null)for(int n=0;n<full.length();n++){JSONObject item=full.optJSONObject(n);text(item.optInt("pallets")+" pallets · "+item.optString("descripcion")+" ("+item.optInt("bultos")+" bultos)",13);}
                    text("Se registran por separado del picking de bultos y unidades sueltas.",12);
                }
                if(!state.equals("Finalizados") && c.optJSONArray("productos").length()>0 && c.optBoolean("can_prepare",true)) styledButton("Iniciar / retomar cancha " + c.optInt("numero"),GREEN,Color.WHITE,GREEN, () -> startCourt(c));
                else if(c.optJSONArray("productos").length()==0)text("Esta cancha solo tiene pallets completos; no requiere picking de sueltos.",14);
                content=body;
            }
            if(count==0) message("No hay canchas asignadas que coincidan con el filtro.");
        });
    }
    private void startCourt(JSONObject c) {
        task(() -> {
            JSONObject started=json("POST","/load-control/loads/"+load.optInt("id")+"/courts/"+c.optInt("numero")+"/start/"+stage(),obj());
            return obj("check",started,"load",json("GET","/load-control/loads/"+load.optInt("id"),null));
        }, result -> {
            load=result.getJSONObject("load");court=c; check=result.getJSONObject("check"); products=check.getJSONArray("products"); index=0;
            JSONObject answers=check.getJSONObject("answers"); while(index<products.length()-1 && answers.has(products.getJSONObject(index).getString("sku"))) index++;
            product();
        });
    }
    private String prompt() {
        JSONObject p=products.optJSONObject(index);
        return ProductSpeech.prompt(p.optString("descripcion_voz",p.optString("descripcion")),p.optInt("bultos"),p.optInt("unidades"),p.optInt("pallets"),stage(),index,products.length())+" "+destinations(p);
    }
    private void product() {
        currentScreen = "product";
        if(products.length()==0) { message("La cancha no tiene productos."); return; }
        JSONObject p=products.optJSONObject(index); screen((stage() == 4 ? "Pallets completos" : "Picking") + " · Cancha " + court.optInt("numero"));
        content=card(BORDER);
        text("SKU " + p.optString("sku")+(p.optString("almacen").isEmpty()?"":" · "+p.optString("almacen")),12);
        text(p.optString("descripcion"),24);
        String destination=destinations(p);
        if(!destination.isEmpty())text(destination,17);
        if(stage() == 4) text(p.optInt("pallets") + " PALLETS COMPLETOS", 28);
        gap(8);LinearLayout amounts=row();content.addView(amounts);
        for(int i=0;i<2;i++){
            LinearLayout box=column();box.setGravity(Gravity.CENTER);box.setPadding(dp(8),dp(8),dp(8),dp(8));box.setBackground(shape(BG,BG,12));
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);if(i==0)lp.rightMargin=dp(10);amounts.addView(box,lp);
            TextView caption=label(i==0?"BULTOS DE LA\nPLANILLA":"UNIDADES DE LA\nPLANILLA",10,MUTED,false);caption.setGravity(Gravity.CENTER);box.addView(caption);
            TextView amount=label(String.valueOf(p.optInt(i==0?"bultos":"unidades")),40,INK,true);amount.setGravity(Gravity.CENTER);box.addView(amount);
        }
        if(check.optJSONObject("answers").has(p.optString("sku"))) text("Este producto ya tiene una respuesta guardada.",16);
        if(stage()==0 && p.optInt("full_pallets_count")>0){
            gap(6);TextView full=text("Pallets completos: "+p.optInt("full_pallets_count")+" · "+p.optInt("full_pallets_bultos")+" bultos",14);full.setTextColor(dark?0xff7dd3fc:0xff0369a1);
            text("Informativo · Se registran por separado del picking indicado arriba.",12);
        }
        content=body;voicePanel();
        boolean paused=check.isNull("timer_started_at");
        if(paused) { message("Proceso pausado. Reanudalo antes de registrar."); button("Reanudar picking", () -> startCourt(court)); }
        else { styledButton("Correcto →",GREEN,Color.WHITE,GREEN, () -> answer(obj("result","ok")));styledButton("Faltante real",0xfffff1f2,RED,0xfffda4af,this::shortage); }
        LinearLayout navigation=row();content.addView(navigation);content=navigation;
        Button previous=styledButton("← Anterior",Color.WHITE,INK,BORDER,()->{if(index>0){index--;product();}});
        Button next=styledButton("Siguiente →",Color.WHITE,INK,BORDER,()->{if(index<products.length()-1){index++;product();}});
        LinearLayout.LayoutParams left=new LinearLayout.LayoutParams(0,-2,1);left.rightMargin=dp(10);previous.setLayoutParams(left);next.setLayoutParams(new LinearLayout.LayoutParams(0,-2,1));
        previous.setEnabled(index>0);previous.setAlpha(index>0?1:0.45f);next.setEnabled(index<products.length()-1);next.setAlpha(index<products.length()-1?1:0.45f);
        content=body;gap(10);text("Siguiente permite revisar sin confirmar el producto.",12);
        button("Escuchar / repetir producto", () -> speak(prompt()));
        button("Pausar y volver a canchas",this::pauseAndLeave);
        text("Reparto "+load.optString("reparto")+" · "+user.optString("username"),12);
        LinearLayout footer=column();footer.setPadding(dp(16),dp(10),dp(16),dp(4));footer.setBackgroundColor(SURFACE);root.addView(footer);content=footer;
        button("Finalizar picking", () -> { stopAudio(); new AlertDialog.Builder(this).setTitle("Finalizar picking")
            .setMessage(check.optJSONObject("answers").length()+" de "+products.length()+" productos registrados. ¿Finalizar?")
            .setNegativeButton("Seguir",(d,w)->product()).setOnCancelListener(d->product()).setPositiveButton("Finalizar",(d,w)->finishPicking()).show(); });
        content=body;
        if(voice && !paused) speak(prompt());
    }
    private void answer(JSONObject data) {
        if(busy || check==null || check.isNull("timer_started_at")) return;
        stopAudio();
        try { data.put("sku",products.getJSONObject(index).getString("sku")); } catch(Exception e) {error(e);return;}
        if(demo) { try { check.getJSONObject("answers").put(data.getString("sku"),data); } catch(Exception e){error(e);} afterAnswer();return; }
        task(() -> json("POST",path()+"/answer",data), result -> {check=result;afterAnswer();});
    }
    private void afterAnswer() {
        if(index<products.length()-1) {index++;product();}
        else {voice=false;product();speak("Último producto registrado. Revisá el avance y tocá finalizar picking.");}
    }
    private void shortage() {
        stopAudio();
        showShortage();
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
        shortageFeedback=text("",16);shortageFeedback.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        android.text.TextWatcher watcher=new android.text.TextWatcher(){
            public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            public void onTextChanged(CharSequence s,int start,int before,int count){shortageFeedback.setText(ShortageAmounts.summary(shortageB.getText().toString(),shortageU.getText().toString(),p.optInt("bultos"),p.optInt("unidades")));}
            public void afterTextChanged(android.text.Editable s){}
        };
        shortageB.addTextChangedListener(watcher);shortageU.addTextChangedListener(watcher);watcher.onTextChanged("",0,0,0);
        styledButton("Registrar faltante",RED,Color.WHITE,RED,() -> {
            try {
                String validation=ShortageAmounts.error(shortageB.getText().toString(),shortageU.getText().toString(),p.optInt("bultos"),p.optInt("unidades"));
                if(!validation.isEmpty()){shortageFeedback.setText(validation);return;}
                int physicalB=Integer.parseInt(shortageB.getText().toString()),physicalU=Integer.parseInt(shortageU.getText().toString());
                int responsible=demo?0:user.getInt("id");
                answer(obj("result","shortage","physical_b",physicalB,"physical_u",physicalU,"responsible_user_id",responsible,"origin","picking","note",note.getText().toString()));
            } catch(Exception e) {error(e);}
        });
        button("Cancelar",()->{stopAudio();product();});content=body;
        text("El faltante se confirma con un toque. La voz solo completa las cantidades; revisalas antes de guardar.",12);
        if(voice)speak("Decí la cantidad que encontraste, no lo que falta. Si no encontraste nada, tocá No encontré nada. Revisá y tocá Registrar faltante para guardar.");
    }
    private void pauseAndLeave() {
        voice=false;stopAudio();
        if(demo){login();return;}
        filter="Todos";
        if(check.isNull("timer_started_at")){openLoad(load.optInt("id"));return;}
        task(() -> json("POST",path()+"/pause",obj()), result -> { check=result; openLoad(load.optInt("id")); });
    }
    private void finishPicking() {
        voice=false;stopAudio();
        if(demo){login();message("Demostración finalizada. No se guardaron datos.");return;}
        task(() -> json("POST",path()+"/finish",obj()), result -> {filter="Todos";announceQueue=true;listLoads();});
    }
    private void enableVoice() {
        if(!visible || busy || check==null || check.isNull("timer_started_at") || !(currentScreen.equals("product") || currentScreen.equals("shortage")))return;
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
    private void activateVoice(){updateVoiceUi("Leyendo…");speak(currentScreen.equals("shortage")?"Decí los bultos y unidades físicos. Revisá y confirmá con el botón.":"Reparto "+load.optString("reparto")+". Cancha "+court.optInt("numero")+". "+prompt());}
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
        if(!voice || voiceSession==null || check==null || check.isNull("timer_started_at"))return;
        voiceSession.listen();
    }
    private void command(String text) {
        if(text.trim().isEmpty())return;
        lastHeard=text;if(heardView!=null)heardView.setText("Escuché: “"+text+"”");
        if(currentScreen.equals("shortage")){
            Integer[] values=VoiceQuantities.parse(text);
            if(values==null){message("Decí cantidades, por ejemplo: dos bultos tres unidades. Para guardar usá el botón.");return;}
            JSONObject p=products.optJSONObject(index);
            if((values[0]!=null && values[0]>p.optInt("bultos")) || (values[1]!=null && values[1]>p.optInt("unidades"))){message("La cantidad dictada supera la planilla. Repetila o corregila a mano.");return;}
            if(values[0]!=null){shortageB.setText(values[0].toString());shortageB.setBackground(shape(Color.WHITE,GREEN,12));bHint.setText("Completado por voz");bHint.setTextColor(GREEN);}
            if(values[1]!=null){shortageU.setText(values[1].toString());shortageU.setBackground(shape(Color.WHITE,GREEN,12));uHint.setText("Completado por voz");uHint.setTextColor(GREEN);}
            message("Revisá las cantidades y tocá Registrar faltante.");return;
        }
        if(!currentScreen.equals("product"))return;
        switch(VoiceCommands.parse(text)){
            case "ok" -> answer(obj("result","ok"));
            case "shortage" -> shortage();
            case "repeat" -> speak(prompt());
            case "next" -> {if(index<products.length()-1){index++;product();}}
            case "prev" -> {if(index>0){index--;product();}}
            default -> message("No entendí. Decí correcto, faltante o repetir.");
        }
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
        if(currentScreen.equals("courts")){listLoads();return;}
        new AlertDialog.Builder(this).setTitle("Salir de la app")
            .setMessage("¿Querés salir de Del Palacio Picking?")
            .setNegativeButton("Quedarme",null).setPositiveButton("Salir",(d,w)->finish()).show();
    }
    @Override protected void onDestroy(){requestVersion++;voice=false;stopAudio();if(tts!=null)tts.shutdown();handler.removeCallbacksAndMessages(null);network.shutdown();super.onDestroy();}
}
