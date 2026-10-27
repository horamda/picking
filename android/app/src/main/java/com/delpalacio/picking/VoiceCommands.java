package com.delpalacio.picking;

import java.text.Normalizer;
import java.util.Locale;

final class VoiceCommands {
    static String parse(String input) {
        String text = Normalizer.normalize(input.toLowerCase(Locale.ROOT), Normalizer.Form.NFD)
            .replaceAll("\\p{M}", "").replaceAll("[.,;:!?]", "").trim().replaceAll("\\s+", " ");
        return switch (text) {
            case "correcto", "confirmo", "bien" -> "ok";
            case "faltante", "falta" -> "shortage";
            case "repetir", "repite" -> "repeat";
            case "siguiente" -> "next";
            case "anterior" -> "prev";
            default -> "unknown";
        };
    }
    static String grammar() {
        return "[\"correcto\",\"confirmo\",\"bien\",\"faltante\",\"falta\",\"repetir\",\"repite\",\"siguiente\",\"anterior\",\"[unk]\"]";
    }
}
