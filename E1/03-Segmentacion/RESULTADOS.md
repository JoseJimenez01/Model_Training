# Comparaciones y límites de segmentación

## Detector global

El piloto inicial comparó Faster R-CNN MobileNetV3-Large FPN estándar con un
perfil para documentos. V29 documento obtuvo AP101 macro 61,30 %, frente a
51,17 % de la base en validación. El test histórico se evaluó una vez y mostró
fragmentación/confusión de categorías; no quedó demostrada generalización.

V32 repitió la receta con las correcciones de anotación de Sandra y comparó
anchors documento frente a tamaños menores. Se entrenó con15páginas y validó
con5; no se consultó test para ese ensayo. Control:84épocas, mejor54; pequeños:
94épocas, mejor64. Una corrida por receta no permite atribuir toda diferencia
a un solo parámetro ni eliminar variabilidad de entrenamiento.

V32 conserva el bloque inferior impreso de Salvador5, pero no resuelve las
dos marcas pequeñas de Sergio3 ni todos los manuscritos de Salvador. Cambiar
solo tamaños de anchors o bajar el umbral no resolvió esas marcas.

## Detección local de manuscritos

La ampliación incorporó otras referencias/páginas: **no comparar sus recuentos
con la validación multiclase de cinco páginas como si fueran el mismo conjunto**.
En nueve páginas de validación ampliada,22regiones de mano, umbral0,35/IoU0,50:

| Ruta | Aciertos | Falsas detecciones | Omisiones |
| --- | ---: | ---: | ---: |
| Base v32 | 18 | 8 | 4 |
| Base + detalle mixto v36 | 18 | 37 | 4 |
| Base + ignorados v37 | 18 | 48 | 4 |
| Base + ajuste ampliado v45 | 19 | 64 | 3 |
| Muestreo dirigido v51, combinado con contención | 18 | 51 | 4 |

V45 recupera una región y sube recall81,82→86,36 %, pero precisión baja
69,23→22,89 %. V51 reduce falsos positivos frente a su control combinado
(101→51), sin mejorar a la base de8falsos positivos y18aciertos.

Contención y consenso se probaron para reducir duplicados/cajas espurias.
Exigir apoyo puede perder marcas válidas; protegerlas vuelve a añadir falsos
positivos. No se adoptó una política general que supere la base conservada.

Los reordenadores geométrico v57 y visual PCA/ridge v59 no pasaron sus controles
en train: en el brazo dirigido pasan85/214/0 a84/215/1 y pierden una referencia.
Se descartaron sin evaluar validation. Una mejor predicción auxiliar de IoU no
garantiza una mejor selección de detecciones.

La consolidación v60 registra24omisiones de la base sobre las referencias
derivadas de ese momento:20train y4validation. No son errores de transcripción.
Hay20omisiones train con85positivos, frente a otro conjunto anterior de84:
no presentar el cambio de denominador como una variación del modelo.

## Renglones y zonas mixtas

- La columna geométrica v86 descarta un componente de cabecera ajeno a los
  números de Sergio3; valida las30lecturas y mantiene Salvador4. Resultado:
  dos de cuatro páginas con secuencia completa, sin completar valores por contexto.
- El remuestreo global con soporte de caja v81 baja CER10,08→7,56 % en seis
  recortes automáticos de Salvador4. No es mejora exclusiva del detector.
- El ajuste por tinta v82 llega a0 % en esos seis renglones; su generalización
  v83 muestra regresiones. No se convierte en regla universal.
- La asociación global v93 conserva orden y unicidad. Exigir30grupos completos
  rechaza páginas con contenido mixto; v95 admite pendientes sin inventar grupos.
- V96 retira el rol de ancla de un grupo inconsistente sin borrar su tinta:
  páginas2/3/4/5 quedan15/27/30/25asociadas y15/3/0/5pendientes respectivamente.
- Las recuperaciones locales v98–v100 rescatan impresión visible en regiones
  inspeccionadas. No constituyen un localizador general ni autorizan el OCR
  de zonas con manuscritos residuales.
- V103 confirma que dos marcas humanas ya anotadas de Sergio3 no intersectan
  ninguna caja de mano guardada, incluso las inferiores al umbral operativo.
  El residuo observado en Salvador3 sigue sin clasificación humana confirmada.

## Límites de evaluación

Los resultados son de pocos documentos y páginas conocidas. La validación de
Salvador se ha usado repetidamente para decisiones; no es evidencia independiente.
No hay calidad mínima acordada. Una caja correcta no garantiza una máscara
por píxel, límites de recorte exactos, numeración física o transcripción fiel.

La clase mano reúne firma y otros manuscritos; las subcategorías se conservan
en las anotaciones. Carnet es una anotación auxiliar dentro del sello, no una
cuarta clase del detector. El piloto aprendido descrito es de tomos; no se
ha validado como detector general para los índices.

## Procedencia

Identificadores de evidencia conservada en desarrollo: piloto v29; comparación
v32 `20261022T010349_755193Z`; ajuste v45 `20261022T174722_592421Z`; ensayo
pareado v51 `20261022T192626_728899Z`; calibrador v57; visual v59; consolidación
v60 `20261022T224502_351736Z`; demostración Lenin v67; numeración v85/v86;
geometría v81–v96; recuperaciones v98–v100; residuos v103 y ensayo pendiente
v104/v105. No se incluyen documentos, anotaciones o recortes notariales.
