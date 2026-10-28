package com.delpalacio.picking;
import org.junit.Test;
import static org.junit.Assert.*;
public class VoiceQuantitiesTest {
    @Test public void fillsOnlyExplicitQuantities() {
        assertArrayEquals(new Integer[]{1,null},VoiceQuantities.parse("un bulto"));
        assertArrayEquals(new Integer[]{2,3},VoiceQuantities.parse("dos bultos tres unidades"));
        assertArrayEquals(new Integer[]{244,1},VoiceQuantities.parse("doscientos cuarenta y cuatro bultos una unidad"));
        assertArrayEquals(new Integer[]{21,0},VoiceQuantities.parse("veintiún bultos cero unidades"));
        assertArrayEquals(new Integer[]{null,0},VoiceQuantities.parse("0 unidades"));
    }
    @Test public void rejectsAmbiguousOrConfirmingPhrases() {
        for(String phrase:new String[]{"correcto","no dos bultos","dos bultos guardar","dos bultos tres bultos","menos uno bulto","1.5 bultos","mil bultos","dos unidades y",""})assertNull(phrase,VoiceQuantities.parse(phrase));
    }
}
