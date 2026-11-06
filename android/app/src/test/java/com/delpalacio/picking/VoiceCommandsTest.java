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
        assertEquals("start", VoiceCommands.parse("iniciar"));
        assertEquals("start", VoiceCommands.parse("iniciar cancha"));
        assertEquals("continue", VoiceCommands.parse("continuar"));
        assertEquals("refresh", VoiceCommands.parse("actualizar tareas"));
        assertEquals("unknown", VoiceCommands.parse("no es correcto"));
        assertEquals("unknown", VoiceCommands.parse("decí correcto o faltante"));
        assertEquals("unknown", VoiceCommands.parse(""));
    }
}
