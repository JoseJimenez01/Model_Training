# 03 — Segmentación de páginas

**De momento se conserva el detector v32 como referencia para localizar texto
impreso, escritura a mano y sellos.** Las variantes posteriores recuperaron
algunas regiones, pero no lograron una mejora que compensara sus detecciones
falsas. La identificación de renglones físicos se trabaja por separado.

La segmentación sigue en desarrollo: hay manuscritos omitidos, cajas que cortan
texto impreso y páginas cuya numeración no se resuelve. Una región detectada
no garantiza que todo su contenido sea apto para OCR.

## Qué se ha probado

- Reglas geométricas, componentes de tinta, proyecciones y agrupación de líneas.
- Separación y agrupación de tinta azul como apoyo para localizar manuscritos.
- Detección aprendida con Faster R-CNN MobileNetV3-Large FPN: configuración base,
  perfil para documentos y tamaños de regiones más pequeños.
- Detectores locales sobre ventanas de detalle/contexto para firmas y manuscritos.
- Ampliación de anotaciones, zonas ignoradas y muestreo de fondos difíciles.
- Combinación de detecciones, contención, consenso y reordenamiento por calidad
  geométrica o visual antes de eliminar duplicados.
- Localización de la columna numérica y verificación de la secuencia1–30.
- Ajuste de límites de renglón mediante grupos de tinta y asociación geométrica
  ordenada, con posiciones pendientes ante ambigüedad.
- Exclusión de cajas de manuscritos/sellos y diagnóstico de impresión cortada
  o trazos manuscritos que permanecen en las entradas OCR.

Las anotaciones humanas sirven para entrenamiento y evaluación. No forman una
etapa de revisión manual obligatoria después del procesamiento productivo.

## ¿Qué ha dado mejores resultados?

### Detección de regiones: v32 como referencia actual

Comparación sobre cinco páginas de validación de Salvador, umbral0,35 e
intersección sobre unión de cajas (IoU)0,50. Las ternas indican
**aciertos / detecciones falsas / omisiones**.

| Modelo | AP101 macro | Impreso | Mano | Sello |
| --- | ---: | --- | --- | --- |
| v29, perfil documento | 61,30 % | 24/7/5 | 12/0/1 | 6/0/0 |
| **v32, control documento** | **62,39 %** | **25/5/4** | 11/1/2 | 6/0/0 |
| v32, tamaños pequeños | 60,40 % | 24/5/5 | 12/0/1 | 6/0/0 |

V32 control mejora el promedio y la detección de impreso, pero **no gana en
todas las clases**: omite una región de mano más que v29 en esta muestra.
El AP101 es la métrica del evaluador local, no una reproducción de COCOeval.
Estas cinco páginas ya guiaron decisiones y no son validación independiente.

En una demostración sobre cinco páginas anotadas de Lenin, v32 registró
impreso23/5/0, mano15/3/0 y sellos4/0/0. Son páginas de entrenamiento, no prueba
de generalización. En páginas adicionales se observaron cajas duplicadas y
texto o manuscritos fuera de las cajas.

### Renglones físicos: mejores avances geométricos

La selección de una columna geométrica antes de leer sus números resolvió la
secuencia1–30 en **Sergio3 y Salvador4**, de cuatro páginas diagnosticadas.
Sergio1 y Salvador1 siguen pendientes. No se inventan números por posición.

En Salvador4, la preparación de recortes y el ajuste de límites por tinta
redujeron el error OCR de caracteres de7,56 % a0 % en seis renglones verificados.
La asociación de página produjo30correspondencias, pero eso no verifica la
transcripción de todos los renglones.

La asociación parcial y el rechazo de anclas inconsistentes permitieron
**97asociaciones geométricas y23pendientes en120posiciones** de Salvador,
páginas2–5. Se conservan las posiciones pendientes: ausencia de asociación
no significa que un renglón esté vacío. No es una exactitud de97/120.

## ¿Qué no ha mejorado suficientemente?

| Prueba | Resultado y decisión |
| --- | --- |
| Reglas o color como único criterio | No cubren todos los manuscritos, especialmente tinta negra o superpuesta. No sustituyen al detector. |
| Regiones pequeñas en v32 | No recuperaron las dos marcas pequeñas objetivo de Sergio y bajaron el AP macro. No adoptadas. |
| Detectores locales ampliados | Recuperan regiones, pero añaden muchos falsos positivos. No reemplazan a la base. |
| Muestreo de fondos difíciles | Reduce falsos positivos frente a su control local, pero sigue peor que v32 en validación. |
| Contención y consenso | Pueden reducir cajas falsas a costa de perder marcas independientes o aciertos. No adoptados como regla general. |
| Calidad geométrica/visual para ordenar duplicados | Mejoran algunos indicadores auxiliares, pero empeoran la selección final y llegan a perder una referencia. Descartadas. |
| Ajuste local de límites aplicado globalmente | Ayuda casos concretos, pero produjo regresiones y asociaciones erróneas en otros. No aplicar sin controles. |
| Borrar rectángulos completos de mano/sello | Puede excluir impresión visible; tampoco elimina manuscritos que el detector omitió. No certifica una región limpia. |

## Qué conservar por ahora

**V32 congelado para comparar regiones, umbral0,35 y geometría conservadora para
renglones, manteniendo explícitos los casos pendientes.** No activar tratamientos
nuevos de etapa02 sobre el detector suponiendo que lo mejorarán: el modelo
conservado se evaluó con su preparación de imagen original.

Las cajas se registran como `[x1,y1,x2,y2]` en píxeles de la imagen fuente. El
detector distingue tres categorías, no transcribe texto ni genera por sí solo
los30renglones. Firmas y manuscritos se detectan sin transcribir; de sellos solo
se busca el carnet en la etapa de lectura correspondiente.

Pendiente resolver marcas manuscritas residuales, cortes de impresión, páginas
mixtas y numeración difícil. El ensayo con los mismos pesos en ventanas está
preparado, **sin resultados de inferencia** por bloqueo de `_C.pyd` en Windows.

Esta entrega registra resultados y configuración. La integración de un ejecutor
autónomo y la distribución de pesos se prepararán por separado; aquí no se
presenta un script nuevo como si ya reprodujera el detector completo.

[Comparaciones detalladas](RESULTADOS.md) · [Modelo y configuración](MODELO.md).
