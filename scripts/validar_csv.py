"""Comparar descripciones con una referencia CSV, sin escribir en ella."""

import argparse
import csv
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voz.conversor import descripcion_para_voz


def comparar(ruta):
    total = coinciden = vacias = 0
    diferencias = []
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo, delimiter=";")
        requeridas = {"Descripcion original", "Descripcion para voz"}
        if not requeridas.issubset(lector.fieldnames or []):
            raise ValueError("Faltan columnas: " + ", ".join(sorted(requeridas - set(lector.fieldnames or []))))
        for fila in lector:
            if None in fila or any(v is None for v in fila.values()):
                raise ValueError(f"Fila mal formada cerca de la línea {lector.line_num}.")
            total += 1
            esperado = fila["Descripcion para voz"]
            obtenido = descripcion_para_voz(fila["Descripcion original"])
            vacias += not esperado.strip()
            if obtenido == esperado:
                coinciden += 1
            else:
                diferencias.append({"fila": total + 1, "codigo": fila.get("Codigo", ""),
                                    "original": fila["Descripcion original"],
                                    "esperado": esperado, "obtenido": obtenido})
    return total, coinciden, vacias, diferencias


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("referencia", nargs="?", default="descripciones-voz.csv", help="CSV UTF-8 con BOM opcional y separador ;")
    args = parser.parse_args(argv)
    try:
        total, coinciden, vacias, diferencias = comparar(args.referencia)
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        parser.exit(2, f"Error: {error}\n")
    print(f"Filas: {total} | Coinciden: {coinciden} | No coinciden: {len(diferencias)} | Referencias vacías: {vacias}")
    for fila in diferencias[:20]:
        print(f"\nFila {fila['fila']} | Código {fila['codigo']}\n  Original: {fila['original']}\n  Esperado: {fila['esperado']}\n  Obtenido: {fila['obtenido']}")
    return 1 if diferencias else 0


if __name__ == "__main__":
    raise SystemExit(main())
