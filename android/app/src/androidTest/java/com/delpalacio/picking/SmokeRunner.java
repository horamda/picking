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
            runOnMainSync(()->{
                button(target.getWindow().getDecorView(),"Probar voz sin guardar datos").performClick();
                Button confirm=button(target.getWindow().getDecorView(),"Correcto · guardar y seguir");
                if(confirm==null)throw new AssertionError("No abrió el producto de demostración");
                confirm.performClick();
                if(button(target.getWindow().getDecorView(),"Anterior")==null)throw new AssertionError("No avanzó al segundo producto");
                button(target.getWindow().getDecorView(),"Registrar faltante").performClick();
                ((MainActivity)target).onBackPressed();
                if(button(target.getWindow().getDecorView(),"Correcto · guardar y seguir")==null)throw new AssertionError("Atrás no volvió del faltante al producto");
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
