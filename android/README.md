# Del Palacio · Android nativo

Primera versión de prueba en Java, con vistas nativas de Android, TextToSpeech y Vosk. No utiliza WebView. Mantiene Flask como backend. Android 8 o posterior; acceso HTTPS por Wi-Fi o datos móviles.

## Probar sin tocar datos

Instalar `app/build/outputs/apk/debug/app-debug.apk` y elegir **Probar voz sin guardar datos**. El modelo español está incluido en el APK y se prepara en el primer uso. Activar voz, conceder micrófono y verificar volumen multimedia y voz española instalada en Android.

La app lee el producto y las cantidades; después abre el micrófono. Reconoce `correcto`, `confirmo`, `bien`, `faltante`, `falta`, `repetir`, `repite`, `siguiente` y `anterior`. Frases ambiguas como “no es correcto” no confirman productos. Dentro de faltantes, la voz completa cantidades explícitas (por ejemplo, `un bulto` o `dos bultos tres unidades`, de cero a 999). No modifica campos omitidos y rechaza cantidades superiores a la planilla. Guardar siempre requiere tocar **Registrar faltante**; decir `correcto` en ese formulario nunca confirma.

El audio se reconoce localmente. Guardar respuestas reales necesita red: no existe cola offline ni reintento automático de escrituras. Tras un error, revisar el estado antes de reintentar. La lectura se detiene antes de escuchar para evitar que la app se confirme a sí misma.

## Operación conectada (0.7)

La cola de camiones se configura en **Supervisión → Planificar cargas**. La app muestra el resumen del camión actual y el trabajo de las canchas asignadas, conservando los repartos separados. Al finalizar esas tareas aparece el siguiente camión, sin esperar los controles ni otros operarios. El detalle de pallets permite consultar la distribución aprobada antes de empezar. Ver [flujo de selección y aprobación](../docs/cola-armado.md).

Picking y faltantes usan tarjetas, cantidades grandes, avance y tiempo activo. La pantalla inicial muestra usuario, canchas y filtro. Atrás vuelve de faltantes al producto, del producto a sus canchas (pausando antes) y de canchas a cargas. El teclado y el audio deben verificarse también en el equipo físico del depósito.

El login acepta `operador` y `palletizador`. La API devuelve solo canchas asignadas y cargas aprobadas. Picking recibe remanentes; pallets completos recibe su cantidad de pallets y bultos. La respuesta del servidor al iniciar determina las cantidades que se leen. Las asignaciones se actualizan al refrescar cargas y se vuelven a verificar al escribir.

El supervisor aprueba las cargas desde la web; administración configura capacidad y altas. La app conserva ónicamente la URL HTTPS del servidor. Contraseña y token permanecen en memoria.

Cerrar Android apaga el micrófono pero no pausa el cronómetro del servidor: usar **Pausar y volver**. El trabajo real requiere conexión. La respuesta confirmada por el servidor es la que cuenta; no existe cola offline. La prueba acústica con teléfono y ruido de depósito continúa pendiente.

## Guía del plan aprobado (0.8)

Al activar voz, Android lee el resumen del camión y el trabajo asignado. Cada producto indica reparto, cancha y cantidades por pallet destino, usando los identificadores del plan aprobado. Si un producto ocupa varios pallets, los enumera con sus cantidades; avisa cuando el pallet se comparte entre canchas. El resumen también tiene un botón para escucharlo antes de comenzar. Al finalizar una cancha consulta la cola y anuncia el camión vigente. Seleccionar cancha, finalizar y confirmar faltantes mantienen sus botones.

Identificar físicamente los pallets con los códigos del plan (M001, M002, etc.) dentro de cada camión. La app no puede verificar que la etiqueta física corresponda. No se inventan destinos cuando falta el plan: se indica consultar al supervisor. La guía requiere instalar el APK 0.8; actualizar la web no actualiza Android.

La compilación, pruebas y lint se verifican localmente. La escucha, pronunciación de códigos y operación con ruido requieren una prueba en el teléfono del depósito.

## Compilar

Android 0.10 simplifica el inicio: camión, avance y Continuar picking. Prioriza tareas en curso, después pausadas y luego sin iniciar, conservando el orden del servidor en cada grupo. Continuar abre el detalle sin iniciar un cronómetro automáticamente. Elegir tarea despliega filtros y repartos; cada reparto despliega sus canchas. Resumen, pallets y sesión permanecen plegados. Al activar voz se anuncia reparto y cancha; las siguientes lecturas se concentran en producto, cantidades y destinos. Verificación visual y acústica en teléfono pendiente.

Android 0.9 presenta el camión y su resumen, seguido de sus cargas/repartos y las canchas asignadas dentro de cada uno. Cada cancha muestra estado y cantidad de productos; cada reparto muestra el avance de canchas terminadas. El filtro solo oculta tareas de la vista: no cambia la cola ni los totales del camión. Tocar una cancha abre su detalle; iniciar o retomar sigue siendo una acción explícita. Mantiene la guía por voz de 0.8.

Requisitos: JDK 17, Android SDK plataforma 35 y conexión para descargar dependencias la primera vez.

1. Descargar el ZIP oficial `https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip`.
2. Ejecutar `python prepare_model.py RUTA_AL_ZIP` desde esta carpeta. El script valida SHA-256. Modelo: Apache-2.0, publicado por Alpha Cephei; conservar el README incluido.
3. Definir `ANDROID_HOME` o `sdk.dir` en `local.properties` (excluido de Git). Copiar la configuración Firebase de `com.delpalacio.picking` en `app/google-services.json` (excluida de Git).
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

## Escucha continua (0.6)

Activar voz inicia un servicio de micrófono con notificación y botón **Parar voz**. No hay límite de silencio. La pantalla permanece encendida mientras la voz está activa; si el operador bloquea el teléfono o cambia de aplicación, el servicio continúa escuchando y la app puede registrar sus comandos. Durante la lectura y las peticiones al servidor se suspende la captura para evitar confirmaciones involuntarias.

Los cortes transitorios de captura se recuperan con hasta cinco reintentos (1, 2, 4, 8 y 15 segundos). Una captura estable durante 30 segundos restablece ese presupuesto. El detector de captura bloqueada observa callbacks de audio, no si el operador está hablando. Si no puede recuperarse o falla una operación de red, la interfaz informa la detención; nunca reenvía una escritura automáticamente.

Parar voz, pausar, finalizar, salir o quitar la app de recientes libera el micrófono y el bloqueo de CPU. Android no la reinicia después de un cierre forzado. La activación inicial debe hacerse con la app visible y permiso de micrófono; Android 13+ también solicita notificaciones. Si se deniegan, el control sigue disponible dentro de la app. El funcionamiento con llamadas, ahorro de batería del fabricante y pantalla bloqueada debe verificarse en el teléfono del depósito.
