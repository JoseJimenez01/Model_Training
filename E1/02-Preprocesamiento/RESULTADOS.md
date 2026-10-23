# Métodos evaluados y resultados

**No se ha elegido un tratamiento universal.** La configuración que funciona
mejor cambia entre páginas. Se conserva `original` como control y se comparan
variantes completas sobre la misma entrada, sin mezclar el mejor texto de cada
renglón usando la referencia.

## Mejores configuraciones históricas por caso

Estas métricas usan referencias **pendientes de confirmación humana**. Son
resultados orientativos de desarrollo y no deben mezclarse con las métricas
confirmadas del README. La escala indicada se aplicó al preparar el recorte
para OCR; este ejecutor de etapa 02 conserva el tamaño de la página.

| Caso | Configuración destacada | CER | WER |
| --- | --- | ---: | ---: |
| Lenin2,30 renglones | Original, escala 0,4 | 0,125 % | 0,761 % |
| Sandra1,13 renglones | Vertical1×3, escala 0,55; menor CER del protocolo | 17,10 % | 57,76 % |
| Sandra1,13 renglones | Vertical1×3, escala 0,4; alternativa por palabras | 19,16 % | 52,17 % |
| Sandra1,13 renglones | Engrosado2×2, escala 0,5 | 18,64 % | 56,52 % |
| Javier1,7 renglones | CLAHE con gamma, sin engrosado, escala 0,55 | 2,25 % | 11,69 % |
| Yanin1,7 renglones | Grises, escala 0,4 | 22,43 % | 48,31 % |
| Índice Lenin,2líneas de declaración | Original, escala 0,4 | 0 % | 0 % |

La evaluación del índice solo cubre dos líneas, no los registros del documento.
Sandra, Javier y Yanin conservan errores; los resultados no resuelven páginas
completas. El engrosado mejora Sandra, pero empeora otros casos y puede unir
trazos. Cambiar filtro y escala a la vez no aísla el efecto de un único filtro.

## DocRes: ejecutado localmente

Se evaluaron `appearance` y `binarization` en dos recortes, con control de
reducción/ampliación: lado máximo768px y retorno al tamaño original para OCR.
Seis evaluaciones, referencias históricas, sin validación de página completa.

| Caso | CER control redimensionado | DocRes appearance | DocRes binarization |
| --- | ---: | ---: | ---: |
| Lenin2 | 3,25 % | 3,16 % | 4,48 % |
| Sandra1 | 49,95 % | 49,64 % | 99,49 % |

`appearance` mejora muy poco sobre su control. `binarization` pierde casi toda
la lectura de Sandra. No se eligió DocRes como tratamiento general. Estas cifras
usan otro protocolo: no compararlas directamente con la tabla anterior para
atribuir superioridad a un modelo.

DocRes **no está integrado en `preprocesar.py`**. Requiere código oficial,
checkpoint y entorno PyTorch separado. Se ensayó el commit
`d3e3a18c7c7ad10e4615ca2eb6a10f83128d8560`, checkpoint SHA256
`1d6a89d754fe1e58ffd1865eab0ef3f03344798d39197b2d9a77ce4fbc8c02fd`.
Condiciones de pesos y dependencias pendientes de revisión institucional.

## Otros métodos y decisiones

| Método | Estado y conclusión |
| --- | --- |
| Pero-enhance | Investigado; no instalado ni ejecutado. Sin métricas propias. Su mejora guiada por texto exige evaluar riesgo de sustitución de caracteres; no usar referencias para generar imágenes. |
| Normalización de fondo gaussiano/morfológico, amplitud local y fondo+CLAHE | Ejecutadas; sin mejora general sobre controles. Fondo morfológico81/gamma 3/escala 0,5 alcanzó CER 19,16 % en Sandra, pero produjo regresiones en Lenin. |
| Mediana, bilateral, suavizado, canales de color, gamma y orden de realce/reducción | Ejecutados en desarrollo; el mejor tratamiento depende del caso. Se retienen seis variantes reproducibles en el ejecutor, no todo el barrido. |
| Selector por contraste | Probado con contraejemplos: activa realce en imágenes que ya se leían mejor sin él. No adoptado. |
| Eliminación de reglas e inpainting | No adoptada. En Sergio1r03, regla y letras comparten componentes; no se demostró preservación de intersecciones. |
| DocRes dewarping u otras tareas no incluidas arriba | Sin resultados locales reportados en esta entrega. |

## Resultados con referencias confirmadas

Al reagrupar los seis renglones de cada configuración del diagnóstico guardado:

| Caso | Configuración | CER | WER |
| --- | --- | ---: | ---: |
| Sergio1 | CLAHE16×16/clip3, suavizado3×3 y gamma2; escala0,55/PSM6 | 14,99 % | 50,75 % |
| Sergio1 | Mismo realce y escala, PSM7 | 17,23 % | 53,73 % |
| Sergio3 | Original0,4, Sauvola interno | 0,13 % | 0,85 % |

Estos valores corresponden a cajas humanas. No sustituirlos por cifras de
recortes automáticos ni atribuir el cambio PSM/Sauvola al realce de página.

La comparación original/CLAHE suave de24 renglones confirmados está en el
README: mejora Sergio1 y empeora los otros tres casos. No respalda CLAHE global.

Sauvola interno de Tesseract y las pruebas de PSM pertenecen a etapa04. En
recortes protegidos de Sergio3, Sauvola redujo CER 2,11→0,40 %, manteniendo
Salvador4 en0 %, pero introdujo una regresión local. Esto depende de cajas,
máscaras y escala; no se presenta como una mejora de página completa en etapa02.

## Procedencia de las mediciones

Identificadores de los experimentos conservados en el proyecto de desarrollo:

La revisión documental de esta entrega comprobó hashes de las17corridas del
resumen del13de octubre (4083evaluaciones), leyó las tres corridas de ampliación
(935evaluaciones), el piloto DocRes y los diagnósticos posteriores enumerados.
No se suman como una única muestra: reutilizan páginas y tienen protocolos y
estados de referencia distintos. No se ejecutó OCR nuevo para redactar el resumen.

- DocRes: `20261005T231902_7389bf2c`.
- Comparación original/CLAHE suave: `v79`, auditada junto con `v80`.
- Sandra y alternativas: resumen auditado de17corridas del13de octubre.
- Javier/Yanin/índice: ampliación del14de octubre,935evaluaciones.
- Sauvola protegido: `v106`; escala adicional no adoptada: `v107`.
- Intersecciones de regla/letras: `v110`, diagnóstico sin OCR nuevo.
