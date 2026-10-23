# Resultados y procedencia de OCR

## Alcance de las referencias

El corpus confirmado contiene56 unidades:24 renglones de cuatro páginas de tomos
y32 unidades de cuatro páginas de índices. Las75 referencias históricas siguen
pendientes de confirmación. No sumar sus resultados como una única precisión
del sistema. Las páginas conocidas y reutilizadas son desarrollo, no validación
independiente. Anotar regiones no verifica automáticamente su transcripción.

## Comparaciones realizadas

| Familia | Alcance y conclusión |
| --- | --- |
| Comprobación confirmada | 242 tareas; muestra efectos distintos de original, grises y realces en tomos e índices. |
| Diagnóstico de recorte y OCR | 378 tareas sobre18 renglones; aísla PSM, binarización, escala, alineación y contexto por comparación. |
| Kraken Sandra | 39 recortes con McCATMuS; en cada comparación el CER fue mayor que Tesseract sobre esas mismas entradas. |
| Kraken dos modelos | 172 recortes por modelo, con Lenin/Sandra, original/CLAHE y escalas0,5/1. No proporcionó una alternativa mejor a los controles claros de Tesseract. |
| Detector→Tesseract en Lenin | Diez páginas,157 invocaciones de cuerpo. Cinco páginas con150 posiciones físicas:139 con texto; otras cinco con11 regiones sin numeración:10 con texto. Esto mide presencia de salida, no exactitud. |
| Sauvola protegido v106 | 24OCR, doce entradas, con controles Otsu reproducidos. Mejora agregada Sergio3 y una regresión local. |
| Escala v107 | Doce OCR0,55 sobre las mismas cajas: CER igual y WER peor en Sergio3. No adoptada. |
| Transferencia v108 | 24OCR sobre cajas humanas de Sergio1/Salvador1 y render global. Mejora parcial de Sergio1; no sustituye su mejor protocolo histórico confirmado. |
| Línea cruda v109 | Doce OCR cambiando solo a PSM 13. Regresiones graves; descartada. |

No agregar el número de tareas como si fueran páginas o ejemplos independientes.
Varias comparaciones reutilizan los mismos textos y cambian la preparación.

## Índices: exactitud de campos, no solo CER agregado

28 celdas y4períodos confirmados. Misma celda entre variantes; original/grises
a0,4, realces a0,55 según protocolo. Las diferencias incluyen escala.

| Tratamiento | CER celdas | Celdas exactas /28 | CER períodos |
| --- | ---: | ---: | ---: |
| Original | 13,45 % | 10 | 1,28 % |
| Grises | 13,23 % | 10 | 1,28 % |
| CLAHE histórico | 31,84 % | 3 | 1,65 % |
| Engrosado vertical | 34,98 % | 3 | 0,91 % |

Exactitud tras normalización técnica NFC/espacios, conservando caja, acentos
y puntuación. No corregir nombres, fechas o números ni inferir ausencia de
instrumentos cuando el OCR falla. Se requiere una declaración explícita.

## Carnet: localizar, encuadrar y leer son problemas distintos

La receta de contexto anterior bloqueaba las cinco lecturas de Salvador pese
a existir candidatos. Al resolver contexto geométrico sin exigir leer otros
campos, se autorizaron los cinco. Las cajas estrechas cortaban dígitos: el primer
ensayo solo estructuró uno de cinco carnets. Un margen fijo horizontal del50 %
de altura de caja y vertical del15 %, limitado al sello padre, produjo cinco
lecturas literales `C. 26624` con PSM 7. No se expandió buscando un valor esperado.

Los tres sellos borrosos de Sandra seguían generando candidatos; no hay un
selector de legibilidad/abstención validado. Su falta de OCR en ese ensayo se
debió al alcance elegido, no a una capacidad demostrada de rechazar lo ilegible.
Sellos DNN y traspasos no se confunden con carnet positivo por falta de lectura.

## Guardia de entrada blanca

Un control completamente blanco produjo `o` con Tesseract. La guardia v101
comprueba la entrada real después del recorte y escalado: todos los valores255
implican no invocar el motor, texto publicable nulo y alerta técnica. Un píxel254
ya impide clasificarla como blanco exacto. No se filtra por palabras esperadas.

Regresión de81 artefactos:80 no blancos conservan su lectura;1 blanco bloqueado
para publicación, manteniendo el literal histórico como evidencia. El control
nunca había sido contenido público: no se afirma haber corregido un JSON que
incluyera esa `o`. La guardia no detecta todos los errores sobre ruido o tinta.

## Motores no ejecutados o pendientes

PyLaia/Calamari: investigados, sin modelo local verificado ni métricas propias.
PaddleOCR: bibliotecas inventariadas, sin pesos de reconocimiento español
verificados. PP-DocLayout-L es detector de maquetación, no reconocedor OCR.
Kraken7.1.1 se ejecutó históricamente en WSL; el último inventario no pudo
acceder a ese entorno. No se afirma que ahora esté disponible ni se repitió.

## Identificadores de evidencia

- Kraken piloto: `20261006T002505_88f93499`.
- McCATMuS: `20261006T003755_2a5bc9e8`.
- CATMuS Print: `20261006T012332_c3acd718`.
- Referencias/comprobación: `20261019T044053_27a8af58`.
- Diagnóstico: `20261019T050048_893391e2`.
- Flujo Lenin: v68; contexto/margen de carnet: v77/v78.
- Guardia blanca: v101; binarización/escala/transferencia/línea cruda: v106–v109.

La entrega no incluye documentos, recortes o transcripciones notariales.
Las tablas resumen resultados existentes; no se ejecutó OCR nuevo al redactarla.
