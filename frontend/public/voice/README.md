# Modelo de voz (Vosk, español)

La pantalla de control usa el reconocimiento de voz del propio equipo. El modelo no va en Git (pesa decenas de MB).

1. Descargar un modelo en español de https://alphacephei.com/vosk/models (por ejemplo `vosk-model-small-es-0.42`).
2. Empaquetarlo como `model.tar.gz` con la carpeta `model/` adentro (estructura que pide vosk-browser).
3. Copiarlo en `frontend/public/voice/model.tar.gz` antes de compilar, o publicarlo en otra URL y definir `VITE_VOICE_MODEL_URL`.

Sin el modelo, la pantalla funciona igual con los botones; solo se desactiva la voz.
