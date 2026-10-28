# Descripciones para voice picking

Conversor determinístico, sin servicios externos ni dependencias de ejecución fuera de la librería estándar. La función pura no escribe datos. La integración de Flask completa `descripcion_voz` en altas e importaciones solo cuando está vacía; conserva todos los textos existentes, incluidos los generados anteriormente. No requiere cambios de esquema.

En Importaciones → Descripciones de voz, **Generar voz para campos vacíos** propone textos para artículos activos ya cargados. La vista previa no guarda: usa el circuito CSV firmado existente para confirmar, auditar y rechazar cambios concurrentes. Los textos vacíos o mayores de 255 caracteres quedan pendientes sin truncarse. Si se borra una voz manualmente, la siguiente importación puede volver a completar ese campo vacío. Android y web reciben el valor guardado a través de la API existente.

```python
from voz.conversor import descripcion_para_voz

descripcion_para_voz("NEGRA MODELO OW X24 0,355L")
# 'NEGRA MODELO pack de 24 de 355 cc'
```

Las reglas se aplican en el orden solicitado: normalización a mayúsculas, equivalencias, volúmenes, packs, abreviaturas y limpieza. Las palabras desconocidas permanecen en mayúsculas; no se expanden por semejanza. `IMPO`, por ejemplo, permanece como está.

Editar `ABREVIATURAS` al principio de `conversor.py` permite incorporar equivalencias aprobadas. Las claves se escriben en mayúsculas y son literales, no expresiones regulares. Se reemplazan una sola vez para no encadenar significados.

Decisiones explícitas de las reglas:

- Se elimina el guion suelto del ejemplo STELLA. Los guiones dentro de palabras desconocidas se conservan.
- `_` permite reconocer `SG_` sin quitar el guion bajo. Letras y números pegados impiden expandir abreviaturas.
- Se agrega `de` después de `pack de N` y `packs de N` tanto para cc como para litros.
- La conversión general a litros prevalece también para PET y retornables de 1000 cc o más.
- No se infiere una unidad para `2,0` ni para códigos como `A-330`. Un número aislado de 200 a 999, o 1000, se interpreta como cc; otros números sin unidad se conservan.
- Los decimales se convierten mediante cadenas, sin redondeos de punto flotante.
- `RET` separado no convierte el número anterior: `QUILMES 1890 RET` conserva la marca. La regla de medida usa `1000RET` unido.
- Los separadores en cc (`2.000CC`) no tienen interpretación definida: se conserva `2.000 cc`, sin asumir decimal ni miles. `ML` no se expande porque no figura entre las equivalencias solicitadas; un número con esa unidad tampoco recibe un `cc` adicional.

## Pruebas y comparación

Desde la raíz del repositorio:

```powershell
python -m pytest tests/test_conversor.py -q
python scripts/validar_csv.py "C:\Users\horac\Downloads\descripciones-voz-listo.csv"
```

El script acepta un CSV con separador `;`, UTF-8 con o sin BOM, y columnas `Descripcion original` y `Descripcion para voz`. `Codigo` es opcional. Sin argumento, busca `descripciones-voz.csv` en el directorio actual. Compara cada descripción original de ese mismo archivo contra su salida esperada, sin cruzar filas por posición con otro archivo.

Imprime los totales y las primeras 20 diferencias con fila, código, original, esperado y obtenido. La comparación es exacta: mayúsculas, espacios y signos cuentan. Las referencias vacías se informan y no se ignoran. No reescribe el CSV. Salidas del proceso: `0` si todo coincide, `1` si hay diferencias, `2` si el archivo es inválido o no puede abrirse.

## Ejemplo de integración futura con Flask

Este ejemplo **no está registrado en la app**. La aplicación real deberá conservar su autenticación y permisos cuando se decida incorporarlo. La conversión propone texto; no debe sobrescribir descripciones de voz editadas por una persona.

```python
from flask import Blueprint, jsonify, request
from voz.conversor import descripcion_para_voz

voz_bp = Blueprint("voz", __name__)

@voz_bp.post("/voz/convertir")
def convertir():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict) or not isinstance(datos.get("descripcion"), str):
        return jsonify(error="Se requiere descripcion como texto."), 400
    return jsonify(voz=descripcion_para_voz(datos["descripcion"]))

# Cuando se apruebe la integración: app.register_blueprint(voz_bp)
```

Entrada: `{"descripcion": "BUD CAN 2X12 0,355L IMPO"}`.
Salida: `{"voz": "Budweiser lata 2 packs de 12 de 355 cc IMPO"}`.
