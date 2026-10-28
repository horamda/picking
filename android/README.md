# Del Palacio · Android nativo

Primera versión de prueba en Java, con vistas nativas de Android, TextToSpeech y Vosk. No utiliza WebView. Mantiene Flask como backend. Android 8 o posterior; acceso HTTPS por Wi-Fi o datos móviles.

## Probar sin tocar datos

Instalar `app/build/outputs/apk/debug/app-debug.apk` y elegir **Probar voz sin guardar datos**. El modelo español está incluido en el APK y se prepara en el primer uso. Activar voz, conceder micrófono y verificar volumen multimedia y voz española instalada en Android.

La app lee el producto y las cantidades; después abre el micrófono. Reconoce `correcto`, `confirmo`, `bien`, `faltante`, `falta`, `repetir`, `repite`, `siguiente` y `anterior`. Frases ambiguas como “no es correcto” no confirman productos. El faltante se completa y confirma manualmente; el dictado de cantidades todavía no está implementado en Android.

El audio se reconoce localmente. Guardar respuestas reales necesita red: no existe cola offline ni reintento automático de escrituras. Tras un error, revisar el estado antes de reintentar. La lectura se detiene antes de escuchar para evitar que la app se confirme a sí misma.

## Operación conectada (0.3)

El login acepta `operador` y `palletizador`. La API devuelve solo canchas asignadas y cargas aprobadas. Picking recibe remanentes; pallets completos recibe su cantidad de pallets y bultos. La respuesta del servidor al iniciar determina las cantidades que se leen. Las asignaciones se actualizan al refrescar cargas y se vuelven a verificar al escribir.

El supervisor aprueba las cargas desde la web; administración configura capacidad y altas. La app conserva ónicamente la URL HTTPS del servidor. Contraseña y token permanecen en memoria.

Cerrar Android apaga el micrófono pero no pausa el cronómetro del servidor: usar **Pausar y volver**. El trabajo real requiere conexión. La respuesta confirmada por el servidor es la que cuenta; no existe cola offline. La prueba acústica con teléfono y ruido de depósito continúa pendiente.

## Compilar

Requisitos: JDK 17, Android SDK plataforma 35 y conexión para descargar dependencias la primera vez.

1. Descargar el ZIP oficial `https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip`.
2. Ejecutar `python prepare_model.py RUTA_AL_ZIP` desde esta carpeta. El script valida SHA-256. Modelo: Apache-2.0, publicado por Alpha Cephei; conservar el README incluido.
3. Definir `ANDROID_HOME` o `sdk.dir` en `local.properties` (excluido de Git).
4. Ejecutar `gradlew.bat assembleDebug testDebugUnitTest lintDebug` en Windows, o `./gradlew` en Linux/macOS.

El APK debug es para pruebas, no para distribución definitiva. Las claves de publicación no se guardan en Git. No hay despliegue ni cambio en producción.

## Validación en teléfono pendiente

- Instalación, voz española y permiso concedido/denegado.
- Lectura completa sin confirmaciones involuntarias; comandos con ruido y auriculares.
- Parar voz, llamadas, bloqueo de pantalla y retorno a la app.
- Pérdida de red durante confirmación, recuperación y ausencia de duplicados.
- Restricciones de cancha verificadas también en el servidor antes de habilitar datos reales.
- Compatibilidad de bibliotecas nativas en el modelo de teléfono utilizado.

La versión 0.3 usa `descripcion_voz` del servidor cuando existe, manteniendo la descripción original en pantalla.
