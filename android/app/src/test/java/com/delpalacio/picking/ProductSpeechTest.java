package com.delpalacio.picking;
import org.junit.Test;
import static org.junit.Assert.*;
public class ProductSpeechTest {
    @Test public void palletDestinationsSpeakExactAmounts(){
        String first=ProductSpeech.destination("M001",2,0,true);
        assertTrue(first.contains("M001"));assertTrue(first.contains("2 bultos"));
        assertTrue(first.contains("Compartido"));assertFalse(first.contains("unidades"));
        String second=ProductSpeech.destination("M002",0,3,false);
        assertTrue(second.contains("3 unidades"));assertFalse(second.contains("bultos"));
        assertFalse(second.contains("Compartido"));
        assertEquals("",ProductSpeech.destination("M003",0,0,false));
    }
    @Test public void speaksOnlyPositiveQuantities(){
        String units=ProductSpeech.prompt("Agua",0,4,0,0,0,3);
        assertTrue(units.contains("Agarrá 4 unidades de Agua"));assertFalse(units.contains("bultos"));
        String cases=ProductSpeech.prompt("Agua",2,0,0,0,0,3);
        assertTrue(cases.contains("Agarrá 2 bultos de Agua"));assertFalse(cases.contains("unidades"));
        assertTrue(ProductSpeech.prompt("Agua",1,1,0,0,0,3).contains("un bulto y una unidad"));
        assertTrue(ProductSpeech.prompt("Agua",0,1,0,0,0,3).contains("Agarrá una unidad"));
    }
    @Test public void emptyAndPalletInstructions(){
        String empty=ProductSpeech.prompt("Agua",0,0,0,0,0,3);
        assertTrue(empty.contains("supervisor"));assertFalse(empty.contains("Agarrá"));assertFalse(empty.contains("decí correcto"));
        assertTrue(ProductSpeech.prompt("Agua",50,0,1,4,0,3).contains("Prepará un pallet completo"));
    }
}
