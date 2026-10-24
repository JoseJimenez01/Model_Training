# Flujo completo provisional — E1

Una entrada para seleccionar un tomo PDF, procesar todas sus páginas o una
selección y generar **`formato.json`** con texto unido por página. Funciona
localmente, sin subir documentos ni entrenar modelos.

Reúne extracción PNG300DPI, preprocesamiento elegido, detector v32, numeración
experimental, Tesseract y exportación `propuesta_tomo_02`. Intenta recuperar
tomo/notario y campos de cabecera; sin lectura suficiente los deja nulos.
El carnet requiere además su localizador específico. Los vueltos se infieren
solo desde un frente leído inmediatamente anterior y estructura compatible.

**Es un flujo provisional:** puede omitir impresión, dejar manuscritos residuales
o devolver texto equivocado. Conserva estas limitaciones y sus alertas. La
integración no convierte los resultados parciales de cada etapa en un sistema
validado para todas las páginas. El contrato definitivo con E3 sigue pendiente.

## Abrir y procesar

Abra **`AbrirFlujo.pyw`** con doble clic. También puede ejecutar `FlujoCompleto.py`
sin parámetros. Es una única entrada de ejecución; los archivos auxiliares de
esta carpeta deben permanecer juntos.

1. Seleccione el PDF y la carpeta donde guardar.
2. Seleccione el checkpoint del detector v32. Si desea intentar el carnet,
   seleccione también el checkpoint del localizador v76.
3. Si los modelos están en otro entorno, seleccione su `python.exe` en
   **Python del detector**. Vacío utiliza el Python que abrió la aplicación.
4. Indique páginas, por ejemplo `1,3-5`; vacío procesa todas. Inicialmente se
   propone solo la página1 para una primera comprobación.
5. Mantenga `original`/`otsu` como control o elija expresamente otro candidato.
6. Pulse **Procesar tomo** y, al terminar, **Ver resultado por pagina**.

El detector siempre recibe la imagen original. La variante elegida se aplica
solo a la copia para OCR, manteniendo coordenadas. No hay selector automático
de tratamiento por calidad ni por nombre del documento.

Las rutas de modelos, destino y ejecutables se recuerdan en `ajustes.local.json`,
excluido de Git. Cada corrida crea una carpeta nueva. **Detener** espera la
operación actual y conserva lo procesado, con páginas restantes canceladas.

## Revisar un PDF largo

El visor muestra un índice y abre **una página cada vez**, con texto, campos
y alertas. No carga el texto completo de200páginas en una sola vista.
`formato.json` reúne todas las páginas seleccionadas; `ejecucion.json` registra
estado y procedencia. El TXT completo es opcional y está desactivado por defecto.
Si se activa, `revision.txt` separa páginas con encabezados de revisión.

```text
flujo_FECHA_HORA/
├── formato.json
├── ejecucion.json
├── evidencia_folios.json
├── index.html
├── revision.txt                 # solo si se solicita
└── paginas/
    ├── page_001.html
    └── page_001/
        ├── original.png
        ├── procesada.png
        ├── protegida.png
        ├── detecciones.json
        ├── evidencia.json
        └── ...                 # recortes, TXT/TSV y numeración
```

Las páginas conservan su número original en el PDF. Sin secuencia numérica
resuelta se usan regiones sin número físico; no se inventan30renglones. Fallos
aislados se registran y continúa la siguiente página. Una entrada totalmente
blanca no invoca el motor ni se interpreta como vacío en la fuente.

`retenciones.json` conserva las páginas de fuentes exactas con problemas ya
identificados: no se ejecuta OCR del cuerpo ni se publica texto de esas páginas.
Los campos de cabecera pueden seguir procesándose en sus regiones específicas.
Este registro no es un detector general de fallos en documentos nuevos.

## Preparación del entorno

Python3.13, Tesseract con modelos **spa y eng**, y las dependencias de
`requirements.txt`. Tcl/Tk es necesario para ventanas. Instale las dependencias
en el Python que abrirá la aplicación:

```powershell
python -m pip install -r requirements.txt
```

El entorno del detector necesita PyTorch/TorchVision compatibles. La referencia
ya utilizada es torch2.7.1+cu118 y torchvision0.22.1+cu118. `requirements-modelo.txt`
documenta las versiones base para un entorno separado; no selecciona por sí
solo la distribución CUDA. Se puede utilizar el entorno existente, sin reinstalar.
No se instalan paquetes, descargan pesos o cambian protecciones automáticamente.

Los checkpoints se mantienen **localmente, fuera del seguimiento de Git**.
La carpeta preparada en este equipo contiene copias en `pesos/detector_v32.pt`
y `pesos/carnet_v76.pt`, junto con ajustes locales para el entorno existente.
En otro equipo deben proporcionarse los mismos checkpoints y revisar las rutas.
También se pueden seleccionar desde otra carpeta del disco.
`modelos.json` comprueba sus hashes; no admite silenciosamente otros pesos.
El localizador de carnet es opcional; su ausencia queda indicada.

El programa busca Tesseract en PATH o su instalación Windows habitual. Si no
lo encuentra, seleccione su ejecutable. Antes de extraer el documento comprueba
Tesseract/modelos: si falta una dependencia esencial, se detiene explícitamente.

## Ejecución sin ventanas

Copie y ajuste `config.ejemplo.json`. Las rutas relativas se resuelven desde
la carpeta de configuración, y la salida debe ser nueva.

```powershell
python FlujoCompleto.py --config config.local.json
```

Para no intentar carnet, deje `modelo_carnet` vacío. La selección indicada
cuenta posiciones PDF, no folios. Los datos desconocidos permanecen nulos y
los conflictos entre lecturas se conservan en evidencia.

## Alcance de comprobación

Siete pruebas pasan con PDF/OCR reales y detecciones simuladas para comprobar
exclusiones, continuidad ante fallos, cancelación y retenciones conocidas.
También se ejecutó el flujo con modelos reales sobre un PDF sintético y las
páginas3–4 de Salvador. La corrida final mantiene el cuerpo de página3 retenido
y genera una salida parcial para página4, carnet y folio/frente-vuelto.
Un control de Lenin reproduce las22clases detectadas, con diferencias menores
de0,001px en las cajas respecto a las predicciones históricas.
No es una evaluación nueva de precisión ni justifica transcribir manuscritos.
La ventana necesita comprobación visual en escritorio: Tcl/Tk no inicia en la
sesión de preparación, aunque el modo por comandos funciona.

```powershell
python -m unittest test_flujo.py -v
```

Las recetas reutilizadas y adaptaciones figuran en `procedencia_recetas.json`.
No se incluyen anotaciones, textos de referencia o PDFs notariales. PyMuPDF
declara AGPL/comercial; PyTorch/TorchVision/Pillow, BSD/avisos correspondientes;
OpenCV Apache2.0 y NumPy BSD/avisos de componentes. Condiciones de distribución
de pesos y compatibilidad institucional pendientes de revisión.
