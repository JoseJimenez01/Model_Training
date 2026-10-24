"""Procesamiento local por pagina, con variantes fijas y trazabilidad."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

VARIANTES = ('original', 'gris', 'clahe_suave', 'clahe_gamma', 'vertical_1x3', 'engrosado_2x2')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def transformar(image, variante):
    """Entrada BGR uint8; no cambia dimensiones ni reconstruye trazos."""
    import cv2
    import numpy as np
    if variante == 'original':
        return image.copy(), {}
    if variante == 'gris':
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), {'conversion': 'BGR2GRAY'}
    if variante == 'clahe_suave':
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR), {'canal': 'L de LAB', 'clipLimit': 1.5, 'tileGridSize': [8, 8]}
    if variante in ('clahe_gamma', 'vertical_1x3', 'engrosado_2x2'):
        gray = cv2.GaussianBlur(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (3, 3), 0)
        result = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16, 16)).apply(gray)
        result = np.clip((result.astype(np.float32) / 255) ** 2 * 255, 0, 255).astype(np.uint8)
        params = {'suavizado_previo': [3, 3], 'clipLimit': 3.0, 'tileGridSize': [16, 16], 'gamma': 2.0}
        if variante != 'clahe_gamma':
            kx, ky = (1, 3) if variante == 'vertical_1x3' else (2, 2)
            result = cv2.erode(result, np.ones((ky, kx), np.uint8))
            params['engrosado_kernel_xy'] = [kx, ky]
        return result, params
    raise ValueError('Variante desconocida: ' + variante)


def procesar(entrada, salida, variante='original'):
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError('Instale requirements.txt con el mismo Python.') from exc
    entrada, salida = Path(entrada), Path(salida)
    if variante not in VARIANTES or not entrada.is_dir():
        raise ValueError('Revise variante y carpeta de entrada.')
    parent = entrada / 'manifest.json'
    previous = None
    if parent.exists():
        previous = json.loads(parent.read_text(encoding='utf-8'))
        if previous.get('etapa') != 'extraccion':
            raise ValueError('El manifiesto de entrada debe corresponder a etapa01.')
        # Keep failed pages too: downstream output must remain explicitly incomplete.
        items = previous['paginas']
        if not items or len(items) != len({r['pagina_pdf'] for r in items}):
            raise ValueError('Manifiesto sin paginas o con paginas duplicadas.')
        for row in items:
            if row['estado'] == 'ok' and Path(row['imagen']).name != row['imagen']:
                raise ValueError('El manifiesto debe contener nombres de imagen locales.')
    else:
        items = [dict(estado='ok', imagen=p.name, pagina_pdf=None)
                 for p in sorted(entrada.iterdir()) if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.tif', '.tiff') and p.is_file()]
        if not items:
            raise ValueError('No hay imagenes compatibles en la carpeta.')
    salida.mkdir(parents=True, exist_ok=False)
    report = dict(etapa='preprocesamiento', estado='en_proceso', fecha_utc=datetime.now(timezone.utc).isoformat(),
        variante=variante, opencv_version=cv2.__version__, numpy_version=np.__version__,
        tipo=previous.get('tipo') if previous else None, fuente_pdf=previous.get('fuente') if previous else None,
        manifiesto_entrada_sha256=sha(parent) if previous else None, paginas=[])

    def save():
        (salida / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    save()
    for index, item in enumerate(items, 1):
        row = dict(pagina_pdf=item['pagina_pdf'], imagen_origen=item.get('imagen'), estado='error')
        try:
            if item['estado'] != 'ok':
                raise ValueError('Fallo previo en extraccion: ' + item.get('error', 'pagina no disponible'))
            source = entrada / item['imagen']
            digest = sha(source)
            if item.get('sha256') and digest != item['sha256']:
                raise ValueError('Hash distinto del registrado por extraccion.')
            image = cv2.imdecode(np.fromfile(source, np.uint8), cv2.IMREAD_UNCHANGED)
            if image is None or image.dtype != np.uint8:
                raise ValueError('Imagen ilegible o profundidad distinta de8bits.')
            if image.ndim == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            if image.ndim != 3 or image.shape[2] != 3:
                raise ValueError('Se requieren imagenes RGB/grises sin transparencia.')
            processed, params = transformar(image, variante)
            if processed.shape[:2] != image.shape[:2]:
                raise ValueError('Cambio de dimensiones inesperado.')
            # Index prevents collisions between different inputs sharing a stem.
            name = f'page_{item["pagina_pdf"]:03}.png' if item['pagina_pdf'] is not None else f'imagen_{index:04}.png'
            target = salida / name
            encoded_ok, encoded = cv2.imencode('.png', processed)
            if not encoded_ok:
                raise RuntimeError('No se pudo codificar PNG.')
            encoded.tofile(target)
            row.update(estado='ok', imagen=name, ancho=processed.shape[1], alto=processed.shape[0],
                canales=1 if processed.ndim == 2 else 3, parametros=params,
                sha256_origen=digest, sha256=sha(target))
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
        report['paginas'].append(row)
        save()
    report['imagenes_generadas'] = sum(r['estado'] == 'ok' for r in report['paginas'])
    report['paginas_con_error'] = len(items) - report['imagenes_generadas']
    report['estado'] = 'incompleto' if report['paginas_con_error'] or (previous and previous['estado'] != 'completo') else 'completo'
    save()
    return report


def iniciar_selector():
    """Seleccion manual auxiliar; CLI disponible para integrar el flujo."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog
    try:
        root = tk.Tk()
    except tk.TclError:
        text = 'No se pudo iniciar Tcl/Tk. Revise Python o use los comandos del README.'
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, 'Preprocesamiento E1', 0x10)
        return 1
    root.withdraw()
    try:
        source = filedialog.askdirectory(parent=root, title='Carpeta de imagenes de etapa01')
        if not source:
            return 0
        variant = simpledialog.askstring('Variante', 'Elija: ' + ', '.join(VARIANTES),
            initialvalue='original', parent=root)
        if variant is None:
            return 0
        variant = variant.strip()
        if variant not in VARIANTES:
            raise ValueError('Variante invalida. Opciones: ' + ', '.join(VARIANTES))
        destination = filedialog.askdirectory(parent=root, title='Carpeta donde guardar el resultado')
        if not destination:
            return 0
        output = Path(destination) / ('preprocesamiento_' + variant + '_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        # Keep a status window responsive while file processing runs separately.
        from queue import Queue, Empty
        from threading import Thread
        events = Queue()
        root.deiconify()
        root.title('Preprocesamiento E1')
        tk.Label(root, text='Procesando imagenes. Espere el resultado...', padx=30, pady=25).pack()
        root.protocol('WM_DELETE_WINDOW', lambda: messagebox.showinfo('Proceso en curso', 'Espere a que termine.', parent=root))
        def work():
            try:
                events.put((True, procesar(source, output, variant)))
            except Exception as exc:
                events.put((False, str(exc)))
        def receive():
            try:
                ok, result = events.get_nowait()
            except Empty:
                root.after(100, receive)
                return
            if ok:
                notify = messagebox.showinfo if result['estado'] == 'completo' else messagebox.showwarning
                notify('Resultado', f"{result['estado']}: {result['imagenes_generadas']} imagenes; "
                    f"{result['paginas_con_error']} errores.\n{output}", parent=root)
            else:
                messagebox.showerror('Error', result, parent=root)
            root.quit()
        Thread(target=work, daemon=True).start()
        root.after(100, receive)
        root.mainloop()
        return 0
    except Exception as exc:
        messagebox.showerror('Error', str(exc), parent=root)
        return 1
    finally:
        root.destroy()


def main():
    if len(sys.argv) == 1:
        return iniciar_selector()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada', type=Path, required=True)
    parser.add_argument('--salida', type=Path, required=True, help='Carpeta nueva.')
    parser.add_argument('--variante', choices=VARIANTES, default='original')
    args = parser.parse_args()
    try:
        result = procesar(args.entrada, args.salida, args.variante)
    except Exception as exc:
        print(f'No se pudo procesar: {exc}', file=sys.stderr)
        return 1
    print(f"{result['estado']}: {result['imagenes_generadas']} imagenes, {result['paginas_con_error']} errores.")
    return 0 if result['estado'] == 'completo' else 2


if __name__ == '__main__':
    raise SystemExit(main())
