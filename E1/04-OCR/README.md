# 04 — Reconocimiento de texto

**Hasta el momento, Tesseract es el motor de referencia de E1.** Ha producido
los mejores resultados disponibles en los controles comparados con Kraken,
pero la configuración adecuada cambia según el recorte y su deterioro.
No hay una receta única validada para todos los tomos e índices.

Esta etapa transcribe texto impreso o mecanografiado de las regiones permitidas.
Firmas y manuscritos se detectan sin transcribir. De los sellos se intenta leer
únicamente el carnet del notario, no su contenido completo.

## Qué se ha probado

- Tesseract con español: línea individual (PSM 7), bloque de varias líneas
  (PSM 6) y diagnóstico de línea cruda (PSM 13).
- Binarización interna Otsu frente a Sauvola, manteniendo los mismos recortes.
- Variaciones de escala, margen, contexto y alineación para separar problemas
  de imagen, recorte y reconocimiento.
- Kraken con los modelos McCATMuS y CATMuS Print Fondue Large, sobre recortes
  compartidos con Tesseract.
- Lectura de renglones de tomos, celdas/períodos de índices y carnet de sellos.
- Flujo detector v32 → regiones protegidas → Tesseract, conservando omisiones
  y lecturas parciales.
- Bloqueo de OCR cuando la entrada es completamente blanca.

PyLaia y Calamari se investigaron, pero no se ejecutaron. PaddleOCR tiene
bibliotecas instaladas, sin un reconocedor español local verificado para esta
comparación. DocRes y pero-enhance corresponden al preprocesamiento, no son
resultados de motores OCR de esta etapa.

## ¿Qué ha dado mejores resultados?

### Renglones con referencias confirmadas

Comparaciones sobre seis renglones por página con cajas humanas. CER mide
errores de caracteres y WER errores de palabras; menor porcentaje es mejor.

| Caso | Configuración destacada | CER | WER |
| --- | --- | ---: | ---: |
| Sergio1 | CLAHE con suavizado/gamma, escala 0,55 y PSM 6 | 14,99 % | 50,75 % |
| Sergio3 | Original, escala 0,4, PSM 7 y Sauvola interno | 0,13 % | 0,85 % |
| Salvador4 | Original, escala 0,4, PSM 7 y Otsu | 0 % | 0 % |

En Sergio1, cambiar solo PSM 7→6 sobre el realce reduce CER 17,23→14,99 %.
En Sergio3, cambiar solo Otsu→Sauvola sobre original reduce CER 10,30→0,13 %.
Estos resultados no verifican páginas completas ni una selección automática
de configuración. No se escoge por renglón la salida que más se parezca a la referencia.

### Lectura sobre recortes del flujo protegido

Al conservar las mismas imágenes y cajas, Sauvola redujo CER 2,11→0,40 % y
WER 12,82→2,56 % en seis renglones de Sergio3. Salvador4 conservó CER/WER 0 %.
Cinco renglones de Sergio mejoraron, pero uno pasó de cero a un error.

El0,40 % de estos recortes no sustituye al0,13 % de cajas humanas: cambia la
entrada. Aumentar después la escala 0,40→0,55 no mejoró CER y empeoró WER.
En otra prueba con cajas humanas y remuestreo global, Sauvola mejoró Sergio1
de CER 42,95 % a28,64 %, pero siguió por debajo del mejor protocolo anterior.

### Índices y campos

Se evaluaron28 celdas y4 bloques de período confirmados de cuatro páginas del
índice de Lenin, con PSM 6. Original obtuvo CER 13,45 % en celdas; grises13,23 %.
Ambos recuperaron10de28 celdas exactas. El realce fuerte cayó a3de28.
Una buena lectura del período no demuestra que los campos del registro estén bien.

### Carnet del notario

Con localización automática y un margen geométrico fijo, Tesseract spa/PSM 7
leyó literalmente `C. 26624` en cinco páginas claras de Salvador. Es un avance
funcional sobre páginas usadas durante el ajuste, no una medición independiente
de exactitud ni una solución validada para sellos borrosos. No se completaron
dígitos por contexto ni se copió el valor de una plantilla.

## Comparación de motores

Controles históricos con referencias pendientes de confirmación, compartiendo
las mismas entradas. Kraken se ejecutó como reconocimiento de una línea sin
segmentación; falta comprobar si ese encuadre es adecuado para sus modelos.

| Entrada | CER Tesseract | McCATMuS | CATMuS Print |
| --- | ---: | ---: | ---: |
| Lenin original, escala 0,5 | 0,17 % | 43,93 % | 35,23 % |
| Sandra con CLAHE, escala 0,5 | 30,69 % | 69,31 % | 72,61 % |
| Sandra original, escala 1 | 94,03 % | 86,71 % | 88,57 % |

Kraken supera a Tesseract en el último control, pero los tres resultados son
deficientes y no superan las mejores configuraciones disponibles de Sandra.
No demuestra que un motor sea peor en general. La comparación de Kraken con
extracción de baseline sigue pendiente, igual que comprobar su entorno actual.

## Qué se descartó o sigue fallando

- **PSM 13:** produjo texto en entradas antes sin lectura, pero con errores
  mayores. En el último ensayo, Sergio1 pasó de CER 28,64 % a92,62 % y Salvador1
  de1,54 % a60,31 %. Más texto no equivale a mejor transcripción.
- **Sauvola universal:** mejora Sergio3, pero empeora otras entradas. Sobre
  Salvador4 realzado subió CER 69,38 % a86,05 %.
- **Más escala o contexto por defecto:** puede introducir fragmentos vecinos,
  alterar detalles pequeños o empeorar puntuación y espacios.
- **OCR de toda región detectada:** deja pasar manuscritos omitidos por el
  detector y puede perder impresión por exclusiones. No está validado como
  reconocimiento automático completo de la página.
- **Confianza como garantía:** no demuestra exactitud ni permite corregir valores.

## ¿Qué se conserva por ahora?

**Tesseract con español, PSM 7 para líneas y PSM 6 para bloques/celdas como bases
de comparación; Sauvola como candidato dirigido, conservando Otsu.** Guardar
texto literal, configuración, coordenadas, confianza y estados técnicos.
Transcribir solo impresión visible, sin corregir palabras o reconstruir lo oculto.

La guardia de entrada totalmente blanca evita invocar Tesseract y publicar
texto espurio sobre esos PNG. No declara que la página fuente esté vacía.
Se distinguen lectura parcial, no reconocido, entrada blanca y error de ejecución.

Pendiente ampliar la evaluación confirmada, medir campos completos, controlar
sellos borrosos y resolver interferencias de segmentación antes de dar el flujo
por terminado. Esta entrega es documental; el ejecutor autónomo queda pendiente.

[Comparaciones y evidencia](RESULTADOS.md) · [Configuraciones de referencia](CONFIGURACIONES.md).
