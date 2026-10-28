"""Conversión determinística de descripciones ERP; no modifica datos ni usa red."""

import re


# Agregar aquí equivalencias aprobadas. Las claves son texto literal, no regex.
# Se aplican al final, junto a las abreviaturas generales, sin encadenarlas.
ABREVIATURAS = {
    "CAN": "lata",
    "PET": "botella",
    "RET": "retornable",
    "GDE": "grande",
    "GDC": "grande",
    "VERT": "vertical",
    "SUBCERO": "sub cero",
}

# Un guion bajo separa palabras del ERP (por ejemplo SG_); letras y números no.
_INICIO = r"(?<![^\W_])"
_FIN = r"(?![^\W_])"
_NUMERO = r"\d+(?:[.,]\d+)?"
_PET = {
    "1500": "1,5 litros",
    "2250": "2,25 litros",
    "2000": "2 litros",
    "2500": "2,5 litros",
    "250": "250 cc",
}
_EQUIVALENCIAS = (
    (r"ADM\s+PET", "botellón"),
    (r"S/G|SG", "sin gas"),
    (r"C/G|CG", "con gas"),
    (r"7-UP|7\s+UP|7UP", "Seven Up"),
    (r"PATAGO|PARAG", "Patagonia"),
    (r"BUD", "Budweiser"),
    (r"COOL\s+BLU|COOLBLU", "Cool Blue"),
    (r"LIM-LIM|LIM\s+LIM", "lima limón"),
    (r"PDT|PASO\s+DLT", "Paso de los Toros"),
    (r"DLT", "de los Toros"),
    (r"NAR|NARA", "naranja"),
    (r"DUR", "durazno"),
    (r"AWAF", "Awafrut"),
    (r"MANZ", "manzana"),
    (r"FRU\s+TRO", "frutas tropicales"),
    (r"TROP", "tropicales"),
    (r"STA", "Stella"),
    (r"NPV", "Nestlé Pureza Vital"),
)


def _sustituir(texto, patron, reemplazo):
    return re.sub(_INICIO + "(?:" + patron + ")" + _FIN, reemplazo, texto)


def _decimal(numero, desplazar=0):
    """Mover la coma con cadenas, sin redondeos de punto flotante."""
    entero, _, fraccion = numero.replace(",", ".").partition(".")
    digitos = entero + fraccion
    posicion = len(entero) + desplazar
    if posicion <= 0:
        digitos = "0" * (1 - posicion) + digitos
        posicion = 1
    if posicion >= len(digitos):
        digitos += "0" * (posicion - len(digitos))
    entero = digitos[:posicion].lstrip("0") or "0"
    fraccion = digitos[posicion:].rstrip("0")
    return entero + ("," + fraccion if fraccion else "")


def _litros(numero):
    numero = _decimal(numero)
    return numero + (" litro" if numero == "1" else " litros")


def _cc(numero):
    entero = numero.replace(",", ".").split(".")[0]
    return _litros(_decimal(numero, -3)) if int(entero) >= 1000 else _decimal(numero) + " cc"


def descripcion_para_voz(texto: str) -> str:
    """Expandir solo equivalencias conocidas; conservar el resto en mayúsculas.

    No infiere unidades para decimales sin unidad ni significados de códigos.
    Una entrada que no sea str produce TypeError.
    """
    if not isinstance(texto, str):
        raise TypeError("La descripción debe ser texto (str).")
    texto = texto.upper().replace("*", " ").replace("#", " ")
    for patron, reemplazo in _EQUIVALENCIAS:
        texto = _sustituir(texto, patron, reemplazo)

    # Volúmenes específicos antes de números y unidades generales.
    texto = _sustituir(texto, r"(\d+[.,]\d+)\s*L", lambda m: (
        _cc(_decimal(m[1], 3)) if int(m[1].replace(",", ".").split(".")[0]) == 0
        else _litros(m[1])
    ))
    texto = _sustituir(texto, r"LAT\s+(\d+)(?![.,]\d)(?:\s*CC)?", lambda m: "lata de " + _cc(m[1]))
    texto = _sustituir(texto, r"PET\s*(\d+)(?![.,]\d)(?:\s*CC)?", lambda m: "botella de " + _PET.get(m[1], _cc(m[1])))
    # RET unido al número sí declara una medida; separado puede seguir a una marca.
    texto = _sustituir(texto, r"(?<![.,])(\d+)RET|(?<![.,])1000RE", lambda m: _cc(m[1] or "1000") + " retornable")
    # El separador decimal está definido para L, no para CC: no adivinar miles.
    texto = _sustituir(texto, "(" + _NUMERO + r")\s*CC", lambda m: (
        m[1] + " cc" if "." in m[1] or "," in m[1] else _cc(m[1])
    ))
    texto = _sustituir(texto, r"(\d+)\s*L", lambda m: _litros(m[1]))
    texto = _sustituir(texto, r"(\d+)\s*GR", lambda m: m[1] + " gramos")
    texto = _sustituir(texto, r"(\d+)\s*KCAL", lambda m: m[1] + " calorías")
    texto = re.sub(r"(?<![\w.,])0\.0(?![\w.,])", "cero", texto)

    # No tocar códigos (ABC330, A-330, 330/ABC), decimales ni cantidades con unidad.
    texto = re.sub(
        r"(?<![\w.,/+\-])([2-9]\d{2}|1000)(?![\w.,/\-])"
        r"(?!\s+(?:cc|litros?|gramos|calorías|ML|CL|KG|MG|GR|CM|MM)\b)",
        lambda m: _cc(m[1]), texto,
    )
    texto = re.sub(_INICIO + r"L\s*$", "litro", texto)

    texto = _sustituir(texto, r"(\d+)X(\d+)", lambda m: m[1] + " packs de " + m[2])
    texto = _sustituir(texto, r"X(\d+)", lambda m: "" if int(m[1]) == 1 else "pack de " + m[1])
    texto = _sustituir(texto, "TWOPACK", "dos packs")
    texto = re.sub(r"(packs? de \d+)\s+(" + _NUMERO + r" (?:cc|litros?))\b", r"\1 de \2", texto)

    if ABREVIATURAS:
        # Una sola sustitución evita expandir otra vez palabras del reemplazo.
        claves = sorted(ABREVIATURAS, key=len, reverse=True)
        texto = _sustituir(texto, "|".join(re.escape(k) for k in claves), lambda m: ABREVIATURAS[m[0]])
    texto = re.sub(_INICIO + r"C/", "con ", texto)
    texto = re.sub(_INICIO + r"S/", "sin ", texto)
    texto = _sustituir(texto, "OW", " ")
    texto = re.sub(r"(?<!\S)-(?!\S)", " ", texto)
    texto = re.sub(r"centímetros\s+cúbicos", "cc", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bcc(?:\s+cc)+\b", "cc", texto, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", texto).strip(" -,.")
