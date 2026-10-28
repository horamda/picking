# Validacion de la referencia de voz

Archivo: `descripciones-voz-listo.csv`. SHA-256: `0a074bdd275dff3425e05bc91633f265cb7495bcaf957920ad33cd54682f2008`.

Filas de datos: **1728**. Coinciden exactamente: **1475**. Diferencias: **253**. Referencias vacias: **0**.

La fila 1 corresponde al encabezado. Se muestra cada diferencia, sin modificar el CSV ni importar sus datos en la app.

## Criterios que requieren revision

- Las reglas escritas prevalecen sobre ejemplos contradictorios del CSV: se agrega `de` entre pack y volumen, y `FRU TRO` se expande a frutas tropicales.
- `AGUAS/G` y `AGUAC/G` no cumplen los limites de palabra solicitados. El CSV convierte ambos a aguas con gas. Esa equivalencia requiere confirmar el significado antes de adoptarla.
- Numeros sin unidad de cuatro cifras (ejemplo `X6 1500`) se conservan. La regla escrita solo asigna cc a numeros aislados entre 200 y 1000; la conversion general de cuatro cifras requiere que sean valores en cc.
- Codigos como `V-200` y `C-2500` no son volumenes. El CSV les asigna unidades; el conversor los conserva.
- El CSV agrega cc a varios pesos (ejemplo `500GR` -> `500 cc gramos`). El conversor conserva solamente gramos.
- Hay formatos adicionales sin reglas aprobadas: `X 9`, `700ML`, separadores en `2.000CC`, descripciones truncadas como `PET 50` y packs inversos como `473X24`.
- Se normalizan ceros decimales en litros (`2,250L` -> `2,25 litros`); algunas referencias los conservan.

## Todas las diferencias

