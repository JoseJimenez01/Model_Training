# 01 — Extracción de páginas PDF

Esta es la primera etapa de E1, se encarga de extraer las páginas de un PDF y convertirlas a imágenes para su procesamiento.
En la versión final se procesará el PDF completo.
Para pruebas dejé 2 opciones de ejecutar este código, una es por consola con parámetros y la otra es mediante una interfaz
de Tkinter.
La idea final es por consola y que ejecute de una vez todo el PDF completo, que la única diferencia sea entre Tomo e Índice.

## Implementado

Convierte un PDF de tomo o índice en una imagen PNG por página mediante
**PyMuPDF**. Permite extraer el documento completo o seleccionar páginas.

- Salida PNG en color RGB, a **300 DPI** por defecto.
- Selector de PDF, carpeta de destino, tipo de documento y páginas con **tkinter**.
- Ejecución por comandos con rutas, páginas y DPI configurables.
- Conservación de la numeración de páginas del PDF.
- Registro de configuración, archivos generados y errores en `manifest.json`.
- Continuación con las demás páginas si falla una; resultado marcado como incompleto.

El procesamiento es local. Cada ejecución procesa un PDF.

## Instalación y uso en Windows

Python 3.13 es la versión utilizada para verificar esta entrega. Desde esta
carpeta, en consola:

```
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Uso con ventanas

Se puede ejcutar de varias formas, la más sencilla es ejecutando `AbrirExtractor.pyw`

1. Pulse **Buscar...** para seleccionar el PDF.
2. Elija la carpeta donde guardar el resultado.
3. Seleccione `tomo` o `indice`.
4. Deje las páginas vacías para extraer todas o escriba, por ejemplo, `1,3-5`.
5. Pulse **Extraer paginas**.

El selector usa 300 DPI y crea una subcarpeta nueva con el nombre del PDF y
fecha/hora dentro del destino seleccionado; no sobrescribe una carpeta previa.
Muestra el estado final y su ubicación, o el error correspondiente. Durante
la extracción mantiene la ventana disponible y bloquea otra ejecución/cierre.
Cancelar un selector no inicia procesos. No incluye previsualización del PDF.

Tkinter utiliza la biblioteca estándar de Python, no agrega una dependencia
pip. La instalación de Python necesita incluir Tcl/Tk para abrir las ventanas.
Los seis archivos de esta carpeta deben permanecer juntos. Una instalación
inicial de Python y PyMuPDF sigue siendo necesaria; no es un ejecutable autónomo.

### Uso por comandos

Extraer **todas** las páginas de un tomo:

```powershell
& .\.venv\Scripts\python.exe .\GetPages.py --pdf "..\..\datos_locales\tomo.pdf" --tipo tomo --salida ".\salidas\tomo_01"
```

Extraer páginas seleccionadas de un índice:

```powershell
& .\.venv\Scripts\python.exe .\GetPages.py --pdf "..\..\datos_locales\indice.pdf" --tipo indice --paginas "1,3-5" --dpi 300 --salida ".\salidas\indice_01"
```

Las rutas de ejemplo deben apuntar a sus archivos locales. Las páginas empiezan
en 1 y corresponden a la posición en el PDF, **no al número de folio notarial**.
Las selecciones se ordenan y eliminan duplicados. La carpeta de salida debe
ser nueva para evitar sobrescribir resultados. No se requiere GPU o Tesseract.

## Archivos generados

```text
salidas/tomo_01/
├── page_001.png
├── page_002.png
└── manifest.json
```

`manifest.json` es evidencia técnica de extracción, **no el JSON de contenido
que E1 entrega a E3**. Registra nombre/hash SHA256 del PDF, tipo declarado,
páginas seleccionadas, DPI, versión PyMuPDF y, por página, estado, dimensiones,
nombre/hash de PNG o error. Las rutas de imagen son relativas a la salida.

Estado final `completo` o `incompleto`. Código de salida 
0 si todas las páginas seleccionadas se extraen.
2 si falla alguna página.
1 ante un error que impide iniciar, como PDF ilegible, contraseña requerida, selección inválida, salida
existente o dependencia ausente.
Un fallo de página queda registrado: no se omite silenciosamente. Un archivo parcialmente escrito se señala en el manifiesto.


## Límites y pendiente

No aplica mejoras de imagen, separación de regiones, OCR, interpretación de
contenido o inferencia de folios. Un PNG generado correctamente no demuestra
que el texto sea legible o esté transcrito correctamente. Tampoco modifica el PDF.

## Dependencia y licencia

PyMuPDF es la dependencia de renderizado ya usada por el proyecto, fijada aquí
a la versión1.28.2 verificada localmente. Su distribución declara licencia dual
**AGPL-3.0 o comercial Artifex**.
