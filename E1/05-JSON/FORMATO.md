# Formato operativo de tomos

Versión: **`propuesta_tomo_02`**. 
Se puede ver el cuerpo en el archivo `ejemplo_tomo.json`
La propuesta de nombres basados en tomo/notario o período no está cerrada ni
debe construirse con metadatos dudosos como si fueran verificados.

## Cabecera

| Campo | Contenido |
| --- | --- |
| `version_esquema` | `propuesta_tomo_02`. |
| `tipo` | `tomo`. |
| `tomo_id` | Identificador técnico derivado de un número reconocido; nulo si falta. |
| `numero_tomo` | Número recuperado; nulo si falta lectura suficiente. |
| `notario.nombre` | Nombre desde una mención explícita del notario; no desde comparecientes o archivo. |
| `notario.carne` | Cadena leída del carnet en su región del sello. Se conserva el nombre de clave elegido. |
| `total_paginas_incluidas` | Cantidad de páginas seleccionadas, no necesariamente total del PDF. |
| `paginas` | Lista de páginas incluidas, en su orden. |

Una conversión técnica, por ejemplo `OCHO`→8 y luego `tomo_08`, conserva la
expresión original y su procedencia en evidencia. No corregir confusiones OCR
por el número esperado ni deducir tomo del nombre del archivo.

## Página

| Campo | Contenido |
| --- | --- |
| `pagina_pdf` | Posición original en el PDF, desde 1. |
| `folio.numero` | Cadena que conserva ceros iniciales, o nulo. |
| `folio.lado` | `frente`, `vuelto` o nulo. |
| `folio.origen` | `leido_ocr`, `inferencia` o el estado que conserva la exportación/evidencia; no asignar lectura ficticia. |
| `papel_seguridad.numero` | Número leído, sin propagación automática entre páginas. |
| `papel_seguridad.serie` | Serie literal recuperada. |
| `actos_mencionados` | Campo del formato conservado; extracción pendiente en el ejemplo actual. |
| `texto` | Texto unido por página o nulo cuando no hay contenido autorizado para publicar. |
| `organizacion_texto` | Unidad usada y cantidad; no certifica que todas las unidades estén transcritas. |
| `alertas` | Códigos y mensajes técnicos, sin interpretación jurídica. |

Regla de folio vigente: el rótulo superior derecho reconocido identifica
folio/frente. La siguiente página PDF consecutiva compatible puede recibir el
mismo folio/vuelto como inferencia. Sin frente leído, ante saltos o contradicción,
mantener pendiente. Nunca calcular folio únicamente por posición/paridad PDF.


## Evidencia técnica

Se conserva por separado: fuente y página, imágenes/hashes, regiones y
`bbox:[x1,y1,x2,y2]`, renglón físico cuando se conoce, texto OCR original,
confianza disponible, variante, escala, configuración, errores y procedencia
de metadatos. Inclusión de bbox en el JSON final pendiente.

Distinguir motor no ejecutado, lectura vacía, lectura parcial, no reconocido,
error y vacío fuente comprobado. Un `null` de consumo necesita esa explicación;
no es por sí mismo un diagnóstico. La guardia de entrada blanca bloquea la
publicación de OCR espurio sin borrar su evidencia histórica.

Conflictos entre lecturas y datos dudosos se conservan en evidencia/alertas;
no se resuelven eligiendo un valor por contexto. No transcribir manuscritos o
sellos completos, reconstruir impresión oculta ni interpretar contenido jurídico.

## Comprobaciones para el exportador

- Una entrada por página solicitada, incluso ante fallo; salida incompleta explícita.
- Conteo de páginas coherente y orden/identidades conservados.
- Texto literal, sin corrección semántica ni invención de campos.
- Posiciones físicas pendientes preservadas si existe estructura de 30 renglones.
- Datos leídos separados de inferidos y trazabilidad hasta la entrada OCR.
- JSON UTF-8 válido; validación de sintaxis separada de validación del contenido.

Estas comprobaciones describen el comportamiento que debe conservar la
integración. No se entrega aquí un validador o exportador autónomo nuevo.