| Fila | Codigo | Original | Referencia | Conversor |
| ---: | --- | --- | --- | --- |
| 14 | 10544 | STELLA NOIRE NEGRA 4X6 330 OW# | STELLA NOIRE NEGRA 4 packs de 6 330 cc | STELLA NOIRE NEGRA 4 packs de 6 de 330 cc |
| 20 | 10576 | STELLA ARTOIS - 4X6 330 OW# | STELLA ARTOIS 4 packs de 6 330 cc | STELLA ARTOIS 4 packs de 6 de 330 cc |
| 22 | 10597 | LIEBER - X12 1000RET# | LIEBER pack de 12 1 litro retornable | LIEBER pack de 12 de 1 litro retornable |
| 23 | 10608 | QUILMES BAJO0 - X12 1000RET# | QUILMES BAJO0 pack de 12 1 litro retornable | QUILMES BAJO0 pack de 12 de 1 litro retornable |
| 24 | 10612 | QUILMES STOUT NEGRA X12 1000RE | QUILMES STOUT NEGRA pack de 12 1 litro retornable | QUILMES STOUT NEGRA pack de 12 de 1 litro retornable |
| 38 | 10777 | STELLA ARTOIS - 4X6 330 OW# | STELLA ARTOIS 4 packs de 6 330 cc | STELLA ARTOIS 4 packs de 6 de 330 cc |
| 39 | 10778 | STELLA ARTOIS - X12 1000RET# | STELLA ARTOIS pack de 12 1 litro retornable | STELLA ARTOIS pack de 12 de 1 litro retornable |
| 40 | 10784 | GATORADE FRU TRO * X6 PET 500 | GATORADE FRU TRO pack de 6 botella de 500 cc | GATORADE frutas tropicales pack de 6 botella de 500 cc |
| 54 | 1099 | GATORADE FRU TRO * X6 473 OW# | GATORADE FRU TRO pack de 6 de 473 cc | GATORADE frutas tropicales pack de 6 de 473 cc |
| 63 | 11042 | IGUANA - X12 1000RET | IGUANA pack de 12 1 litro retornable | IGUANA pack de 12 de 1 litro retornable |
| 64 | 11065 | GATORADE FRU TRO * X6 PET1250# | GATORADE FRU TRO pack de 6 botella de 1,25 litros | GATORADE frutas tropicales pack de 6 botella de 1,25 litros |
| 68 | 11071 | GATORADE FRU TRO * X1 PET 500# | GATORADE FRU TRO botella de 500 cc | GATORADE frutas tropicales botella de 500 cc |
| 88 | 11437 | EQUIPO ELECT V-200 UBC GROUP U | EQUIPO ELECT V-200 cc UBC GROUP U | EQUIPO ELECT V-200 UBC GROUP U |
| 101 | 11521 | GATORADE FRU TRO * X6 PET 500 | GATORADE FRU TRO pack de 6 botella de 500 cc | GATORADE frutas tropicales pack de 6 botella de 500 cc |
| 102 | 11522 | GATORADE FRU TRO * X6 PET 500# | GATORADE FRU TRO pack de 6 botella de 500 cc | GATORADE frutas tropicales pack de 6 botella de 500 cc |
| 150 | 132 | GLACIAR AGUAS/G * X6 PET1500 | GLACIAR aguas con gas pack de 6 botella de 1,5 litros | GLACIAR AGUAS/G pack de 6 botella de 1,5 litros |
| 157 | 13223 | PEPSI PET X6 1500 BLACK | PEPSI botella pack de 6 de 1,5 litros BLACK | PEPSI botella pack de 6 1500 BLACK |
| 158 | 13224 | QUILMES 1890 CAN 4X6 473 | QUILMES 1890 lata 4 packs de 6 473 cc | QUILMES 1890 lata 4 packs de 6 de 473 cc |
| 160 | 13228 | PEPSI PET X8 2250 BLACK | PEPSI botella pack de 8 de 2,25 litros BLACK | PEPSI botella pack de 8 2250 BLACK |
| 161 | 133 | GLACIAR AGUAS/G * X6 PET2000 | GLACIAR aguas con gas pack de 6 botella de 2 litros | GLACIAR AGUAS/G pack de 6 botella de 2 litros |
| 163 | 13404 | BRAHMA CHOPP CAN 1X12 473 ML S | BRAHMA CHOPP lata 1 packs de 12 de 473 cc S | BRAHMA CHOPP lata 1 packs de 12 473 ML S |
| 166 | 13501 | PEPSI PET PR 0,250L X 9 | PEPSI botella PR 250 cc pack de 9 | PEPSI botella PR 250 cc X 9 |
| 167 | 13502 | STELLA ARTOIS CAN 4X6 473 | STELLA ARTOIS lata 4 packs de 6 473 cc | STELLA ARTOIS lata 4 packs de 6 de 473 cc |
| 168 | 13503 | QUILMES STOUT CAN 4X6 473 | QUILMES STOUT lata 4 packs de 6 473 cc | QUILMES STOUT lata 4 packs de 6 de 473 cc |
| 182 | 13950 | PEPSI PET X8 2250 BLACK | PEPSI botella pack de 8 de 2,25 litros BLACK | PEPSI botella pack de 8 2250 BLACK |
| 183 | 13952 | PEPSI CAN 4X6 354 BLACK | PEPSI lata 4 packs de 6 354 cc BLACK | PEPSI lata 4 packs de 6 de 354 cc BLACK |
| 188 | 14094 | AWAF NAR-DUR PET X6 1.65L PN | Awafrut naranja-durazno botella pack de 6 1,65 litros PN | Awafrut naranja-durazno botella pack de 6 de 1,65 litros PN |
| 189 | 14095 | AWAF POMELO PET X6 1.65L PN | Awafrut POMELO botella pack de 6 1,65 litros PN | Awafrut POMELO botella pack de 6 de 1,65 litros PN |
| 192 | 14098 | AWAF PERA PET  X6 1.65L PN | Awafrut PERA botella pack de 6 1,65 litros PN | Awafrut PERA botella pack de 6 de 1,65 litros PN |
| 193 | 14099 | AWAF LIMON PET X6 1.65L PN | Awafrut LIMON botella pack de 6 1,65 litros PN | Awafrut LIMON botella pack de 6 de 1,65 litros PN |
| 195 | 14100 | AWAF POMELO PET X06 2,250L PN | Awafrut POMELO botella pack de 06 2,250 litros PN | Awafrut POMELO botella pack de 06 de 2,25 litros PN |
| 196 | 14101 | AWA NAR-DUR PET X6 2,250 L PN | AWA naranja-durazno botella pack de 6 2,250 litros PN | AWA naranja-durazno botella pack de 6 de 2,25 litros PN |
| 207 | 14190 | H2OH CITRUS CAN 4X6 354 | H2OH CITRUS lata 4 packs de 6 354 cc | H2OH CITRUS lata 4 packs de 6 de 354 cc |
| 208 | 14191 | PEPSI BLACK PET X6 1500 | PEPSI BLACK botella pack de 6 de 1,5 litros | PEPSI BLACK botella pack de 6 1500 |
| 221 | 1426 | GATORADE FRU TRO * X6 PET1250 | GATORADE FRU TRO pack de 6 botella de 1,25 litros | GATORADE frutas tropicales pack de 6 botella de 1,25 litros |
| 241 | 14902 | ECO DE LOS ANDES SG PET X6 100 | ECO DE LOS ANDES sin gas botella pack de 6 de 100 cc | ECO DE LOS ANDES sin gas botella pack de 6 100 |
| 246 | 14938 | ECO ANDES SG PET X6 2000 PR 92 | ECO ANDES sin gas botella pack de 6 de 2 litros PR 92 | ECO ANDES sin gas botella pack de 6 2000 PR 92 |
| 254 | 15171 | STELLA ARTOIS CAN 4X6 269 | STELLA ARTOIS lata 4 packs de 6 269 cc | STELLA ARTOIS lata 4 packs de 6 de 269 cc |
| 255 | 15178 | CORONA OW 2X12 355 | CORONA 2 packs de 12 355 cc | CORONA 2 packs de 12 de 355 cc |
| 256 | 15234 | STELLA ARTOIS CAN 4X6 473 CART | STELLA ARTOIS lata 4 packs de 6 473 cc CART | STELLA ARTOIS lata 4 packs de 6 de 473 cc CART |
| 258 | 15240 | STELLA ARTOIS CAN 4X6 355 | STELLA ARTOIS lata 4 packs de 6 355 cc | STELLA ARTOIS lata 4 packs de 6 de 355 cc |
| 261 | 15605 | BRAHMA CAN 4X6 473 PR | BRAHMA lata 4 packs de 6 473 cc PR | BRAHMA lata 4 packs de 6 de 473 cc PR |
| 264 | 15621 | PATAGONIA IPA CAN 4X6 473 CART | PATAGONIA IPA lata 4 packs de 6 473 cc CART | PATAGONIA IPA lata 4 packs de 6 de 473 cc CART |
| 265 | 15624 | BRAHMA CAN 4X6 269 | BRAHMA lata 4 packs de 6 269 cc | BRAHMA lata 4 packs de 6 de 269 cc |
| 266 | 1586 | STELLA ARTOIS - X12 1000RET# | STELLA ARTOIS pack de 12 1 litro retornable | STELLA ARTOIS pack de 12 de 1 litro retornable |
| 268 | 1606 | PASO DLT POMELO LIGH X12 PET 5 | Paso de los Toros POMELO LIGH pack de 12 botella 5 | Paso de los Toros POMELO LIGH pack de 12 botella de 5 cc |
| 270 | 16225 | PATAGONIA AMBER CAN 4X6 473 CA | PATAGONIA AMBER lata 4 packs de 6 473 cc CA | PATAGONIA AMBER lata 4 packs de 6 de 473 cc CA |
| 276 | 16371 | RED BULL CAN 6X4 250 | RED BULL lata 6 packs de 4 250 cc | RED BULL lata 6 packs de 4 de 250 cc |
| 278 | 16375 | RED BULL CAN 4X6 250 | RED BULL lata 4 packs de 6 250 cc | RED BULL lata 4 packs de 6 de 250 cc |
| 291 | 16666 | ANDES ORIGEN NEGRA RET X12 100 | ANDES ORIGEN NEGRA retornable pack de 12 de 100 cc | ANDES ORIGEN NEGRA retornable pack de 12 100 |
| 293 | 16668 | ANDES ORIGEN RUBIA RET X12 100 | ANDES ORIGEN RUBIA retornable pack de 12 de 100 cc | ANDES ORIGEN RUBIA retornable pack de 12 100 |
| 302 | 16811 | ANDES ORIGEN RUBIA CAN 4X6 473 | ANDES ORIGEN RUBIA lata 4 packs de 6 473 cc | ANDES ORIGEN RUBIA lata 4 packs de 6 de 473 cc |
| 306 | 16986 | QUILMES BOCK CAN 4X6 473 | QUILMES BOCK lata 4 packs de 6 473 cc | QUILMES BOCK lata 4 packs de 6 de 473 cc |
| 308 | 17081 | ECO DE LOS ANDES SG PET X6 100 | ECO DE LOS ANDES sin gas botella pack de 6 de 100 cc | ECO DE LOS ANDES sin gas botella pack de 6 100 |
| 309 | 17091 | BUD CAN 4X6 473 | Budweiser lata 4 packs de 6 473 cc | Budweiser lata 4 packs de 6 de 473 cc |
| 310 | 17095 | BUD CAN 4X6 355 | Budweiser lata 4 packs de 6 355 cc | Budweiser lata 4 packs de 6 de 355 cc |
| 311 | 17097 | 7-UP PET X8 2450 | Seven Up botella pack de 8 de 2,45 litros | Seven Up botella pack de 8 2450 |
| 312 | 17358 | ANDES CAN 4X6 473 | ANDES lata 4 packs de 6 473 cc | ANDES lata 4 packs de 6 de 473 cc |
| 315 | 17501 | WRST CAN 4X6 473 80BUL/PAL | WRST lata 4 packs de 6 473 cc 80BUL/PAL | WRST lata 4 packs de 6 de 473 cc 80BUL/PAL |
| 328 | 17932 | ANDES ORIGEN ROJA CAN 4X6 473 | ANDES ORIGEN ROJA lata 4 packs de 6 473 cc | ANDES ORIGEN ROJA lata 4 packs de 6 de 473 cc |
| 329 | 17933 | ANDES ORIGEN NEGRA CAN 4X6 473 | ANDES ORIGEN NEGRA lata 4 packs de 6 473 cc | ANDES ORIGEN NEGRA lata 4 packs de 6 de 473 cc |
| 330 | 17952 | GUARANÁ SIN AZÚCAR PET X6 1500 | GUARANÁ SIN AZÚCAR botella pack de 6 de 1,5 litros | GUARANÁ SIN AZÚCAR botella pack de 6 1500 |
| 331 | 17953 | GUARANÁ SIN AZÚCAR PET X8 2250 | GUARANÁ SIN AZÚCAR botella pack de 8 de 2,25 litros | GUARANÁ SIN AZÚCAR botella pack de 8 2250 |
| 332 | 17954 | GUARANÁ SIN AZÚCAR CAN 4X6 354 | GUARANÁ SIN AZÚCAR lata 4 packs de 6 354 cc | GUARANÁ SIN AZÚCAR lata 4 packs de 6 de 354 cc |
| 342 | 18558 | 7UP REG PET X8 2450 PROMO | Seven Up REG botella pack de 8 de 2,45 litros PROMO | Seven Up REG botella pack de 8 2450 PROMO |
| 343 | 18559 | PEPSI REG PET X8 2450 PROMO | PEPSI REG botella pack de 8 de 2,45 litros PROMO | PEPSI REG botella pack de 8 2450 PROMO |
| 344 | 18561 | MIRINDA NARANJA PET X6 3000 NF | MIRINDA NARANJA botella pack de 6 de 3 litros NF | MIRINDA NARANJA botella pack de 6 3000 NF |
| 345 | 18562 | MIRINDA NARANJA PET X8 2250 NF | MIRINDA NARANJA botella pack de 8 de 2,25 litros NF | MIRINDA NARANJA botella pack de 8 2250 NF |
| 347 | 18564 | RED BULL PR BDG CAN 6X4 250 | RED BULL PR BDG lata 6 packs de 4 250 cc | RED BULL PR BDG lata 6 packs de 4 de 250 cc |
| 348 | 18565 | MIRINDA NARANJA PET X6 1500 NF | MIRINDA NARANJA botella pack de 6 de 1,5 litros NF | MIRINDA NARANJA botella pack de 6 1500 NF |
| 349 | 18568 | MIRINDA PET X 9 0,25L NF | MIRINDA botella pack de 9 de 250 cc NF | MIRINDA botella X 9 250 cc NF |
| 352 | 18571 | H2OH CITRUS PET X8 2250 PROMO | H2OH CITRUS botella pack de 8 de 2,25 litros PROMO | H2OH CITRUS botella pack de 8 2250 PROMO |
| 353 | 18572 | H2OH LIMONETO PET X8 2250 PROM | H2OH LIMONETO botella pack de 8 de 2,25 litros PROM | H2OH LIMONETO botella pack de 8 2250 PROM |
| 354 | 18587 | PATAGONIA AMBER CAN 4X6 473 | PATAGONIA AMBER lata 4 packs de 6 473 cc | PATAGONIA AMBER lata 4 packs de 6 de 473 cc |
| 355 | 18588 | PATAGONIA WEISSE CAN 4X6 473 | PATAGONIA WEISSE lata 4 packs de 6 473 cc | PATAGONIA WEISSE lata 4 packs de 6 de 473 cc |
| 363 | 18743 | NPV SG PET X6 1500 PR 1.5L S/G | Nestlé Pureza Vital sin gas botella pack de 6 de 1,5 litros PR 1,5 litros sin gas | Nestlé Pureza Vital sin gas botella pack de 6 1500 PR 1,5 litros sin gas |
| 364 | 18744 | NPV SG PET X6 2250 PR 2.25L S/ | Nestlé Pureza Vital sin gas botella pack de 6 de 2,25 litros PR 2,25 litros sin | Nestlé Pureza Vital sin gas botella pack de 6 2250 PR 2,25 litros sin |
| 365 | 18745 | NPV SG PET 0 3000 PR 6,3L - 3 | Nestlé Pureza Vital sin gas botella 0 3000 PR 6,3 litros 3 | Nestlé Pureza Vital sin gas botella de 0 cc 3000 PR 6,3 litros 3 |
| 366 | 18746 | NPV SG PET 0 3000PR 6,3L -4 PI | Nestlé Pureza Vital sin gas botella 0 3000PR 6,3 litros -4 PI | Nestlé Pureza Vital sin gas botella de 0 cc 3000PR 6,3 litros -4 PI |
| 369 | 19026 | BUD CAN 4X6 473 CMQ | Budweiser lata 4 packs de 6 473 cc CMQ | Budweiser lata 4 packs de 6 de 473 cc CMQ |
| 370 | 19086 | PEPSI PET X6 1500 NF | PEPSI botella pack de 6 de 1,5 litros NF | PEPSI botella pack de 6 1500 NF |
| 371 | 19087 | PEPSI PET X8 2250 NF | PEPSI botella pack de 8 de 2,25 litros NF | PEPSI botella pack de 8 2250 NF |
| 372 | 19088 | PEPSI RECO PET X8 2000 NF | PEPSI RECO botella pack de 8 de 2 litros NF | PEPSI RECO botella pack de 8 2000 NF |
| 373 | 19089 | PEPSI PET X6 3000 NF | PEPSI botella pack de 6 de 3 litros NF | PEPSI botella pack de 6 3000 NF |
| 375 | 19111 | NPV SG PET X6 1500 PR 4 PISOS | Nestlé Pureza Vital sin gas botella pack de 6 de 1,5 litros PR 4 PISOS | Nestlé Pureza Vital sin gas botella pack de 6 1500 PR 4 PISOS |
| 376 | 19189 | PEPSI PET X8 2000 NF | PEPSI botella pack de 8 de 2 litros NF | PEPSI botella pack de 8 2000 NF |
| 384 | 19254 | ANDES ORIGEN IPA CAN 4X6 473 | ANDES ORIGEN IPA lata 4 packs de 6 473 cc | ANDES ORIGEN IPA lata 4 packs de 6 de 473 cc |
| 387 | 19337 | 7-UP PET X6 1500 NF | Seven Up botella pack de 6 de 1,5 litros NF | Seven Up botella pack de 6 1500 NF |
| 388 | 19338 | 7-UP PET X8 2250 NF | Seven Up botella pack de 8 de 2,25 litros NF | Seven Up botella pack de 8 2250 NF |
| 389 | 19339 | 7-UP PET X6 3000 NF | Seven Up botella pack de 6 de 3 litros NF | Seven Up botella pack de 6 3000 NF |
| 390 | 19341 | 7-UP RECO X8 2000 NF | Seven Up RECO pack de 8 de 2 litros NF | Seven Up RECO pack de 8 2000 NF |
| 391 | 19348 | BUDWEISER CAN 4X6 473 PROMO | BUDWEISER lata 4 packs de 6 473 cc PROMO | BUDWEISER lata 4 packs de 6 de 473 cc PROMO |
| 392 | 19365 | PATAGONIA IPA CAN 4X6 473 TRAN | PATAGONIA IPA lata 4 packs de 6 473 cc TRAN | PATAGONIA IPA lata 4 packs de 6 de 473 cc TRAN |
| 393 | 19372 | PATAGONIA AMBER CAN 4X6 473 TR | PATAGONIA AMBER lata 4 packs de 6 473 cc TR | PATAGONIA AMBER lata 4 packs de 6 de 473 cc TR |
| 397 | 19498 | PATAGONIA WEISSE CAN 4X6 473 C | PATAGONIA WEISSE lata 4 packs de 6 473 cc C | PATAGONIA WEISSE lata 4 packs de 6 de 473 cc C |
| 399 | 19534 | QUILMES RED LAGER CAN 4X6 473 | QUILMES RED LAGER lata 4 packs de 6 473 cc | QUILMES RED LAGER lata 4 packs de 6 de 473 cc |
| 412 | 20360 | PATAGONIA KUNE CAN 4X6 473 CAR | PATAGONIA KUNE lata 4 packs de 6 473 cc CAR | PATAGONIA KUNE lata 4 packs de 6 de 473 cc CAR |
| 419 | 2051 | ANDES - X12 1000RET | ANDES pack de 12 1 litro retornable | ANDES pack de 12 de 1 litro retornable |
| 428 | 20810 | BRAHMA LIME CAN 4X6 269 | BRAHMA LIME lata 4 packs de 6 269 cc | BRAHMA LIME lata 4 packs de 6 de 269 cc |
| 429 | 2089 | IGUANA - X6 1000RET# | IGUANA pack de 6 1 litro retornable | IGUANA pack de 6 de 1 litro retornable |
| 430 | 2093 | IGUANA - X12 1000RET# | IGUANA pack de 12 1 litro retornable | IGUANA pack de 12 de 1 litro retornable |
| 435 | 21033 | CORONA OW 4X6 330 IMPO | CORONA 4 packs de 6 330 cc IMPO | CORONA 4 packs de 6 de 330 cc IMPO |
| 444 | 21473 | GLACIAR PET X6 1250 PLUS MANZA | GLACIAR botella pack de 6 de 1,25 litros PLUS MANZA | GLACIAR botella pack de 6 1250 PLUS MANZA |
| 445 | 21474 | GLACIAR PET X6 1250 PLUS LIMON | GLACIAR botella pack de 6 de 1,25 litros PLUS LIMON | GLACIAR botella pack de 6 1250 PLUS LIMON |
| 447 | 2153 | Q ECO X 20 | Q ECO pack de 20 | Q ECO X 20 |
| 448 | 2156 | BALTICA - X12 1000RET | BALTICA pack de 12 1 litro retornable | BALTICA pack de 12 de 1 litro retornable |
| 450 | 2157 | ECO ANDES AGUAC/G * X20 500 RE | ECO ANDES aguas con gas pack de 20 de 500 cc RE | ECO ANDES AGUAC/G pack de 20 de 500 cc RE |
| 451 | 2158 | ECO ANDES AGUAS/G * X20 500 RE | ECO ANDES aguas con gas pack de 20 de 500 cc RE | ECO ANDES AGUAS/G pack de 20 de 500 cc RE |
| 453 | 21698 | PDTOROS TONICA CAN 4X6 269 | PDTOROS TONICA lata 4 packs de 6 269 cc | PDTOROS TONICA lata 4 packs de 6 de 269 cc |
| 459 | 21846 | PATAGONIA VERA IPA CAN 4X6 410 | PATAGONIA VERA IPA lata 4 packs de 6 410 cc | PATAGONIA VERA IPA lata 4 packs de 6 de 410 cc |
| 460 | 21847 | PATAGONIA BOHEMIAN CAN 4X6 410 | PATAGONIA BOHEMIAN lata 4 packs de 6 410 cc | PATAGONIA BOHEMIAN lata 4 packs de 6 de 410 cc |
| 461 | 21849 | PATAGONIA VERA IPA CAN 4X6 410 | PATAGONIA VERA IPA lata 4 packs de 6 410 cc | PATAGONIA VERA IPA lata 4 packs de 6 de 410 cc |
| 465 | 21863 | CORONA CAN 4X6 269 CART | CORONA lata 4 packs de 6 269 cc CART | CORONA lata 4 packs de 6 de 269 cc CART |
| 466 | 21864 | CORONA CAN 2X10 269 CART | CORONA lata 2 packs de 10 269 cc CART | CORONA lata 2 packs de 10 de 269 cc CART |
| 471 | 21965 | 7-UP PET X8 2450 NF | Seven Up botella pack de 8 de 2,45 litros NF | Seven Up botella pack de 8 2450 NF |
| 472 | 21966 | PEPSI COLA PET X08 2.45L NF | PEPSI COLA botella pack de 08 2,45 litros NF | PEPSI COLA botella pack de 08 de 2,45 litros NF |
| 473 | 21967 | PEPSI CAN 4X6 354 NF | PEPSI lata 4 packs de 6 354 cc NF | PEPSI lata 4 packs de 6 de 354 cc NF |
| 474 | 21971 | 7-UP NF CAN 4X6 354 | Seven Up NF lata 4 packs de 6 354 cc | Seven Up NF lata 4 packs de 6 de 354 cc |
| 479 | 22057 | TRATENFU ALMENDRA X8 1L | TRATENFU ALMENDRA pack de 8 1 litro | TRATENFU ALMENDRA pack de 8 de 1 litro |
| 482 | 22134 | P HOPPY L CAN X10 269 | P HOPPY litro lata pack de 10 de 269 cc | P HOPPY L lata pack de 10 de 269 cc |
| 487 | 22275 | GIFT AO CAN 4X6 473 VARIEDADES | GIFT AO lata 4 packs de 6 473 cc VARIEDADES | GIFT AO lata 4 packs de 6 de 473 cc VARIEDADES |
| 490 | 22318 | ECO DE LOS ANDES SG PET X6 100 | ECO DE LOS ANDES sin gas botella pack de 6 de 100 cc | ECO DE LOS ANDES sin gas botella pack de 6 100 |
| 494 | 22322 | ROBINO NEBIOLO AMABLE OW 6X 75 | ROBINO NEBIOLO AMABLE 6 packs de 75 | ROBINO NEBIOLO AMABLE 6X 75 |
| 532 | 22608 | SA NOIRE CAN 4X6 473 CART | SA NOIRE lata 4 packs de 6 473 cc CART | SA NOIRE lata 4 packs de 6 de 473 cc CART |
| 533 | 22614 | STELLA ARTOIS CAN 2X10 269 | STELLA ARTOIS lata 2 packs de 10 269 cc | STELLA ARTOIS lata 2 packs de 10 de 269 cc |
| 541 | 2284 | QUILMES STOUT NEGRA X12 1000RE | QUILMES STOUT NEGRA pack de 12 1 litro retornable | QUILMES STOUT NEGRA pack de 12 de 1 litro retornable |
| 543 | 2291 | QUILMES BOCK NEGRA X12 1000RET | QUILMES BOCK NEGRA pack de 12 1 litro retornable | QUILMES BOCK NEGRA pack de 12 de 1 litro retornable |
| 547 | 22992 | PATAGONIA SOLCITRA CAN 4X6 473 | PATAGONIA SOLCITRA lata 4 packs de 6 473 cc | PATAGONIA SOLCITRA lata 4 packs de 6 de 473 cc |
| 562 | 24011 | ANDES ORIGEN ROJA CAN 2X10 269 | ANDES ORIGEN ROJA lata 2 packs de 10 269 cc | ANDES ORIGEN ROJA lata 2 packs de 10 de 269 cc |
| 567 | 2410 | ECO ANDES AGUAS/G * X6 PET2000 | ECO ANDES aguas con gas pack de 6 botella de 2 litros | ECO ANDES AGUAS/G pack de 6 botella de 2 litros |
| 571 | 2416 | ECO ANDES AGUAS/G * X6 PET2000 | ECO ANDES aguas con gas pack de 6 botella de 2 litros | ECO ANDES AGUAS/G pack de 6 botella de 2 litros |
| 575 | 2428 | ECO ANDES AGUAC/G * X6 PET1500 | ECO ANDES aguas con gas pack de 6 botella de 1,5 litros | ECO ANDES AGUAC/G pack de 6 botella de 1,5 litros |
| 577 | 2430 | ECO ANDES AGUAS/G * X6 PET1500 | ECO ANDES aguas con gas pack de 6 botella de 1,5 litros | ECO ANDES AGUAS/G pack de 6 botella de 1,5 litros |
| 578 | 2433 | ECO ANDES AGUAS/G * X6 PET1500 | ECO ANDES aguas con gas pack de 6 botella de 1,5 litros | ECO ANDES AGUAS/G pack de 6 botella de 1,5 litros |
| 580 | 2436 | ECO ANDES AGUAS/G * X6 PET1500 | ECO ANDES aguas con gas pack de 6 botella de 1,5 litros | ECO ANDES AGUAS/G pack de 6 botella de 1,5 litros |
| 585 | 2439 | ECO ANDES AGUAS/G * X6 PET1500 | ECO ANDES aguas con gas pack de 6 botella de 1,5 litros | ECO ANDES AGUAS/G pack de 6 botella de 1,5 litros |
| 586 | 2440 | ECO ANDES AGUAC/G * X6 PET1500 | ECO ANDES aguas con gas pack de 6 botella de 1,5 litros | ECO ANDES AGUAC/G pack de 6 botella de 1,5 litros |
| 587 | 2446 | ECO ANDES AGUAC/G * X6 PET1500 | ECO ANDES aguas con gas pack de 6 botella de 1,5 litros | ECO ANDES AGUAC/G pack de 6 botella de 1,5 litros |
| 588 | 2449 | ECO ANDES AGUAS/G * X6 PET2000 | ECO ANDES aguas con gas pack de 6 botella de 2 litros | ECO ANDES AGUAS/G pack de 6 botella de 2 litros |
| 589 | 2450 | ECO ANDES AGUAS/G * X12 PET 50 | ECO ANDES aguas con gas pack de 12 botella 50 | ECO ANDES AGUAS/G pack de 12 botella de 50 cc |
| 590 | 2452 | ECO ANDES AGUAS/G * X12 PET 50 | ECO ANDES aguas con gas pack de 12 botella 50 | ECO ANDES AGUAS/G pack de 12 botella de 50 cc |
| 593 | 2458 | ECO ANDES AGUAS/G * X12 PET 50 | ECO ANDES aguas con gas pack de 12 botella 50 | ECO ANDES AGUAS/G pack de 12 botella de 50 cc |
| 595 | 2462 | ECO ANDES AGUAC/G * X12 PET 50 | ECO ANDES aguas con gas pack de 12 botella 50 | ECO ANDES AGUAC/G pack de 12 botella de 50 cc |
| 598 | 24691 | CHALICE 330ML STELLA ARTOIS | CHALICE 330 cc STELLA ARTOIS | CHALICE 330ML STELLA ARTOIS |
| 620 | 2498 | ECO ANDES AGUAC/G * X12 PET 50 | ECO ANDES aguas con gas pack de 12 botella 50 | ECO ANDES AGUAC/G pack de 12 botella de 50 cc |
| 621 | 2499 | ECO ANDES AGUAS/G * X6 PET2000 | ECO ANDES aguas con gas pack de 6 botella de 2 litros | ECO ANDES AGUAS/G pack de 6 botella de 2 litros |
| 663 | 25538 | PDT TONICA 0 KCAL PET X6 1.5L | Paso de los Toros TONICA 0 KCAL botella pack de 6 1,5 litros | Paso de los Toros TONICA 0 calorías botella pack de 6 de 1,5 litros |
| 699 | 25981 | GATORADE COOL BLUE PET X6 1250 | GATORADE COOL BLUE botella pack de 6 de 1,25 litros | GATORADE COOL BLUE botella pack de 6 1250 |
| 702 | 26206 | PATAGONIA TRAVESIA CAN 4X6 410 | PATAGONIA TRAVESIA lata 4 packs de 6 410 cc | PATAGONIA TRAVESIA lata 4 packs de 6 de 410 cc |
| 705 | 26412 | AWAFRUT NAR-DUR BC PET X6 1500 | AWAFRUT naranja-durazno BC botella pack de 6 de 1,5 litros | AWAFRUT naranja-durazno BC botella pack de 6 1500 |
| 752 | 27678 | PATAGONIA BOHEMIAN RET X12 100 | PATAGONIA BOHEMIAN retornable pack de 12 de 100 cc | PATAGONIA BOHEMIAN retornable pack de 12 100 |
| 762 | 28242 | BRAHMA CARNAVAL 2023 X24 473CC | BRAHMA CARNAVAL 2023 packs de 24 de 473 cc | BRAHMA CARNAVAL 2023 pack de 24 de 473 cc |
| 764 | 28251 | PRINGLES ORIGINAL X14 124GR | PRINGLES ORIGINAL pack de 14 de 124 cc gramos | PRINGLES ORIGINAL pack de 14 124 gramos |
| 766 | 28253 | PRINGLES QUESO X14 124GR | PRINGLES QUESO pack de 14 de 124 cc gramos | PRINGLES QUESO pack de 14 124 gramos |
| 768 | 28315 | STELLA ARTOIS 0.0% CAN 4X6 473 | STELLA ARTOIS cero% lata 4 packs de 6 473 cc | STELLA ARTOIS cero% lata 4 packs de 6 de 473 cc |
| 773 | 2852 | STELLA ARTOIS - 4X6 330 OW | STELLA ARTOIS 4 packs de 6 330 cc | STELLA ARTOIS 4 packs de 6 de 330 cc |
| 775 | 2854 | STELLA ARTOIS - X12 1000RET | STELLA ARTOIS pack de 12 1 litro retornable | STELLA ARTOIS pack de 12 de 1 litro retornable |
| 794 | 28842 | PATAGONIA IPA 24.7 RET X12 100 | PATAGONIA IPA 24.7 retornable pack de 12 de 100 cc | PATAGONIA IPA 24.7 retornable pack de 12 100 |
| 800 | 29021 | PEPAS FB TEREPIN X14 300GR | PEPAS FB TEREPIN pack de 14 de 300 cc gramos | PEPAS FB TEREPIN pack de 14 300 gramos |
| 814 | 2923 | NESTLE PV AGUAS/G * X6 PET1500 | NESTLE PV aguas con gas pack de 6 botella de 1,5 litros | NESTLE PV AGUAS/G pack de 6 botella de 1,5 litros |
| 819 | 29396 | GOOSE ISLAND LAGER CAN 4X6 473 | GOOSE ISLAND LAGER lata 4 packs de 6 473 cc | GOOSE ISLAND LAGER lata 4 packs de 6 de 473 cc |
| 842 | 29650 | ANDES ORIGEN RUBIA CAN 4X4 710 | ANDES ORIGEN RUBIA lata 4 packs de 4 710 cc | ANDES ORIGEN RUBIA lata 4 packs de 4 de 710 cc |
| 844 | 29672 | MIX MAGDALENAS POZO X10 200GR | MIX MAGDALENAS POZO pack de 10 de 200 cc gramos | MIX MAGDALENAS POZO pack de 10 200 gramos |
| 849 | 29736 | VAINILLAS POZO X14 148GR | VAINILLAS POZO pack de 14 de 148 cc gramos | VAINILLAS POZO pack de 14 148 gramos |
| 850 | 29740 | QUILMES 1890 RET X12 1L SMK | QUILMES 1890 retornable pack de 12 1 litro SMK | QUILMES 1890 retornable pack de 12 de 1 litro SMK |
| 859 | 29802 | ROCKSTAR MIX FRUIT PET X6 1500 | ROCKSTAR MIX FRUIT botella pack de 6 de 1,5 litros | ROCKSTAR MIX FRUIT botella pack de 6 1500 |
| 865 | 29818 | H2OH STILL LIMON PET X6 1.500L | H2OH STILL LIMON botella pack de 6 1,500 litros | H2OH STILL LIMON botella pack de 6 de 1,5 litros |
| 923 | 30789 | PEPSI BLACK PET X8 2.000CC 202 | PEPSI BLACK botella pack de 8 2.000 cc 202 cc | PEPSI BLACK botella pack de 8 de 2.000 cc 202 cc |
| 924 | 30790 | PEPSI BLACK PET X6 1.500CC 202 | PEPSI BLACK botella pack de 6 1.500 cc 202 cc | PEPSI BLACK botella pack de 6 de 1.500 cc 202 cc |
| 927 | 30795 | PEPSI 70KCAL PET X8 2.000CC RE | PEPSI 70 calorías botella pack de 8 2.000 cc RE | PEPSI 70 calorías botella pack de 8 de 2.000 cc RE |
| 931 | 30843 | H2OH STILL LIMON PET X6 1.500L | H2OH STILL LIMON botella pack de 6 1,500 litros | H2OH STILL LIMON botella pack de 6 de 1,5 litros |
| 945 | 30986 | OBLEA VAINILLA ZUPAY X12 100GR | OBLEA VAINILLA ZUPAY pack de 12 de 100 cc gramos | OBLEA VAINILLA ZUPAY pack de 12 100 gramos |
| 946 | 30987 | OBLEA FRUTILLA ZUPAY X12 100GR | OBLEA FRUTILLA ZUPAY pack de 12 de 100 cc gramos | OBLEA FRUTILLA ZUPAY pack de 12 100 gramos |
| 984 | 31602 | H2OH STILL MANZANA PET X8 2000 | H2OH STILL MANZANA botella pack de 8 de 2 litros | H2OH STILL MANZANA botella pack de 8 2000 |
| 987 | 31747 | JAGERMEISTER X6 700ML | JAGERMEISTER pack de 6 de 700 cc | JAGERMEISTER pack de 6 700ML |
| 988 | 31748 | QUILMES CLASICA RET X12 1L BAJ | QUILMES CLASICA retornable pack de 12 1 litro BAJ | QUILMES CLASICA retornable pack de 12 de 1 litro BAJ |
| 998 | 31978 | POLENTA MOLINOS ALA X10 500GR | POLENTA MOLINOS ALA pack de 10 de 500 cc gramos | POLENTA MOLINOS ALA pack de 10 500 gramos |
| 1008 | 32120 | BISCUITS SORIANO X16 125GR | BISCUITS SORIANO pack de 16 de 125 cc gramos | BISCUITS SORIANO pack de 16 125 gramos |
| 1031 | 32492 | H2OH S/GAS NARANJA PET X6 1500 | H2OH sin GAS NARANJA botella pack de 6 de 1,5 litros | H2OH sin GAS NARANJA botella pack de 6 1500 |
| 1033 | 32537 | GLACIAR PET X6 2L | GLACIAR botella pack de 6 2 litros | GLACIAR botella pack de 6 de 2 litros |
| 1035 | 32707 | GLACIAR PET X2 6.400CC | GLACIAR botella pack de 2 6.400 cc | GLACIAR botella pack de 2 de 6.400 cc |
| 1040 | 33387 | JAGERMEISTER RETRO X6 700ML | JAGERMEISTER RETRO pack de 6 de 700 cc | JAGERMEISTER RETRO pack de 6 700ML |
| 1085 | 42108 | BALTICA - X12 1000RET | BALTICA pack de 12 1 litro retornable | BALTICA pack de 12 de 1 litro retornable |
| 1091 | 46629 | QUILMES CLASICA RET X12 1L MUN | QUILMES CLASICA retornable pack de 12 1 litro MUN | QUILMES CLASICA retornable pack de 12 de 1 litro MUN |
| 1121 | 5098 | BOT MED 350X24 | BOT MED 350 cc packs de 24 | BOT MED 350 packs de 24 |
| 1122 | 5099 | Q MED 350X24 VD | Q MED 350 cc packs de 24 VD | Q MED 350 packs de 24 VD |
| 1144 | 5547 | PEPSI COLA PET X08 2.45L | PEPSI COLA botella pack de 08 2,45 litros | PEPSI COLA botella pack de 08 de 2,45 litros |
| 1147 | 5615 | MIX QBAJO0/1890 X12 1000RET | MIX QBAJO0/1890 packs de 12 1 litro retornable | MIX QBAJO0/1890 pack de 12 de 1 litro retornable |
| 1152 | 5741 | IGUANA SUMMER - X12 1000RET | IGUANA SUMMER pack de 12 1 litro retornable | IGUANA SUMMER pack de 12 de 1 litro retornable |
| 1170 | 5954 | NESTLE PV AGUA * X6 2250 | NESTLE PV AGUA pack de 6 de 2,25 litros | NESTLE PV AGUA pack de 6 2250 |
| 1193 | 671 | GLACIAR AGUAS/G * X12 PET 500# | GLACIAR aguas con gas pack de 12 botella de 500 cc | GLACIAR AGUAS/G pack de 12 botella de 500 cc |
| 1200 | 7017 | LIEBER - X12 1000RET | LIEBER pack de 12 1 litro retornable | LIEBER pack de 12 de 1 litro retornable |
| 1202 | 7026 | QUILMES - X12 1000RET | QUILMES pack de 12 1 litro retornable | QUILMES pack de 12 de 1 litro retornable |
| 1203 | 7028 | QUILMES BAJO0 - X12 1000RET | QUILMES BAJO0 pack de 12 1 litro retornable | QUILMES BAJO0 pack de 12 de 1 litro retornable |
| 1204 | 7030 | QUILMES STOUT NEGRA X12 1000RE | QUILMES STOUT NEGRA pack de 12 1 litro retornable | QUILMES STOUT NEGRA pack de 12 de 1 litro retornable |
| 1205 | 7031 | QUILMES BOCK NEGRA X12 1000RET | QUILMES BOCK NEGRA pack de 12 1 litro retornable | QUILMES BOCK NEGRA pack de 12 de 1 litro retornable |
| 1206 | 7032 | LIEBER - X12 1000RET | LIEBER pack de 12 1 litro retornable | LIEBER pack de 12 de 1 litro retornable |
| 1207 | 7035 | BRAHMA - X12 1000RET | BRAHMA pack de 12 1 litro retornable | BRAHMA pack de 12 de 1 litro retornable |
| 1208 | 7038 | BRAHMA - X12 1000RET# | BRAHMA pack de 12 1 litro retornable | BRAHMA pack de 12 de 1 litro retornable |
| 1213 | 7097 | QUILMES NIGHT - 4X6 355 OW | QUILMES NIGHT 4 packs de 6 355 cc | QUILMES NIGHT 4 packs de 6 de 355 cc |
| 1215 | 7108 | QUILMES 1890 - X12 1000RET | QUILMES 1890 pack de 12 1 litro retornable | QUILMES 1890 pack de 12 de 1 litro retornable |
| 1218 | 7116 | QUILMES 1890 - X12 1000RET | QUILMES 1890 pack de 12 1 litro retornable | QUILMES 1890 pack de 12 de 1 litro retornable |
| 1219 | 7125 | STELLA NOIRE NEGRA 4X6 330 OW | STELLA NOIRE NEGRA 4 packs de 6 330 cc | STELLA NOIRE NEGRA 4 packs de 6 de 330 cc |
| 1220 | 7126 | STELLA NOIRE NEGRA X12 1000RET | STELLA NOIRE NEGRA pack de 12 1 litro retornable | STELLA NOIRE NEGRA pack de 12 de 1 litro retornable |
| 1226 | 7176 | QUILMES 1890 - 4X6 340 OW | QUILMES 1890 4 packs de 6 340 cc | QUILMES 1890 4 packs de 6 de 340 cc |
| 1229 | 7189 | QUILMES - 4X6 340 OW | QUILMES 4 packs de 6 340 cc | QUILMES 4 packs de 6 de 340 cc |
| 1230 | 7193 | QUILMES NIGHT - X6 1000RET | QUILMES NIGHT pack de 6 1 litro retornable | QUILMES NIGHT pack de 6 de 1 litro retornable |
| 1237 | 742 | GATORADE FRU TRO * X6 750 | GATORADE FRU TRO pack de 6 de 750 cc | GATORADE frutas tropicales pack de 6 de 750 cc |
| 1246 | 747 | NPV AWAFR NRJ DUR * X12 PET 50 | Nestlé Pureza Vital AWAFR NRJ durazno pack de 12 botella 50 | Nestlé Pureza Vital AWAFR NRJ durazno pack de 12 botella de 50 cc |
| 1263 | 753 | NPV AWAFR MANZANA * X12 PET 50 | Nestlé Pureza Vital AWAFR MANZANA pack de 12 botella 50 | Nestlé Pureza Vital AWAFR MANZANA pack de 12 botella de 50 cc |
| 1269 | 7615 | BRAHMA - X12 1000RET | BRAHMA pack de 12 1 litro retornable | BRAHMA pack de 12 de 1 litro retornable |
| 1280 | 76411 | MIKEÂ´S HARD LEMONADE  6X4 355 | MIKEÂ´S HARD LEMONADE 6 packs de 4 355 cc | MIKEÂ´S HARD LEMONADE 6 packs de 4 de 355 cc |
| 1285 | 76479 | CACHAMATE AMARILLA X12 500GR | CACHAMATE AMARILLA pack de 12 de 500 cc gramos | CACHAMATE AMARILLA pack de 12 500 gramos |
| 1286 | 76481 | CACHAMATE ROSA X12 500GR | CACHAMATE ROSA pack de 12 de 500 cc gramos | CACHAMATE ROSA pack de 12 500 gramos |
| 1289 | 76503 | LECHE ENTERA LARGA VIDA X12 1L | LECHE ENTERA LARGA VIDA pack de 12 1 litro | LECHE ENTERA LARGA VIDA pack de 12 de 1 litro |
| 1297 | 767 | NPV AWAFR LIMONAD * X12 PET 50 | Nestlé Pureza Vital AWAFR LIMONAD pack de 12 botella 50 | Nestlé Pureza Vital AWAFR LIMONAD pack de 12 botella de 50 cc |
| 1306 | 77697 | VAINILLAS POZO X24 160 GR | VAINILLAS POZO pack de 24 de 160 cc gramos | VAINILLAS POZO pack de 24 160 gramos |
| 1307 | 77698 | VAINILLAS POZO X12 296 GR | VAINILLAS POZO pack de 12 de 296 cc gramos | VAINILLAS POZO pack de 12 296 gramos |
| 1310 | 77710 | MAGDALENA CLASICA X10 200GR | MAGDALENA CLASICA pack de 10 de 200 cc gramos | MAGDALENA CLASICA pack de 10 200 gramos |
| 1312 | 77726 | PEPAS MEMBRILLO X24 200 GR | PEPAS MEMBRILLO pack de 24 de 200 cc gramos | PEPAS MEMBRILLO pack de 24 200 gramos |
| 1313 | 77727 | PEPAS MEMBRILLO X14 400 GR | PEPAS MEMBRILLO pack de 14 de 400 cc gramos | PEPAS MEMBRILLO pack de 14 400 gramos |
| 1317 | 77784 | LECHE ENTERA TRES NINAS X12 1L | LECHE ENTERA TRES NINAS pack de 12 1 litro | LECHE ENTERA TRES NINAS pack de 12 de 1 litro |
| 1321 | 77820 | STA TWOPACK ANDES X2 200GR | Stella dos packs ANDES pack de 2 de 200 cc gramos | Stella dos packs ANDES pack de 2 200 gramos |
| 1322 | 77821 | STA TWOPACK BUD X2 200GR | Stella dos packs Budweiser pack de 2 de 200 cc gramos | Stella dos packs Budweiser pack de 2 200 gramos |
| 1328 | 77832 | YERBA MATE MAÑANITA X10 500GR | YERBA MATE MAÑANITA pack de 10 de 500 cc gramos | YERBA MATE MAÑANITA pack de 10 500 gramos |
| 1329 | 77833 | YERBA MATE LA MERCED CAMPO X 6 | YERBA MATE LA MERCED CAMPO pack de 6 | YERBA MATE LA MERCED CAMPO X 6 |
| 1346 | 77898 | FRAPERA CORONA X10 400GR | FRAPERA CORONA pack de 10 de 400 cc gramos | FRAPERA CORONA pack de 10 400 gramos |
| 1347 | 77914 | TRIPACK VASOS TEMPLE X3 300ML | TRIPACK VASOS TEMPLE pack de 3 de 300 cc | TRIPACK VASOS TEMPLE pack de 3 300ML |
| 1358 | 77950 | ACEITE REFINADO FRITOMAC X4 5L | ACEITE REFINADO FRITOMAC pack de 4 5 litros | ACEITE REFINADO FRITOMAC pack de 4 de 5 litros |
| 1382 | 78121 | PITUSAS CHOCOLATE X30 160GR | PITUSAS CHOCOLATE pack de 30 de 160 cc gramos | PITUSAS CHOCOLATE pack de 30 160 gramos |
| 1383 | 78128 | PITUSAS VAINILLA X30 160GR | PITUSAS VAINILLA pack de 30 de 160 cc gramos | PITUSAS VAINILLA pack de 30 160 gramos |
| 1385 | 78142 | ARROZ LF MOLINOS ALA X10 500GR | ARROZ LF MOLINOS ALA pack de 10 de 500 cc gramos | ARROZ LF MOLINOS ALA pack de 10 500 gramos |
| 1396 | 78215 | CACAO EN POLVO TODDY X12 180GR | CACAO EN POLVO TODDY pack de 12 de 180 cc gramos | CACAO EN POLVO TODDY pack de 12 180 gramos |
| 1400 | 78233 | YERBA MATE CACHAMATE X12 500GR | YERBA MATE CACHAMATE pack de 12 de 500 cc gramos | YERBA MATE CACHAMATE pack de 12 500 gramos |
| 1401 | 78243 | STA FRAPERA ANDES X 20 | Stella FRAPERA ANDES pack de 20 | Stella FRAPERA ANDES X 20 |
| 1409 | 78279 | PAN RALLADO MORIXE X12 500GR | PAN RALLADO MORIXE pack de 12 de 500 cc gramos | PAN RALLADO MORIXE pack de 12 500 gramos |
| 1410 | 78280 | REBOZADOR MORIXE X12 500GR | REBOZADOR MORIXE pack de 12 de 500 cc gramos | REBOZADOR MORIXE pack de 12 500 gramos |
| 1414 | 7897 | AFICHETA SA 30 X 20 LATA 2017 | AFICHETA SA 30 packs de 20 LATA 2017 | AFICHETA SA 30 X 20 LATA 2017 |
| 1415 | 7898 | AFICHETA SA 24 X 10 LATA 2017 | AFICHETA SA 24 packs de 10 LATA 2017 | AFICHETA SA 24 X 10 LATA 2017 |
| 1417 | 7924 | BRAHMA - X12 1000RET# | BRAHMA pack de 12 1 litro retornable | BRAHMA pack de 12 de 1 litro retornable |
| 1429 | 8064 | GLACIAR AGUAS/G * X6 PET1500# | GLACIAR aguas con gas pack de 6 botella de 1,5 litros | GLACIAR AGUAS/G pack de 6 botella de 1,5 litros |
| 1450 | 8104 | ECO ANDES AGUAS/G * X6 PET1000 | ECO ANDES aguas con gas pack de 6 botella de 1 litro | ECO ANDES AGUAS/G pack de 6 botella de 1 litro |
| 1461 | 8126 | NESTLE PV AGUA ME * X12 PET 50 | NESTLE PV AGUA ME pack de 12 botella 50 | NESTLE PV AGUA ME pack de 12 botella de 50 cc |
| 1462 | 8127 | NESTLE PV AGUAS/G * X6 PET1500 | NESTLE PV aguas con gas pack de 6 botella de 1,5 litros | NESTLE PV AGUAS/G pack de 6 botella de 1,5 litros |
| 1516 | 82937 | EQUIPO ELEC. C-2500 CORNELIUS | EQUIPO ELEC. C-2,5 litros CORNELIUS | EQUIPO ELEC. C-2500 CORNELIUS |
| 1518 | 82941 | EQUIPO ELEC. V-200 COSTERO USA | EQUIPO ELEC. V-200 cc COSTERO USA | EQUIPO ELEC. V-200 COSTERO USA |
| 1520 | 82949 | EQUIPO ELEC. AVANT V-200 CORNE | EQUIPO ELEC. AVANT V-200 cc CORNE | EQUIPO ELEC. AVANT V-200 CORNE |
| 1581 | 870 | GLACIAR AGUAC/G * X6 PET1500 | GLACIAR aguas con gas pack de 6 botella de 1,5 litros | GLACIAR AGUAC/G pack de 6 botella de 1,5 litros |
| 1582 | 871 | GLACIAR AGUAS/G * X6 PET1500# | GLACIAR aguas con gas pack de 6 botella de 1,5 litros | GLACIAR AGUAS/G pack de 6 botella de 1,5 litros |
| 1583 | 873 | GLACIAR AGUAS/G * X12 PET 500# | GLACIAR aguas con gas pack de 12 botella de 500 cc | GLACIAR AGUAS/G pack de 12 botella de 500 cc |
| 1585 | 898 | GLACIAR AGUAS/G * X6 PET2000# | GLACIAR aguas con gas pack de 6 botella de 2 litros | GLACIAR AGUAS/G pack de 6 botella de 2 litros |
| 1586 | 899 | GLACIAR AGUAS/G * X6 PET2000# | GLACIAR aguas con gas pack de 6 botella de 2 litros | GLACIAR AGUAS/G pack de 6 botella de 2 litros |
| 1729 | 993 | BUDWEISER LATA 473X24 | BUDWEISER LATA 473 cc packs de 24 | BUDWEISER LATA 473 packs de 24 |
