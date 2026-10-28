import csv

import pytest

from voz.conversor import ABREVIATURAS, descripcion_para_voz
from scripts.validar_csv import comparar, main


@pytest.mark.parametrize("original, esperado", [
    ("NEGRA MODELO OW X24 0,355L", "NEGRA MODELO pack de 24 de 355 cc"),
    ("MIRINDA NARANJA * X6 PET1500#", "MIRINDA NARANJA pack de 6 botella de 1,5 litros"),
    ("BRAHMA CARNAVAL RET X12 1000CC", "BRAHMA CARNAVAL retornable pack de 12 de 1 litro"),
    ("STELLA ARTOIS - 4X6 330 OW#", "STELLA ARTOIS 4 packs de 6 de 330 cc"),
    ("7 UP LIM-LIM * X6 PET1500#", "Seven Up lima limón pack de 6 botella de 1,5 litros"),
    ("PASO DLT POMELO * X24 LAT 354", "Paso de los Toros POMELO pack de 24 lata de 354 cc"),
    ("BUD CAN 2X12 0,355L IMPO", "Budweiser lata 2 packs de 12 de 355 cc IMPO"),
    ("GLACIAR ADM PET BIDON 6,3L X2", "GLACIAR botellón BIDON 6,3 litros pack de 2"),
    ("GATORADE FRU TRO * X6 PET 500", "GATORADE frutas tropicales pack de 6 botella de 500 cc"),
    ("NPV _AGUA MESA_ SG_ PET X6 2,0", "Nestlé Pureza Vital _AGUA MESA_ sin gas_ botella pack de 6 2,0"),
])
def test_casos_solicitados(original, esperado):
    assert descripcion_para_voz(original) == esperado


@pytest.mark.parametrize("original, esperado", [
    ("S/G C/G SG CG", "sin gas con gas sin gas con gas"),
    ("ASG SG2 CGA 1CG BUDGET STA1 PETABC", "ASG SG2 CGA 1CG BUDGET STA1 PETABC"),
    ("7-UP 7UP PATAGO PARAG BUD", "Seven Up Seven Up Patagonia Patagonia Budweiser"),
    ("COOL BLU COOLBLU LIM LIM PDT DLT", "Cool Blue Cool Blue lima limón Paso de los Toros de los Toros"),
    ("NAR NARA DUR AWAF MANZ TROP STA NPV", "naranja naranja durazno Awafrut manzana tropicales Stella Nestlé Pureza Vital"),
    ("0.5L 1.65L 1,0L 0,0005L", "500 cc 1,65 litros 1 litro 0,5 cc"),
    ("473CC 355CC 410CC 1000CC 1500CC 2250CC 3000CC", "473 cc 355 cc 410 cc 1 litro 1,5 litros 2,25 litros 3 litros"),
    ("PET1500 PET2250 PET2000 PET2500 PET250 PET500 PET3000", "botella de 1,5 litros botella de 2,25 litros botella de 2 litros botella de 2,5 litros botella de 250 cc botella de 500 cc botella de 3 litros"),
    ("1000RET 750RET 1500RET 1000RE", "1 litro retornable 750 cc retornable 1,5 litros retornable 1 litro retornable"),
    ("20L 30L 1L 500GR 70KCAL 0.0", "20 litros 30 litros 1 litro 500 gramos 70 calorías cero"),
    ("199 200 999 1000 1001", "199 200 cc 999 cc 1 litro 1001"),
    ("A330 330B A-330 330/A 2,0 1.65 0.01", "A330 330B A-330 330/A 2,0 1.65 0.01"),
    ("X1 X12 X200 TWOPACK", "pack de 12 pack de 200 dos packs"),
    ("CAN PET RET C/RACK S/AZUCAR GDE GDC VERT SUBCERO", "lata botella retornable con RACK sin AZUCAR grande grande vertical sub cero"),
    (" \t- . AGUA 355 CC cc centímetros cúbicos # - \n", "AGUA 355 cc"),
    ("MARCA IMPO BIDON L", "MARCA IMPO BIDON litro"),
    ("PALABRA-NUEVA CODIGO123", "PALABRA-NUEVA CODIGO123"),
    ("PATAGONIA 24.7 RET QUILMES 1890 RET ANDES 2.0 RET", "PATAGONIA 24.7 retornable QUILMES 1890 retornable ANDES 2.0 retornable"),
    ("2.000CC 1.500CC 6.400CC", "2.000 cc 1.500 cc 6.400 cc"),
    ("473 ML 500 KG 350ML", "473 ML 500 KG 350ML"),
    ("PET 1.500 LAT 354.5", "botella 1.500 LAT 354.5"),
    ("", ""),
    (" * # - ", ""),
])
def test_reglas_y_limites(original, esperado):
    assert descripcion_para_voz(original) == esperado


def test_diccionario_editable_literal_sin_encadenar(monkeypatch):
    monkeypatch.setitem(ABREVIATURAS, "PRUEBA", "CAN")
    monkeypatch.setitem(ABREVIATURAS, "A+B", "especial")
    assert descripcion_para_voz("PRUEBA A+B PRUEBA2") == "CAN especial PRUEBA2"


@pytest.mark.parametrize("valor", [None, 123, []])
def test_rechaza_entradas_no_textuales(valor):
    with pytest.raises(TypeError):
        descripcion_para_voz(valor)


def test_comparador_csv_bom_comillas_y_vacios(tmp_path, capsys):
    archivo = tmp_path / "referencia.csv"
    with archivo.open("w", encoding="utf-8-sig", newline="") as salida:
        writer = csv.writer(salida, delimiter=";")
        writer.writerow(["Codigo", "Descripcion original", "Descripcion para voz"])
        writer.writerows([["001", "BUD", "Budweiser"], ["002", "A;B", "diferente"], ["003", "AGUA", ""]])
    antes = archivo.read_bytes()
    total, coinciden, vacias, diferencias = comparar(archivo)
    assert (total, coinciden, vacias) == (3, 1, 1)
    assert diferencias[0] == {"fila": 3, "codigo": "002", "original": "A;B", "esperado": "diferente", "obtenido": "A;B"}
    assert main([str(archivo)]) == 1
    assert "No coinciden: 2" in capsys.readouterr().out
    assert archivo.read_bytes() == antes


def test_comparador_rechaza_columnas_faltantes(tmp_path):
    archivo = tmp_path / "invalido.csv"
    archivo.write_text("Codigo;Descripcion original\n1;BUD\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Faltan columnas"):
        comparar(archivo)
