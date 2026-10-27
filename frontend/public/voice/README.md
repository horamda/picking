# Modelo de voz (Vosk, español)

La pantalla de control usa el reconocimiento de voz del propio equipo. El modelo no va en Git (pesa decenas de MB).

1. Descargar un modelo en español de https://alphacephei.com/vosk/models (por ejemplo `vosk-model-small-es-0.42`).
2. Empaquetarlo como `model.tar.gz` con la carpeta `model/` adentro (estructura que pide vosk-browser).
3. Copiarlo en `frontend/public/voice/model.tar.gz` antes de compilar, o publicarlo en otra URL y definir `VITE_VOICE_MODEL_URL`.

Sin el modelo, la pantalla funciona igual con los botones; solo se desactiva la voz.

## Verificación local (24/10/2026)

- Modelo revisado: `vosk-model-small-es-0.42`, descargado del sitio oficial indicado arriba.
- Se leyó la tabla de símbolos completa de `graph/Gr.fst` (100.006 entradas). Todas las palabras de `VOICE_VOCABULARY`, incluida `y`, y `[unk]` existen en ella. Esto verifica pertenencia al vocabulario, no precisión de reconocimiento.
- En el paquete instalado `vosk-browser@0.0.8` se verificaron `KaldiRecognizer(sampleRate, grammar)`, `acceptWaveformFloat(Float32Array, sampleRate)` y los eventos `result`/`partialresult`, con `result.text`/`result.partial`.
- Las cantidades compuestas de 31 a 49 tienen pruebas del parser. Sin etiquetas, “treinta y dos” significa 32 bultos; para 30 bultos y 2 unidades, decir “treinta bultos dos unidades”.

## Prueba pendiente en Android / Chrome

Usar una carga de prueba en un entorno aislado, servido por HTTPS, con el modelo disponible. Registrar teléfono, versión de Android/Chrome, tiempo de carga inicial y errores de consola.

1. Activar voz, conceder micrófono y comprobar que aparecen transcripciones parciales y finales. Repetir con el modelo ya descargado.
2. Usar “Escuchar producto” para comprobar el parlante. Al activar voz se informa el permiso de micrófono y la carga del modelo. Durante la lectura, permanecer en silencio: no debe guardarse ninguna respuesta ni cambiar de producto. El motor envía silencio al reconocedor durante la síntesis y descarta resultados mientras habla; esta protección todavía debe validarse en el dispositivo. Si hay confirmaciones involuntarias, detener la prueba por voz.
3. Probar “correcto”, “faltante”, “repetir”, “siguiente” y “anterior”; “error corregido” debe operar solo en controles 1 y 2.
4. En faltante, dictar “dos bultos tres unidades”, “treinta y dos bultos” y “cuarenta y una unidades”. Verificar los campos antes de guardar; responsable y proceso siguen siendo obligatorios.
5. Parar voz, pausar y salir de la pantalla; comprobar el indicador de micrófono y que no lleguen comandos posteriores. Probar también activación repetida y permiso denegado.
6. Repetir con ruido habitual del depósito y anotar errores y demora al responder. La revisión local no valida estos casos.

Se mantiene ScriptProcessor hasta medir su comportamiento en el dispositivo. Si hay cortes o retrasos atribuibles al procesamiento de audio en el hilo principal, evaluar un AudioWorklet con transferencia de audio al reconocedor. Un fallo de permiso o de carga del modelo no demuestra un problema de ScriptProcessor.
