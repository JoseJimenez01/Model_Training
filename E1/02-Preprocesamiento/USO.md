# Uso del preprocesamiento

## Instalación

Python3.13 y Tcl/Tk para las ventanas. Desde esta carpeta, en PowerShell:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Uso con ventanas

Ejecute **`AbrirPreprocesamiento.pyw`**  donde
instaló las dependencias. Seleccione la carpeta de imágenes, escriba el nombre
de la variante y elija dónde guardar. Se crea una subcarpeta nueva y se muestra
el resultado final. Windows necesita tener asociada la extensión`.pyw` a Python.
También puede usar:

```powershell
& .\.venv\Scripts\pythonw.exe .\AbrirPreprocesamiento.pyw
```

## Uso por comandos

```powershell
& .\.venv\Scripts\python.exe .\preprocesar.py --entrada "..\01-Extraccion\salidas\tomo_01" --salida ".\salidas\tomo_original" --variante original
```

Para comparar, repita con otra variante y otra carpeta de salida. Una carpeta
de salida existente se rechaza. 
Código de salida 0: completo.
1: error de inicio.
2: resultado incompleto.

## Salida

```text
salidas/tomo_original/
├── page_001.png
├── page_002.png
└── manifest.json
```

El manifiesto conserva la identificación del PDF y las páginas de extracción.
Sin manifiesto de entrada, el número de página PDF queda desconocido y los
archivos se nombran `imagen_0001.png`, etc.; no se infiere folio por el nombre.
Las imágenes se guardan como PNG de8bits; RGB para original/CLAHE suave y
grises para las otras variantes. Un gris de entrada se representa como RGB
equivalente antes de aplicar la variante. No admite transparencia ni imágenes
de 16 bits. No se conserva metadato DPI del PNG: se conservan sus dimensiones;
la configuración de extracción puede consultarse en su manifiesto original.

