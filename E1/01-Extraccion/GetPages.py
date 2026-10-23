"""Renderiza paginas PDF como PNG locales; etapa 01 del modulo E1.

Adaptacion Experimental usa PyMuPDF y 300 DPI por
defecto, con parametros de entrada.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def seleccionar_paginas(expression, total):
    """Indices humanos desde 1; devuelve seleccion ordenada sin duplicados."""
    if expression is None:
        return list(range(1, total + 1))
    selected = set()
    for item in expression.split(','):
        limits = item.strip().split('-')
        if len(limits) not in (1, 2) or any(not v.strip().isdigit() for v in limits):
            raise ValueError('Paginas invalidas; use por ejemplo 1,3-5.')
        first, last = int(limits[0]), int(limits[-1])
        if not 1 <= first <= last <= total:
            raise ValueError(f'Rango {item!r} fuera de las paginas 1 a {total}.')
        selected.update(range(first, last + 1))
    return sorted(selected)


def extraer(pdf, salida, tipo, paginas=None, dpi=300):
    """Devuelve manifiesto; no sobrescribe salidas ni omite fallos de paginas."""
    try:
        import pymupdf
    except ImportError as exc:
        raise RuntimeError('Falta PyMuPDF. Instale requirements.txt con el mismo Python.') from exc
    if dpi <= 0 or tipo not in ('tomo', 'indice'):
        raise ValueError('DPI debe ser positivo y tipo debe ser tomo o indice.')
    pdf, salida = Path(pdf), Path(salida)
    source_hash = sha256(pdf)
    # Opening and validating happen before any output folder is created.
    with pymupdf.open(pdf) as document:
        if not document.is_pdf:
            raise ValueError('La entrada no es un PDF.')
        if document.needs_pass:
            raise ValueError('PDF protegido con contrasena; no se puede abrir para extraer.')
        if document.page_count == 0:
            raise ValueError('PDF sin paginas.')
        selected = seleccionar_paginas(paginas, document.page_count)
        salida.mkdir(parents=True, exist_ok=False)
        manifest = dict(etapa='extraccion', estado='en_proceso',
            fecha_utc=datetime.now(timezone.utc).isoformat(), tipo=tipo,
            fuente=dict(archivo=pdf.name, sha256=source_hash, paginas_totales=document.page_count),
            configuracion=dict(dpi=dpi, formato='PNG', color='RGB', alpha=False,
                anotaciones_pdf=True, paginas_seleccionadas=selected),
            pymupdf_version=pymupdf.VersionBind, paginas=[])

        def guardar():
            (salida / 'manifest.json').write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

        guardar()
        for number in selected:
            record = dict(pagina_pdf=number)
            image = salida / f'page_{number:03}.png'
            try:
                page = document[number - 1]
                pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False, annots=True)
                pixmap.save(image)
                record.update(estado='ok', imagen=image.name, ancho=pixmap.width,
                    alto=pixmap.height, sha256=sha256(image))
            except Exception as exc:
                record.update(estado='error', error=f'{type(exc).__name__}: {exc}')
                if image.exists():
                    record['archivo_posiblemente_incompleto'] = image.name
            manifest['paginas'].append(record)
            guardar()
        manifest['estado'] = 'completo' if all(p['estado'] == 'ok' for p in manifest['paginas']) else 'incompleto'
        manifest['paginas_extraidas'] = sum(p['estado'] == 'ok' for p in manifest['paginas'])
        manifest['paginas_con_error'] = len(selected) - manifest['paginas_extraidas']
        guardar()
    return manifest


def main():
    if len(sys.argv) == 1:
        from selector_pdf import iniciar
        return iniciar()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--salida', type=Path, required=True, help='Carpeta nueva; no puede existir.')
    parser.add_argument('--tipo', choices=('tomo', 'indice'), required=True)
    parser.add_argument('--paginas', help='Numeros PDF desde 1, por ejemplo 1,3-5. Omitir para todas.')
    parser.add_argument('--dpi', type=int, default=300)
    args = parser.parse_args()
    try:
        result = extraer(args.pdf, args.salida, args.tipo, args.paginas, args.dpi)
    except Exception as exc:
        print(f'No se pudo ejecutar la extraccion: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    print(f"Estado: {result['estado']}. Paginas extraidas: {result['paginas_extraidas']}; "
          f"con error: {result['paginas_con_error']}. Manifiesto: {args.salida / 'manifest.json'}")
    return 0 if result['estado'] == 'completo' else 2


if __name__ == '__main__':
    raise SystemExit(main())
