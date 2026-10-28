package com.delpalacio.picking;

import android.app.*;
import android.content.Intent;
import android.os.Bundle;
import android.view.*;
import android.widget.*;
import org.vosk.*;
import org.vosk.android.StorageService;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

/** Runs only a synthetic demo; never connects to the operational API. */
public class SmokeRunner extends Instrumentation {
    private Activity renderingActivity;
    private void screenshot(String name) throws Exception {
        waitForIdleSync();Thread.sleep(250);
        AtomicReference<android.graphics.Bitmap> rendered=new AtomicReference<>();
        runOnMainSync(()->{View view=renderingActivity.getWindow().getDecorView();android.graphics.Bitmap b=android.graphics.Bitmap.createBitmap(view.getWidth(),view.getHeight(),android.graphics.Bitmap.Config.ARGB_8888);view.draw(new android.graphics.Canvas(b));rendered.set(b);});
        android.graphics.Bitmap bitmap=rendered.get();
        try(java.io.FileOutputStream out=new java.io.FileOutputStream(new java.io.File(getTargetContext().getExternalFilesDir(null),name+".png"))){bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out);}finally{bitmap.recycle();}
    }
    private void command(Activity activity,String words){
        try{java.lang.reflect.Method method=MainActivity.class.getDeclaredMethod("command",String.class);method.setAccessible(true);method.invoke(activity,words);}catch(Exception e){throw new AssertionError(e);}
    }
    private EditText field(View view,String description){
        if(view instanceof EditText && description.equals(String.valueOf(view.getContentDescription())))return (EditText)view;
        if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++){EditText v=field(((ViewGroup)view).getChildAt(i),description);if(v!=null)return v;}return null;
    }
    @Override public void onCreate(Bundle arguments) { super.onCreate(arguments); start(); }
    private Button button(View view, String label) {
        if (view instanceof Button && ((Button)view).getText().toString().equals(label)) return (Button)view;
        if (view instanceof ViewGroup) for (int i=0;i<((ViewGroup)view).getChildCount();i++) {
            Button found=button(((ViewGroup)view).getChildAt(i),label); if(found!=null)return found;
        }
        return null;
    }
    @Override public void onStart() {
        Bundle result=new Bundle(); Activity activity=null;
        try {
            activity=startActivitySync(new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            Activity target=activity;
            renderingActivity=activity;
            screenshot("login");
            runOnMainSync(()->{
                button(target.getWindow().getDecorView(),"Probar voz sin guardar datos").performClick();
                Button confirm=button(target.getWindow().getDecorView(),"Correcto →");
                if(confirm==null)throw new AssertionError("No abrió el producto de demostración");
            });
            screenshot("picking");
            runOnMainSync(()->{
                Button confirm=button(target.getWindow().getDecorView(),"Correcto →");
                confirm.performClick();
                if(!button(target.getWindow().getDecorView(),"← Anterior").isEnabled())throw new AssertionError("No avanzó al segundo producto");
                button(target.getWindow().getDecorView(),"Faltante real").performClick();
                command(target,"un bulto");
                if(!field(target.getWindow().getDecorView(),"Bultos físicos").getText().toString().equals("1"))throw new AssertionError("No completó cantidades por voz");
                command(target,"correcto");
                if(button(target.getWindow().getDecorView(),"Registrar faltante")==null)throw new AssertionError("La voz confirmó un faltante sin toque");
                command(target,"un bulto");
            });
            screenshot("faltante");
            runOnMainSync(()->{
                ((MainActivity)target).onBackPressed();
                if(button(target.getWindow().getDecorView(),"Correcto →")==null)throw new AssertionError("Atrás no volvió del faltante al producto");
                ((MainActivity)target).onBackPressed();
                if(button(target.getWindow().getDecorView(),"Probar voz sin guardar datos")==null)throw new AssertionError("Atrás no volvió de la demostración al inicio");
            });
            CountDownLatch latch=new CountDownLatch(1);AtomicReference<Throwable> failure=new AtomicReference<>();
            StorageService.unpack(getTargetContext(),"model-es","smoke-model",model->{
                try(Recognizer recognizer=new Recognizer(model,16000,VoiceCommands.grammar())) {
                    recognizer.acceptWaveForm(new byte[32000],32000);
                    if(!recognizer.getFinalResult().contains("text"))throw new AssertionError("Sin resultado de Vosk");
                } catch(Throwable error){failure.set(error);} finally {model.close();latch.countDown();}
            },error->{failure.set(error);latch.countDown();});
            if(!latch.await(120,TimeUnit.SECONDS))throw new AssertionError("Tiempo agotado al cargar modelo");
            if(failure.get()!=null)throw new AssertionError(failure.get());
            result.putString("stream","OK: demo, avance por producto y modelo Vosk español cargado.\n");finish(Activity.RESULT_OK,result);
        } catch(Throwable error){result.putString("stream","FAIL: "+error+"\n");finish(Activity.RESULT_CANCELED,result);}
        finally {if(activity!=null){Activity target=activity;runOnMainSync(target::finish);}}
    }
}
