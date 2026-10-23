# Configuraciones OCR de referencia

Tesseract usado en los últimos controles: **5.5.3.20260724**, idioma `spa`.
Se requiere el ejecutable y su modelo de español, no solo una biblioteca Python.
Los resultados guardan la versión completa y el comando de cada invocación.

| Uso | Configuración experimental |
| --- | --- |
| Renglón impreso aislado | PSM 7; Otsu interno0 como control. |
| Celda o bloque de varias líneas | PSM 6. |
| Candidato Sauvola | `thresholding_method=2`, con los demás parámetros internos de la misma instalación. |
| Margen blanco | 20 px después de preparar el recorte. |
| Carnet Salvador v78 | spa/PSM 7, altura objetivo48 px y margen blanco20 px, con caja/margen geométrico previos. |

Las escalas0,4/0,55 pertenecen a protocolos concretos, no son una configuración
universal. Hay reducción local y reducción global con soporte de caja; conservar
el mapeo exacto. PSM 6 sobre una línea realzada fue una comparación dirigida,
no motivo para cambiar todas las líneas a ese modo.

En índices se preservan las celdas multilínea. En tomos se conserva la identidad
de renglón físico cuando la numeración está resuelta; los saltos de línea del
motor no crean automáticamente nuevos renglones físicos.

El resultado interno debe conservar texto OCR literal, confianza disponible,
modelo/idioma/PSM/binarización, imagen de entrada, transformaciones, coordenadas,
fuente/página y errores. NFC/espacios se usan para comparar métricas sin corregir
el contenido. No reconstruir impresión oculta ni transcribir manuscritos.

Una salida vacía del motor se distingue de motor no ejecutado, error y vacío
fuente verificado. Una imagen no blanca tampoco demuestra texto recuperable.

Kraken comparado:7.1.1, modo `ocr --no-segmentation`. Modelos históricos:

- McCATMuS_nfd_nofix_V1, SHA256
  `dfb911ba25fd11f93efc1b0c340957162981ecfdaac0ee1e26793d491f770244`.
- catmus-print-fondue-large, SHA256
  `1ed39e732b26ccdd0f14b9abd3edc66c4b04a02e3d827d7f9e96a7fe7b585b64`.

Hashes históricos, sin recálculo actual en WSL. Adecuación del encuadre,
segmentación por baseline y licencia específica de pesos pendientes de verificar.
No se incluyen pesos ni instalación automática. Tesseract/Kraken usan licencia
de software Apache2.0; conservar avisos y revisar también las condiciones de
modelos, instalador y distribución institucional.

Esta carpeta documenta el avance. Pendiente preparar el ejecutor autónomo para
el repositorio grupal con entradas de etapa03 y evidencia para etapa05.
