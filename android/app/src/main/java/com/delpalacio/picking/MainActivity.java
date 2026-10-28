package com.delpalacio.picking;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.text.InputType;
import android.view.View;
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
    private TextView status;
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
        getWindow().setStatusBarColor(Color.rgb(14, 69, 107));
        getWindow().setNavigationBarColor(Color.WHITE);
        tts = new TextToSpeech(this, result -> {
            if (result == TextToSpeech.SUCCESS) {
                int language = tts.setLanguage(new Locale("es", "AR"));
                ttsReady = language != TextToSpeech.LANG_MISSING_DATA && language != TextToSpeech.LANG_NOT_SUPPORTED;
            }
        });
        login();
    }
    private int dp(int n) { return Math.round(n * getResources().getDisplayMetrics().density); }
    private void screen(String title) {
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(242, 246, 250)); root.setFitsSystemWindows(true);
        TextView header = new TextView(this); header.setText("DEL PALACIO\n" + title); header.setTextSize(22);
        header.setTextColor(Color.WHITE); header.setBackgroundColor(Color.rgb(14, 69, 107)); header.setPadding(dp(20),dp(20),dp(20),dp(20));
        root.addView(header);
        ScrollView scroll = new ScrollView(this); content = new LinearLayout(this); content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(20),dp(12),dp(20),dp(20)); scroll.addView(content); root.addView(scroll);
        setContentView(root); status = text(demo ? "DEMOSTRACIÓN · No guarda datos" : "Servidor compartido · Las confirmaciones se guardan", 14);
        if (user != null) text("Usuario: " + user.optString("username") + " · Versión 0.4.0", 14);
    }
    private TextView text(String value, int size) {
        TextView v = new TextView(this); v.setText(value); v.setTextSize(size); v.setTextColor(Color.rgb(20,45,65));
        v.setPadding(0,dp(8),0,dp(8)); content.addView(v); return v;
    }
    private EditText input(String hint, int type) {
        EditText v = new EditText(this); v.setHint(hint); v.setTextSize(18); v.setInputType(type); v.setSingleLine(true);
        content.addView(v, new LinearLayout.LayoutParams(-1,dp(60))); return v;
    }
    private void button(String title, Runnable action) {
        Button b = new Button(this); b.setText(title); b.setAllCaps(false); b.setTextSize(18); b.setMinHeight(dp(58));
        content.addView(b, new LinearLayout.LayoutParams(-1,-2)); b.setOnClickListener(v -> { if (!busy) action.run(); });
    }
    private void message(String value) { if (status != null) status.setText(value); }
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
        message("Ingresá como operador. La voz funciona en el teléfono; guardar requiere conexión.");
        EditText host = input("https://servidor", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        host.setText(getPreferences(0).getString("server", ""));
        EditText name = input("Usuario", InputType.TYPE_CLASS_TEXT);
        EditText password = input("Contraseña", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        button("Ingresar", () -> {
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
        button("Probar voz sin guardar datos", this::demo);
        text("Versión 0.4.0 · Solo verás cargas habilitadas y tus canchas asignadas.",14);
    }
    private void demo() {
        demo = true; user = obj("id",0,"username","Demostración"); load = obj("id",0,"reparto","DEMO");
        products = new JSONArray().put(obj("sku","DEMO-1","descripcion","Agua mineral de un litro","bultos",2,"unidades",3))
            .put(obj("sku","DEMO-2","descripcion","Gaseosa de dos litros","bultos",4,"unidades",0));
        court = obj("numero",1,"productos",products); check = obj("id","demo","answers",new JSONObject(),"timer_started_at","demo"); index=0;
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
        text("Canchas asignadas: " + assigned,16);
        Spinner options = new Spinner(this); options.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"Todos","En curso","Sin iniciar","Pausados","Finalizados"}));
        content.addView(options); options.setSelection(Arrays.asList("Todos","En curso","Sin iniciar","Pausados","Finalizados").indexOf(filter));
        button("Aplicar filtro / actualizar", () -> { filter=options.getSelectedItem().toString(); listLoads(); });
        button("Cerrar sesión", this::login);
        task(() -> obj("permissions", json("GET","/load-control/my-courts",null), "trucks", new JSONArray(api.request("GET","/load-control/trucks",null))), response -> {
            assigned.clear(); JSONArray permissions=response.getJSONObject("permissions").getJSONArray("courts");
            for(int i=0;i<permissions.length();i++) assigned.add(permissions.getInt(i));
            JSONArray trucks=response.getJSONArray("trucks");
            int found=0;
            for(int t=0;t<trucks.length();t++) { JSONObject truck=trucks.getJSONObject(t); JSONArray loads=truck.getJSONArray("loads");
                for(int l=0;l<loads.length();l++) { JSONObject item=loads.getJSONObject(l); JSONArray courts=item.getJSONArray("canchas"); boolean show=false;
                    for(int c=0;c<courts.length();c++) if(matches(courts.getJSONObject(c))) show=true;
                    if(show) { found++; button("Camión " + truck.optString("truck") + " · Reparto " + item.optString("reparto"), () -> openLoad(item.optInt("id"))); }
                }
            }
            message(found == 0 ? "Sin cargas para tus canchas y este filtro. El supervisor debe habilitar las cargas desde la web." : "Elegí una carga. Filtro: " + filter);
        });
    }
    private void openLoad(int id) {
        task(() -> json("GET","/load-control/loads/"+id,null), result -> {
            currentScreen = "courts"; check = null; court = null;
            load=result; screen("Reparto " + load.optString("reparto")); button("Volver a cargas",this::listLoads);
            JSONArray courts=load.getJSONArray("canchas"); int count=0;
            for(int i=0;i<courts.length();i++) { JSONObject c=courts.getJSONObject(i); if(!matches(c)) continue; count++;
                String state=processState(c); text("Cancha " + c.optInt("numero") + " · " + state,22);
                if(!state.equals("Finalizados")) button("Iniciar / retomar cancha " + c.optInt("numero"), () -> startCourt(c));
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
        text("Reparto " + load.optString("reparto") + " · " + user.optString("username"),16);
        text("Producto " + (index+1) + "/" + products.length() + " · " + check.optJSONObject("answers").length() + " registrados",16);
        text(p.optString("descripcion"),26); text("SKU " + p.optString("sku"),16);
        if(stage() == 4) text(p.optInt("pallets") + " PALLETS COMPLETOS", 28);
        text(p.optInt("bultos") + " BULTOS  +  " + p.optInt("unidades") + " UNIDADES",28);
        if(check.optJSONObject("answers").has(p.optString("sku"))) text("Este producto ya tiene una respuesta guardada.",16);
        button(voice ? "Detener voz" : "Activar voz", () -> { if(voice) { voice=false; stopAudio(); product(); } else enableVoice(); });
        button("Escuchar / repetir producto", () -> speak(prompt()));
        boolean paused=check.isNull("timer_started_at");
        if(paused) { message("Proceso pausado. Reanudalo antes de registrar."); button("Reanudar picking", () -> startCourt(court)); }
        else { button("Correcto · guardar y seguir", () -> answer(obj("result","ok"))); button("Registrar faltante",this::shortage); }
        if(index>0) button("Anterior", () -> { index--; product(); });
        if(index<products.length()-1) button("Siguiente sin confirmar", () -> { index++; product(); });
        button("Pausar y volver a canchas",this::pauseAndLeave);
        button("Finalizar picking", () -> { stopAudio(); new AlertDialog.Builder(this).setTitle("Finalizar picking")
            .setMessage(check.optJSONObject("answers").length()+" de "+products.length()+" productos registrados. ¿Finalizar?")
            .setNegativeButton("Seguir",(d,w)->product()).setOnCancelListener(d->product()).setPositiveButton("Finalizar",(d,w)->finishPicking()).show(); });
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
        if(demo) { showShortage(); return; }
        task(() -> new JSONArray(api.request("GET","/load-control/operators",null)), rows -> {operators=rows;showShortage();});
    }
    private void showShortage() {
        currentScreen = "shortage";
        JSONObject p=products.optJSONObject(index); screen("Faltante · " + p.optString("sku")); text(p.optString("descripcion"),24);
        text("Planilla: "+p.optInt("bultos")+" bultos + "+p.optInt("unidades")+" unidades",18);
        EditText b=input("Bultos físicos",InputType.TYPE_CLASS_NUMBER), u=input("Unidades físicas",InputType.TYPE_CLASS_NUMBER);
        text("Proceso responsable: Picking",16); EditText note=input("Observación (opcional)",InputType.TYPE_CLASS_TEXT);
        button("Guardar faltante y continuar", () -> {
            try {
                int physicalB=Integer.parseInt(b.getText().toString()),physicalU=Integer.parseInt(u.getText().toString());
                if(physicalB<0 || physicalU<0 || physicalB>p.optInt("bultos") || physicalU>p.optInt("unidades") || (physicalB==p.optInt("bultos") && physicalU==p.optInt("unidades"))) throw new Exception("Las cantidades deben ser menores a la planilla y no negativas.");
                int responsible=demo?0:user.getInt("id");
                answer(obj("result","shortage","physical_b",physicalB,"physical_u",physicalU,"responsible_user_id",responsible,"origin","picking","note",note.getText().toString()));
            } catch(Exception e) {error(e);}
        });
        button("Cancelar",this::product);
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
            modelLoading=false;if(isDestroyed()){ready.close();return;}model=ready;if(visible && check!=null){voice=true;product();}
        },error->{modelLoading=false;if(!isDestroyed())error(error);});}
        else {voice=true;product();}
    }
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] grants) {
        super.onRequestPermissionsResult(request,permissions,grants);
        if(request==10 && grants.length>0 && grants[0]==PackageManager.PERMISSION_GRANTED) enableVoice();
        else message("Sin permiso de micrófono. Podés continuar con los botones.");
    }
    private void speak(String value) {
        stopAudio();
        if(!ttsReady){message("No hay voz española disponible. Revisá Texto a voz en Android.");return;}
        int generation=++speechVersion;
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener(){
            @Override public void onStart(String id){}
            @Override public void onDone(String id){handler.postDelayed(()->{if(generation==speechVersion && voice && visible && !busy) startMic();},400);}
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
                @Override public void onResult(String value){if(generation!=speechVersion || !voice || busy || !visible)return;try{command(new JSONObject(value).optString("text"));}catch(Exception e){error(e);}}
                @Override public void onFinalResult(String value){}
                @Override public void onError(Exception e){if(generation==speechVersion){voice=false;stopMic();error(e);}}
                @Override public void onTimeout(){if(generation==speechVersion){voice=false;stopMic();message("Escucha detenida. Tocá Activar voz.");}}
            }); message("Escuchando. Decí correcto, faltante o repetir.");
        } catch(Exception e){voice=false;stopMic();error(e);}
    }
    private void command(String text) {
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
    @Override protected void onResume(){super.onResume();visible=true;}
    @Override protected void onPause(){visible=false;voice=false;stopAudio();super.onPause();}
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
