package com.delpalacio.picking;
import org.junit.Test;
import static org.junit.Assert.*;
public class ShortageAmountsTest {
    @Test public void unitsOnlyShortage(){
        assertTrue(ShortageAmounts.error("0","6",0,6).contains("Correcto"));
        assertEquals("",ShortageAmounts.error("0","0",0,6));
        assertEquals("Faltan: 0 bultos + 4 unidades.",ShortageAmounts.summary("0","2",0,6));
    }
    @Test public void invalidInputsAreExplained(){
        for(String value:new String[]{"","-1","7","1.5","999999999999"})assertFalse(ShortageAmounts.error("0",value,0,6).isEmpty());
        assertEquals("",ShortageAmounts.error("1","0",2,3));
    }
}
