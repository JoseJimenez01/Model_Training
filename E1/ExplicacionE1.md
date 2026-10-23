# OCR y Extracción de Texto

Mi módulo se divide en 5 tareas:
1. Extraer las imágenes del PDF.
2. Aplicar algun preprocesmiento a las imágenes antes de intentar reconocer su contenido.
3. Aplicar una segmentación a la página que permite identificar los elementos más importantes.
4. Aplicar el motor de OCR que extraiga el texto de los segmentos del punto anterior.
5. Crear un archivo tipo JSON con la información extraída del PDF.

La idea es que sea un único flujo seguido, un solo programa, sin embargo, para poder probar cada etapa, en esta rama creé 5 carpetas y agrego código separado en cada etapa, de modo que pueda ir mejorando cada una hasta llegar al  objetivo final.

Voy a agregar también código que permita ejecutar las 5 etapas a la vez actuales, sin embargo será solo algo temporal para ver el avance actual y no es la versión final.

Ahorita los procesos están más centrados en tomos que en los índices. Aún no he llegado a procesar bien los índices.