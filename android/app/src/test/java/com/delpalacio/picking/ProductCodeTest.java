package com.delpalacio.picking;
import org.junit.Test;
import static org.junit.Assert.*;
public class ProductCodeTest {
    @Test public void requiresEveryDigit(){
        assertEquals("040512",ProductCode.parse("cero cuatro cero cinco uno dos"));
        assertEquals("40512",ProductCode.parse("40512"));
        assertEquals("",ProductCode.parse("correcto 40512"));
        assertEquals("",ProductCode.parse("cuarenta mil cinco"));
        assertEquals("",ProductCode.parse(""));
    }
}
