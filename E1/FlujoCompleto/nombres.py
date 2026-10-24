"""Nombres tecnicos de salida; nunca completan los campos documentales del JSON."""
from pathlib import Path
import re
import unicodedata


def etiqueta_notario(name):
    ascii_name=unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode('ascii')
    words=re.findall(r'[A-Za-z0-9]+',ascii_name)
    if not words:raise ValueError('Falta la etiqueta del notario.')
    return ''.join(word[:1].upper()+word[1:].lower() for word in words)


def nombre_tomo(number,notary):
    if isinstance(number,bool) or not str(number).isdigit() or int(number)<1:
        raise ValueError('El numero de tomo debe ser un entero positivo.')
    return validar_nombre(f'tomo{int(number):02d}_{etiqueta_notario(notary)}.json')


def nombre_indice(period,notary):
    """Periodo proporcionado, no deducido de fechas de registros."""
    if not re.fullmatch(r'[0-9]{4}(?:-[0-9]{4}|-(?:0[1-9]|1[0-2])(?:-Q[12])?)?',period):
        raise ValueError('Periodo: AAAA, AAAA-AAAA, AAAA-MM o AAAA-MM-Q1/Q2.')
    if int(period[:4])<1 or (len(period)==9 and int(period[-4:])<int(period[:4])):
        raise ValueError('Rango de periodo invalido.')
    return validar_nombre(f'indice{period}_{etiqueta_notario(notary)}.json')


def validar_nombre(name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,150}\.json',name):
        raise ValueError('Use un nombre .json sin rutas, espacios ni tildes; ejemplo tomo08_LeninRojas.json.')
    stem=name[:-5]
    if name.lower() in ('ejecucion.json','evidencia_folios.json') or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])',stem):
        raise ValueError('Nombre reservado; elija otro para el contenido.')
    return name


def sugerir_desde_pdf(path):
    """Sugerencia editable desde etiqueta de entrada; no es lectura OCR verificada."""
    match=re.fullmatch(r'\s*tomo[\s_-]*([0-9]+)[\s_-]+(.+?)\s*',Path(path).stem,re.I)
    if match:
        try:return nombre_tomo(match.group(1),match.group(2))
        except ValueError:pass
    return 'resultado_pendiente.json'
