package com.delpalacio.picking;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
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
import org.vosk.Model;
import org.vosk.Recognizer;
import org.vosk.android.RecognitionListener;
import org.vosk.android.SpeechService;
import org.vosk.android.StorageService;
import java.util.*;
import java.util.concurrent.*;

public final class MainActivity extends Activity {
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private LinearLayout content;
    private LinearLayout root, body;
    private TextView status;
    private TextView voiceStatus, heardView, clockView, bHint, uHint;
    private Button voiceButton;
    private EditText shortageB, shortageU;
    private String lastHeard="";
    private static final int INK=0xff0f172a, MUTED=0xff607493, GREEN=0xff059669, RED=0xffb91c1c, BORDER=0xffdce5ef, BG=0xfff0f5f9;
    private final Runnable clockTick=new Runnable(){public void run(){updateClock();handler.postDelayed(this,1000);}};
    private Api api;
    private JSONObject user, load, court, check;
    private JSONArray products = new JSONArray(), operators = new JSONArray();
    private Set<Integer> assigned = new HashSet<>();
    private String filter = "Todos";
    private String currentScreen = "login";
    private int index = 0, requestVersion = 0, speechVersion = 0;
    private boolean demo = false, busy = false, voice = false, visible = false, ttsReady = false, modelLoading = false;
    private TextToSpeech tts;
    private Model model;
    private SpeechService service;
    private Recognizer recognizer;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.WHITE);
        getWindow().setNavigationBarColor(Color.WHITE);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
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
        GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));d.setStroke(dp(1),border);return d;
    }
    private TextView label(String value,int size,int color,boolean bold) {
        TextView v=new TextView(this);v.setText(value);v.setTextSize(size);v.setTextColor(color);
        if(bold)v.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
        v.setIncludeFontPadding(false);v.setPadding(0,dp(3),0,dp(3));return v;
    }
    private LinearLayout column(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.VERTICAL);return v;}
    private LinearLayout row(){LinearLayout v=new LinearLayout(this);v.setGravity(Gravity.CENTER_VERTICAL);return v;}
    private void gap(int height){View v=new View(this);content.addView(v,new LinearLayout.LayoutParams(1,dp(height)));}
    private LinearLayout card(int border){
        LinearLayout v=column();v.setPadding(dp(14),dp(12),dp(14),dp(12));v.setBackground(shape(Color.WHITE,border,16));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(12);content.addView(v,lp);return v;
    }
    private void screen(String title) {
        voiceStatus=null;heardView=null;voiceButton=null;clockView=null;shortageB=null;shortageU=null;
        root=column();root.setBackgroundColor(BG);root.setFitsSystemWindows(true);
        boolean working=currentScreen.equals("product") || currentScreen.equals("shortage");
        LinearLayout header=column();header.setBackgroundColor(Color.WHITE);header.setPadding(dp(16),dp(8),dp(16),dp(10));root.addView(header);
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
        gap(10);heardView=text(lastHeard.isEmpty()?"Todavía no escuché un comando":"Escuché: “"+lastHeard+"”",14);heardView.setTextColor(0xff047857);heardView.setPadding(dp(12),dp(10),dp(12),dp(10));heardView.setBackground(shape(0xffecfdf5,0xffa7f3d0,8));
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
    private void error(Exception error) { message(error.getMessage() == null ? "No se pudo completar. Revisá la conexión y reintentá." : error.getMessage()); }
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
        content=body;text("Versión 0.5.0 · Para guardar necesitás conexión.",12);
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
    private void listLoads() {
        currentScreen = "loads"; check = null; court = null;
        stopAudio(); check=null; screen("Mis cargas");
        content=card(BORDER);text("Hola, "+user.optString("username"),22);
        List<Integer> sortedCourts=new ArrayList<>(assigned);Collections.sort(sortedCourts);
        TextView assignments=text("Tus canchas: " + sortedCourts,14);text("Elegí una carga habilitada para comenzar o retomar tu trabajo.",14);content=body;
        content=card(BORDER);text("Estado del trabajo",13);
        Spinner options = new Spinner(this); options.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"Todos","En curso","Sin iniciar","Pausados","Finalizados"}));
        content.addView(options); options.setSelection(Arrays.asList("Todos","En curso","Sin iniciar","Pausados","Finalizados").indexOf(filter));
        button("Aplicar filtro / actualizar", () -> { filter=options.getSelectedItem().toString(); listLoads(); });
        content=body;
        task(() -> obj("permissions", json("GET","/load-control/my-courts",null), "trucks", new JSONArray(api.request("GET","/load-control/trucks",null))), response -> {
            assigned.clear(); JSONArray permissions=response.getJSONObject("permissions").getJSONArray("courts");
            for(int i=0;i<permissions.length();i++) assigned.add(permissions.getInt(i));
            List<Integer> refreshed=new ArrayList<>(assigned);Collections.sort(refreshed);assignments.setText("Tus canchas: "+refreshed);
            JSONArray trucks=response.getJSONArray("trucks");
            int found=0;
            for(int t=0;t<trucks.length();t++) { JSONObject truck=trucks.getJSONObject(t); JSONArray loads=truck.getJSONArray("loads");
                for(int l=0;l<loads.length();l++) { JSONObject item=loads.getJSONObject(l); JSONArray courts=item.getJSONArray("canchas"); boolean show=false;
                    for(int c=0;c<courts.length();c++) if(matches(courts.getJSONObject(c))) show=true;
                    if(show) {
                        found++;content=card(BORDER);text("Camión "+truck.optString("truck"),20);
                        text("Reparto "+item.optString("reparto")+" · "+truck.optString("load_date"),14);
                        styledButton("Ver canchas →",GREEN,Color.WHITE,GREEN,()->openLoad(item.optInt("id")));content=body;
                    }
                }
            }
            message(found == 0 ? "Sin cargas para tus canchas y este filtro. El supervisor debe habilitar las cargas desde la web." : "Elegí una carga. Filtro: " + filter);
            button("Cerrar sesión", this::login);text("Del Palacio · Android 0.5.0",12);
        });
    }
    private void openLoad(int id) {
        task(() -> json("GET","/load-control/loads/"+id,null), result -> {
            currentScreen = "courts"; check = null; court = null;
            load=result; screen("Reparto " + load.optString("reparto")); button("Volver a cargas",this::listLoads);
            JSONArray courts=load.getJSONArray("canchas"); int count=0;
            for(int i=0;i<courts.length();i++) { JSONObject c=courts.getJSONObject(i); if(!matches(c)) continue; count++;
                content=card(BORDER);String state=processState(c); text("Cancha " + c.optInt("numero"),22);text(state+" · "+c.optJSONArray("productos").length()+" productos",14);
                if(!state.equals("Finalizados")) styledButton("Iniciar / retomar cancha " + c.optInt("numero"),GREEN,Color.WHITE,GREEN, () -> startCourt(c));
                content=body;
            }
            if(count==0) message("No hay canchas asignadas que coincidan con el filtro.");
        });
    }
    private void startCourt(JSONObject c) {
        task(() -> json("POST","/load-control/loads/"+load.optInt("id")+"/courts/"+c.optInt("numero")+"/start/"+stage(),obj()), result -> {
            court=c; check=result; products=result.getJSONArray("products"); index=0;
            JSONObject answers=check.getJSONObject("answers"); while(index<products.length()-1 && answers.has(products.getJSONObject(index).getString("sku"))) index++;
            product();
        });
    }
    private String prompt() {
        JSONObject p=products.optJSONObject(index);
        if (stage() == 4) return "Prepará " + p.optInt("pallets") + " pallets completos de " + p.optString("descripcion_voz", p.optString("descripcion")) + ". Cuando termines, decí correcto.";
        return "Producto " + (index+1) + " de " + products.length() + ". Agarrá " + p.optInt("bultos") + " bultos y " + p.optInt("unidades") + " unidades de " + p.optString("descripcion_voz", p.optString("descripcion")) + ". Cuando termines, decí correcto. Si falta mercadería, decí faltante.";
    }
    private void product() {
        currentScreen = "product";
        if(products.length()==0) { message("La cancha no tiene productos."); return; }
        JSONObject p=products.optJSONObject(index); screen((stage() == 4 ? "Pallets completos" : "Picking") + " · Cancha " + court.optInt("numero"));
        content=card(BORDER);
        text("SKU " + p.optString("sku")+(p.optString("almacen").isEmpty()?"":" · "+p.optString("almacen")),12);
        text(p.optString("descripcion"),24);
        if(stage() == 4) text(p.optInt("pallets") + " PALLETS COMPLETOS", 28);
        gap(8);LinearLayout amounts=row();content.addView(amounts);
        for(int i=0;i<2;i++){
            LinearLayout box=column();box.setGravity(Gravity.CENTER);box.setPadding(dp(8),dp(8),dp(8),dp(8));box.setBackground(shape(BG,BG,12));
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);if(i==0)lp.rightMargin=dp(10);amounts.addView(box,lp);
            TextView caption=label(i==0?"BULTOS DE LA\nPLANILLA":"UNIDADES DE LA\nPLANILLA",10,MUTED,false);caption.setGravity(Gravity.CENTER);box.addView(caption);
            TextView amount=label(String.valueOf(p.optInt(i==0?"bultos":"unidades")),40,INK,true);amount.setGravity(Gravity.CENTER);box.addView(amount);
        }
        if(check.optJSONObject("answers").has(p.optString("sku"))) text("Este producto ya tiene una respuesta guardada.",16);
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
        LinearLayout footer=column();footer.setPadding(dp(16),dp(10),dp(16),dp(4));footer.setBackgroundColor(Color.WHITE);root.addView(footer);content=footer;
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
        text(p.optString("descripcion")+" · planilla: "+p.optInt("bultos")+" bultos + "+p.optInt("unidades")+" unidades",13);gap(8);
        LinearLayout form=content, quantities=row();content.addView(quantities);
        for(int i=0;i<2;i++){
            LinearLayout field=column();LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);if(i==0)lp.rightMargin=dp(10);quantities.addView(field,lp);content=field;
            text(i==0?"Bultos físicos":"Unidades físicas",12);EditText value=input(i==0?"Bultos físicos":"Unidades físicas",InputType.TYPE_CLASS_NUMBER);value.setTextSize(22);value.setText("0");
            TextView hint=text("Tocá para corregir",11);
            if(i==0){shortageB=value;bHint=hint;}else{shortageU=value;uHint=hint;}
        }
        content=form;gap(8);text("Proceso al que corresponde",13);TextView origin=text(stage()==4?"Pallets completos":"Picking",16);origin.setPadding(dp(14),dp(14),dp(14),dp(14));origin.setBackground(shape(Color.WHITE,0xffcbd5e1,12));
        text("Responsable: "+user.optString("username"),12);gap(4);
        text("Observación (opcional)",13); EditText note=input("Escribí qué pasó con el producto…",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE);note.setSingleLine(false);note.setMinLines(3);note.setGravity(Gravity.TOP);
        styledButton("Registrar faltante",RED,Color.WHITE,RED,() -> {
            try {
                int physicalB=Integer.parseInt(shortageB.getText().toString()),physicalU=Integer.parseInt(shortageU.getText().toString());
                if(physicalB<0 || physicalU<0 || physicalB>p.optInt("bultos") || physicalU>p.optInt("unidades") || (physicalB==p.optInt("bultos") && physicalU==p.optInt("unidades"))) throw new Exception("Las cantidades deben ser menores a la planilla y no negativas.");
                int responsible=demo?0:user.getInt("id");
                answer(obj("result","shortage","physical_b",physicalB,"physical_u",physicalU,"responsible_user_id",responsible,"origin","picking","note",note.getText().toString()));
            } catch(Exception e) {error(e);}
        });
        button("Cancelar",()->{stopAudio();product();});content=body;
        text("El faltante se confirma con un toque. La voz solo completa las cantidades; revisalas antes de guardar.",12);
        if(voice)speak("Indicá los bultos y unidades físicos. Para guardar el faltante, tocá Registrar faltante.");
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
        task(() -> json("POST",path()+"/finish",obj()), result -> listLoads());
    }
    private void enableVoice() {
        if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED) {requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},10);return;}
        if(!ttsReady){message("Activá o instalá una voz en español en los ajustes de texto a voz de Android.");return;}
        if(modelLoading) return;
        if(model==null){modelLoading=true;message("Preparando el modelo español. Esperá…");StorageService.unpack(this,"model-es","voice-model", ready->{
            modelLoading=false;if(isDestroyed()){ready.close();return;}model=ready;if(visible && check!=null && (currentScreen.equals("product") || currentScreen.equals("shortage")))activateVoice();
        },error->{modelLoading=false;if(!isDestroyed())error(error);});}
        else activateVoice();
    }
    private void activateVoice(){voice=true;updateVoiceUi("Leyendo…");speak(currentScreen.equals("shortage")?"Decí los bultos y unidades físicos. Revisá y confirmá con el botón.":prompt());}
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] grants) {
        super.onRequestPermissionsResult(request,permissions,grants);
        if(request==10 && grants.length>0 && grants[0]==PackageManager.PERMISSION_GRANTED) enableVoice();
        else message("Sin permiso de micrófono. Podés continuar con los botones.");
    }
    private void speak(String value) {
        stopAudio();
        if(!ttsReady){message("No hay voz española disponible. Revisá Texto a voz en Android.");return;}
        int generation=++speechVersion;
        updateVoiceUi("Leyendo…");
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener(){
            @Override public void onStart(String id){}
            @Override public void onDone(String id){handler.postDelayed(()->{if(generation==speechVersion && visible && !busy){if(voice)startMic();else updateVoiceUi("Voz desactivada");}},400);}
            @Override public void onError(String id){handler.post(()->{if(generation==speechVersion)message("No se pudo leer el producto. Revisá el volumen multimedia.");});}
        });
        if(tts.speak(value,TextToSpeech.QUEUE_FLUSH,null,"product-"+generation)==TextToSpeech.ERROR) message("No se pudo iniciar la lectura.");
    }
    private void startMic() {
        if(!voice || !visible || model==null || check==null || check.isNull("timer_started_at"))return;
        stopMic(); int generation=speechVersion;
        try {
            recognizer=new Recognizer(model,16000,VoiceCommands.grammar()); service=new SpeechService(recognizer,16000);
            service.startListening(new RecognitionListener(){
                @Override public void onPartialResult(String value){}
                @Override public void onResult(String value){handler.post(()->{if(generation!=speechVersion || !voice || busy || !visible)return;try{command(new JSONObject(value).optString("text"));}catch(Exception e){error(e);}});}
                @Override public void onFinalResult(String value){}
                @Override public void onError(Exception e){handler.post(()->{if(generation==speechVersion){voice=false;stopMic();updateVoiceUi("Voz detenida");error(e);}});}
                @Override public void onTimeout(){handler.post(()->{if(generation==speechVersion){voice=false;stopMic();updateVoiceUi("Voz detenida");message("Escucha detenida. Tocá Activar voz.");}});}
            }); updateVoiceUi("Escuchando…");
        } catch(Exception e){voice=false;stopMic();error(e);}
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
    private void stopMic(){if(service!=null){service.stop();service.shutdown();service=null;}if(recognizer!=null){recognizer.close();recognizer=null;}}
    private void stopAudio(){speechVersion++;stopMic();if(tts!=null)tts.stop();}
    @Override protected void onResume(){super.onResume();visible=true;handler.removeCallbacks(clockTick);handler.post(clockTick);}
    @Override protected void onPause(){visible=false;voice=false;stopAudio();updateVoiceUi("Voz desactivada");handler.removeCallbacks(clockTick);super.onPause();}
    @Override public void onBackPressed(){
        if(busy){message("Esperá a que termine la operación.");return;}
        if(currentScreen.equals("shortage")){stopAudio();product();return;}
        if(currentScreen.equals("product")){pauseAndLeave();return;}
        if(currentScreen.equals("courts")){listLoads();return;}
        new AlertDialog.Builder(this).setTitle("Salir de la app")
            .setMessage("¿Querés salir de Del Palacio Picking?")
            .setNegativeButton("Quedarme",null).setPositiveButton("Salir",(d,w)->finish()).show();
    }
    @Override protected void onDestroy(){requestVersion++;stopAudio();if(tts!=null)tts.shutdown();if(model!=null)model.close();network.shutdown();super.onDestroy();}
}
