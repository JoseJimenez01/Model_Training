# 02 — Preprocesamiento de imágenes

Se han comparado tratamientos para mejorar la lectura de páginas escaneadas.
**Hasta el momento conviene conservar el original en páginas claras, aplicar
CLAHE con suavizado y gamma en ciertos casos difíciles, y usar engrosado
vertical leve en el caso de tinta tenue.** No hay un tratamiento
que mejore todos los documentos de manera general hasta ahora.

Se comparan errores de caracteres (CER) y palabras (WER) contra transcripciones
de referencia. Un porcentaje menor indica menos errores; una imagen con más
contraste o un OCR con más texto no necesariamente da un mejor resultado.

## Qué se ha probado

- Original, escala de grises y canales R/G/B.
- CLAHE y gamma, distintas cuadrículas y órdenes de aplicación.
- Suavizado gaussiano, mediana, bilateral y enfoque.
- Normalización de fondo gaussiano/morfológico y contraste local.
- Engrosado de trazos vertical1×3,2×2 y otras configuraciones.
- Reducción/ampliación, interpoladores y realce antes o después de reducir.
- Alineación global, rectificación local y contexto de recorte.
- Eliminación experimental de líneas del formulario.
- DocRes: mejora de apariencia y binarización.

También se investigó **pero-enhance**, pero aún no lo he ejecutado.
Las pruebas se midieron con OCR; cambios de PSM y Sauvola interno se registran
como parte del reconocimiento, sin atribuir su efecto a un filtro de página.

## ¿Qué ha dado mejores resultados?

### Casos con referencias confirmadas

| Caso | Configuración destacada | Resultado |
| --- | --- | --- |
| Sergio1,6 renglones con cajas humanas | Suavizado gris3×3, CLAHE16×16/clip 3, gamma 2; escala 0,55 y Tesseract PSM6 | CER 14,99 %, WER 50,75 %. Con PSM7: CER 17,23 %. |
| Sergio3,6 renglones con cajas humanas | Original, escala 0,4 y Sauvola interno de Tesseract | CER 0,13 %, WER 0,85 %. |
| Salvador4,6 renglones con cajas humanas | Original, escala 0,4 | CER 0 %, WER 0 %. No necesita realce en esta muestra. |

Son configuraciones completas sobre renglones conocidos, **no resultados sobre
páginas completas**. En Sergio1 el valor también depende del modo OCR. En
Sergio3 destaca la binarización dentro de OCR, sin realce adicional de página.

Los límites de recorte también influyen: con recortes automáticos protegidos,
Sergio3 obtuvo CER 0,40 % con Sauvola, no0,13 %. En Salvador4, ajustar los límites
redujo CER 7,56 % a0 % en seis renglones con el mismo OCR. En Salvador1, la receta
geométrica sobre cajas humanas bajó CER 1,54 % a0,22 %. Estas mejoras de regiones
se documentarán con segmentación; no son filtros para aplicar a toda imagen.

### Casos históricos con referencias pendientes de confirmación

| Caso | Configuración que destacó | Resultado |
| --- | --- | --- |
| Sandra1,13 renglones | Suavizado3×3, CLAHE16×16/clip 3, gamma 2 y engrosado vertical1×3; escala 0,55 | Menor CER del protocolo:17,10 %, frente a19,36 % del control histórico. WER 57,76 %. |
| Javier1,7 renglones | CLAHE con suavizado/gamma sin engrosado; escala 0,55 | CER 2,25 %, frente a36,68 % del original a0,4. |
| Yanin1,7 renglones | Grises, escala 0,4 | CER 22,43 %, frente a24,30 % del original a igual escala. Persisten errores importantes. |
| Lenin2,30 renglones | Original, escala 0,4 | CER 0,125 %, WER 0,761 %. El realce lo empeoró. |
| Índice Lenin,2líneas de declaración | Original | CER 0 %. No evalúa los registros del índice. |

En Sandra, vertical1×3 a escala 0,4 obtuvo WER 52,17 % y CER 19,16 %:
el menor CER no coincide con el menor WER. La alternativa2×2 a0,5 obtuvo
CER 18,64 % y WER 56,52 %. Conviene indicar qué error reduce cada configuración.

Estas cifras son orientativas hasta confirmar las referencias. No se mezclan
con las anteriores. Cuando cambian filtro y escala, se compara el conjunto de
parámetros, no el efecto aislado de una transformación.

## Qué ha dado resultados menores o negativos

| Prueba | Resultado y decisión |
| --- | --- |
| DocRes appearance | Mejora pequeña frente al control redimensionado: CER 3,25→3,16 % en Lenin y49,95→49,64 % en Sandra. No elegido como tratamiento general. |
| DocRes binarization | Empeora: CER 4,48 % en Lenin y99,49 % en Sandra. No adoptado. |
| CLAHE suave,24 renglones confirmados | Sergio1 mejora57,27→41,16 %, pero Sergio3 empeora10,30→76,35 % y ambos casos claros empeoran. No aplicar globalmente. |
| Normalización de fondo | Algunas configuraciones ayudan Sandra y perjudican Lenin. Sin mejora general sobre los controles. |
| Enfoque, realce por recorte e interpoladores alternativos | No superaron el mejor resultado posterior de Sandra. |
| Rectificación local en Sergio1 | No superó los mejores controles disponibles y produjo regresiones. No adoptada. |
| Eliminación de reglas | No dio una mejora que justificara adoptarla; puede afectar letras que tocan las líneas. No se demostró preservación de intersecciones al suprimir la banda en Sergio1. |
| Selector por contraste | Activó realce donde el original ya se leía mejor. No adoptado. |

DocRes se evaluó sobre recortes redimensionados con otro protocolo; sus cifras
no se comparan directamente con las de los renglones anteriores. Pero-enhance
queda como investigación pendiente, no como resultado negativo.

## ¿Qué conservar por ahora?

**Original como control; grises, CLAHE con suavizado/gamma y engrosado vertical
como candidatos según el caso.** No se activa realce automáticamente. Falta
ampliar referencias confirmadas y comprobar su efecto sobre segmentación y OCR
en las mismas entradas antes de elegir una política para el flujo completo.

El código aplica las transformaciones a página completa conservando dimensiones
y número de página. Para generar la variante que destacó en Sandra:

```powershell
python preprocesar.py --entrada "carpeta_de_imagenes" --salida "salidas/vertical" --variante vertical_1x3
```

El comando aplica el tratamiento de página, **no reproduce por sí solo el
CER 17,10 %**: ese resultado incluye recortes, exclusiones y escala OCR0,55.
Para una página clara, usar `--variante original` como control.

[Instrucciones de uso](USO.md) · [Detalle y procedencia de resultados](RESULTADOS.md).

OpenCV y NumPy procesan localmente. DocRes requiere entorno/pesos separados y
no está integrado en este ejecutor. Licencias: OpenCV Apache2.0; NumPy BSD y
avisos de componentes incluidos. Compatibilidad institucional pendiente de revisar.
