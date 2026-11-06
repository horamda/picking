package com.delpalacio.picking;

import java.text.Normalizer;
import java.util.Locale;
import java.util.*;
import org.json.*;

final class VoiceCommands {
    static String parse(String input) {
        return parse(input,null);
    }
    static String parse(String input,JSONObject configured) {
        String text = Normalizer.normalize(input.toLowerCase(Locale.ROOT), Normalizer.Form.NFD)
            .replaceAll("\\p{M}", "").replaceAll("[.,;:!?]", "").trim().replaceAll("\\s+", " ");
        if(configured!=null)for(Iterator<String> keys=configured.keys();keys.hasNext();){String key=keys.next();JSONArray aliases=configured.optJSONArray(key);if(aliases==null)continue;for(int i=0;i<aliases.length();i++)if(text.equals(normalize(aliases.optString(i))))return key;}
        return switch (text) {
            case "correcto", "confirmo", "bien" -> "ok";
            case "faltante", "falta" -> "shortage";
            case "repetir", "repite" -> "repeat";
            case "siguiente" -> "next";
            case "anterior" -> "prev";
            case "continuar", "continuar tarea" -> "continue";
            case "iniciar", "iniciar cancha" -> "start";
            case "finalizar", "finalizar picking" -> "finish";
            case "confirmar", "si confirmar" -> "confirm";
            case "cancelar", "no cancelar" -> "cancel";
            case "actualizar", "actualizar tareas" -> "refresh";
            case "registrar faltante", "guardar faltante" -> "register";
            default -> "unknown";
        };
    }
    private static String normalize(String value){return Normalizer.normalize(value.toLowerCase(Locale.ROOT),Normalizer.Form.NFD).replaceAll("\\p{M}","").trim().replaceAll("\\s+"," ");}
    static String grammar() {
        return grammar(null);
    }
    static String grammar(JSONObject configured) {
        java.util.Set<String> words=VoiceQuantities.vocabulary();
        if(configured!=null)for(Iterator<String> keys=configured.keys();keys.hasNext();){JSONArray aliases=configured.optJSONArray(keys.next());if(aliases!=null)for(int i=0;i<aliases.length();i++)words.add(normalize(aliases.optString(i)));}
        else words.addAll(java.util.Arrays.asList("correcto","ok","confirmo","bien","faltante","falta","repetir","repite","siguiente","anterior","continuar","iniciar","finalizar","confirmar","cancelar","actualizar","registrar faltante"));
        words.add("[unk]");
        return "[\""+String.join("\",\"",words)+"\"]";
    }
}
