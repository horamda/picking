package com.delpalacio.picking;
import org.junit.Test;
import static org.junit.Assert.*;
public class VoiceCommandsTest {
    @Test public void acceptsOnlyExplicitCommands() {
        assertEquals("ok", VoiceCommands.parse("Correcto."));
        assertEquals("shortage", VoiceCommands.parse("faltante"));
        assertEquals("repeat", VoiceCommands.parse("repetir"));
        assertEquals("next", VoiceCommands.parse("siguiente"));
        assertEquals("prev", VoiceCommands.parse("anterior"));
        assertEquals("unknown", VoiceCommands.parse("no es correcto"));
        assertEquals("unknown", VoiceCommands.parse("decí correcto o faltante"));
        assertEquals("unknown", VoiceCommands.parse(""));
    }
}
