"""Flujo provisional PDF -> imagen -> regiones -> OCR -> formato elegido.

Procesa una pagina a la vez, sin referencias humanas, descargas o entrenamiento.
El detector recibe original; la variante elegida solo cambia la entrada OCR.
"""
import csv
from datetime import datetime, timezone
import html
import io
import json
import os
from pathlib import Path
from queue import Queue, Empty
import re
import shutil
import subprocess
import sys
import tempfile
from threading import Thread

import cv2
import numpy as np
from PIL import Image

from extraccion import seleccionar_paginas
from preprocesamiento import transformar
from nombres import validar_nombre
from recetas import (sha, guardar_json, guardar_imagen, masks, fallback_regions, detectar,
    header_geometry, select_seal, candidates, assign_fields, header, parse_field,
    resolve, enhance, expand, render, inspect_input, reconocer)

BASE = Path(__file__).resolve().parent


def retencion(pdf_hash, number):
    registry=json.loads((BASE/'retenciones.json').read_text(encoding='utf-8'))
    return next((p['motivo'] for p in registry['paginas'] if p['sha256_pdf']==pdf_hash and p['pagina_pdf']==number),None)


class Detector:
    """Un proceso para todos los pesos; permite otro Python sin modificar entornos."""
    def __init__(self, config):
        self.events = Queue()
        self.stderr = tempfile.TemporaryFile(mode='w+', encoding='utf-8')
        self.process = subprocess.Popen([config.get('python_modelo') or sys.executable,
            '-u', str(BASE/'motor_detector.py')], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.stderr, text=True, encoding='utf-8', creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),
            env={**os.environ,'CUBLAS_WORKSPACE_CONFIG':':4096:8'})
        def read():
            for line in self.process.stdout:
                self.events.put(line)
            self.events.put(None)
        Thread(target=read,daemon=True).start()
        try:
            hashes=json.loads((BASE/'modelos.json').read_text(encoding='utf-8'))
            self.info=self.request(dict(**hashes,
                **{'global':config['modelo'], 'carnet':config.get('modelo_carnet')}))
        except Exception:
            self.close()
            raise

    def request(self, value):
        self.process.stdin.write(json.dumps(value)+'\n'); self.process.stdin.flush()
        try:
            line=self.events.get(timeout=300)
        except Empty as exc:
            raise RuntimeError('El detector no respondio dentro de300s.') from exc
        if line is None:
            self.stderr.seek(0)
            raise RuntimeError('El proceso del detector termino: '+self.stderr.read()[-2000:])
        result=json.loads(line)
        if not result['ok']:
            raise RuntimeError('Detector no disponible: '+result['error'])
        return result

    def predict(self, path, name='global'):
        return self.request(dict(imagen=str(path), modelo=name))

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.wait()
        for stream in (self.process.stdin,self.process.stdout,self.stderr):
            if stream:stream.close()


def tesseract(config):
    motor=config.get('tesseract') or shutil.which('tesseract')
    if not motor:
        default=Path(os.environ.get('ProgramFiles',''))/'Tesseract-OCR'/'tesseract.exe'
        motor=str(default) if default.is_file() else None
    if not motor:
        raise RuntimeError('Falta Tesseract; seleccione su ejecutable.')
    version=subprocess.run([motor,'--version'],capture_output=True,text=True,check=True,timeout=30).stdout
    langs=subprocess.run([motor,'--list-langs'],capture_output=True,text=True,check=True,timeout=30).stdout.splitlines()
    if not {'spa','eng'}.issubset({s.strip() for s in langs}):
        raise RuntimeError('Tesseract necesita spa y eng para cuerpo y numeracion.')
    return motor,version


def read_region(image, bbox, folder, identity, motor, psm, threshold):
    """Cuadricula global0,4/margen20; TXT y TSV literales de una invocacion."""
    pixels,mapping=render(image,bbox,'pagina_soporte_bbox',.4)
    path=folder/(identity+'.png');guardar_imagen(path,pixels)
    state=inspect_input(pixels)
    result=dict(bbox=bbox,mapping=mapping,imagen=str(path),sha256=sha(path),psm=psm,
        thresholding_method=threshold,escala=.4,**state,ocr_ejecutado=False,texto_original='',palabras=[])
    if not state['ejecutar_ocr']:
        return result
    base=path.with_suffix('')
    command=[motor,str(path),str(base),'-l','spa','--psm',str(psm),'-c',
        'thresholding_method='+str(threshold),'txt','tsv']
    completed=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',check=True,timeout=60,
        env={**os.environ,'OMP_THREAD_LIMIT':'1'},creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    result.update(comando=command,ocr_ejecutado=True,texto_original=base.with_suffix('.txt').read_text(encoding='utf-8'),
        stderr=completed.stderr,palabras=[dict(texto=r['text'],confianza=float(r['conf'])) for r in
            csv.DictReader(io.StringIO(base.with_suffix('.tsv').read_text(encoding='utf-8')),delimiter='\t')
            if r['level']=='5' and r['text'].strip()])
    return result


def empty_page(number,code='pendiente'):
    return dict(pagina_pdf=number,folio=dict(numero=None,lado=None,origen='no_determinado'),
        papel_seguridad=dict(numero=None,serie=None),actos_mencionados=[],texto=None,
        organizacion_texto=dict(unidad='no_determinada',cantidad=0),
        alertas=[dict(codigo=code,mensaje='No indica que la pagina fuente este vacia.')])


def body(raw,processed,pred,folder,motor,threshold,cancel):
    _,excluded,allowed,boxes=masks(raw.shape,pred,.35)
    protected=np.full_like(processed,255)
    protected[allowed]=processed[allowed]
    guardar_imagen(folder/'protegida.png',protected)
    numbering=detectar(raw,folder/'numeracion',motor)
    physical=numbering['estado']=='propuesta'
    regions=numbering['renglones'] if physical else fallback_regions(allowed)
    rows=[]
    for region in regions:
        row=dict(id=region['id'],renglon_fisico=region.get('renglon_fisico'),bbox=region['bbox'],texto=None)
        if cancel.is_set():
            row['estado']='cancelado';rows.append(row);continue
        x1,y1,x2,y2=row['bbox'];x2=raw.shape[1] if physical else x2
        local=allowed[y1:y2,x1:x2]
        overlap=bool(excluded[y1:y2,x1:x2].any())
        if not local.any():
            row['estado']='excluido' if overlap else 'sin_region_impresa_detectada'
        else:
            ys,xs=np.where(local);bbox=[x1+int(xs.min()),y1,x1+int(xs.max())+1,y2]
            try:
                evidence=read_region(protected,bbox,folder,region['id'],motor,7 if physical else 6,threshold)
                guardar_json(folder/(region['id']+'.json'),evidence)
                row.update(bbox_ocr=bbox,evidencia=region['id']+'.json')
                if not evidence['ocr_ejecutado']:row['estado']='entrada_ocr_blanca'
                else:
                    row['texto']=evidence['texto_original'].strip()
                    row['estado']=('lectura_parcial' if overlap else 'texto_recuperado') if row['texto'] else 'no_reconocido'
            except Exception as exc:row.update(estado='error',error=str(exc))
        rows.append(row)
    return rows,numbering,boxes,allowed


def metadata(raw,boxes,allowed,rows,folder,motor,detector,has_carnet,cancel):
    geometry=header_geometry(raw,boxes)
    safe=np.full_like(raw,255);safe[allowed]=raw[allowed]
    compact,start=candidates(raw.shape,sorted(boxes,key=lambda b:-b['score']))
    details=dict(cuerpo_inicio_predicho=geometry['inicio_cuerpo'],candidatos=compact,ocr_cabecera=[],errores=[],
        carnet=dict(valor=None,estado='no_buscado_sin_modelo'),apertura=header(rows))
    for box in compact:
        if cancel.is_set():break
        try:
            ocr=reconocer(safe,box['bbox'],folder,'cabecera_'+box['id'],motor,'spa',7,1.,60)
            details['ocr_cabecera'].append(dict(id=box['id'],bbox=box['bbox'],**ocr))
        except Exception as exc:details['errores'].append(str(exc))
    details['papel_seguridad']=assign_fields(details['ocr_cabecera'])
    if has_carnet and not cancel.is_set():
        selected,reason=select_seal(raw.shape,boxes,geometry)
        details['seleccion_sello']=reason
        details['carnet']=dict(valor=None,estado=reason)
        if len(selected)==1:
            try:
                parent=selected[0]['bbox'];a,b,c,d=parent
                rgb=cv2.cvtColor(raw[b:d,a:c],cv2.COLOR_BGR2RGB)
                prepared=enhance(rgb,{'clipLimit':1.5,'tileGridSize':[8,8]})
                path=folder/'sello_para_localizador.png';Image.fromarray(prepared).save(path)
                children=[r for r in detector.predict(path,'carnet')['predicciones'] if r['score']>=.35]
                details['propuestas_carnet']=children
                if len(children)==1:
                    h,w=prepared.shape[:2];p=children[0]['bbox']
                    box=[max(0,int(np.floor(p[0]))),max(0,int(np.floor(p[1]))),min(w,int(np.ceil(p[2]))),min(h,int(np.ceil(p[3])))]
                    if not ((box[2]-box[0])>=.15*w and 0<box[3]-box[1]<=.3*h):
                        raise ValueError('Subregion de carnet incompatible.')
                    box=expand(box,w,h,.5,.15)
                    if box[2]-box[0]>.75*w or box[3]-box[1]>.4*h:
                        raise ValueError('Expansion excesiva; no leer sello completo.')
                    ocr=reconocer(cv2.cvtColor(prepared,cv2.COLOR_RGB2BGR),box,folder,'carnet',motor,'spa',7,
                        min(3.,max(1.,48/(box[3]-box[1]))),60)
                    value=parse_field('carnet',ocr['texto_original'])
                    details['carnet']=dict(valor=value,estado='lectura_no_verificada' if value else 'no_reconocido',
                        bbox_local=box,bbox_sello=parent,ocr=ocr)
            except Exception as exc:details['carnet']=dict(valor=None,estado='error',error=str(exc))
    return details


def page_html(page,path,previous=None,following=None):
    links=' '.join(f'<a href="page_{n:03}.html">Pagina {n}</a>' for n in (previous,following) if n is not None)
    path.write_text('<!doctype html><meta charset="utf-8"><title>Pagina '+str(page['pagina_pdf'])+'</title>'
        '<style>body{font:17px sans-serif;max-width:1000px;margin:30px auto}pre{white-space:pre-wrap}a{margin:10px}</style>'
        '<p><a href="../index.html">Indice</a>'+links+'</p><h1>Pagina PDF '+str(page['pagina_pdf'])+'</h1>'
        '<p>Lectura experimental; consulte alertas y evidencia.</p><pre>'+html.escape(page['texto'] or '[Sin texto publicado]')
        +'</pre><details><summary>Campos y alertas</summary><pre>'+html.escape(json.dumps({k:v for k,v in page.items() if k!='texto'},ensure_ascii=False,indent=2))+'</pre></details>',encoding='utf-8')


def run(config,progress,cancel,detector_factory=Detector):
    import pymupdf
    if config.get('variante','original') not in ('original','gris','clahe_gamma','vertical_1x3'):
        raise ValueError('Variante OCR no admitida.')
    if config.get('binarizacion','otsu') not in ('otsu','sauvola'):
        raise ValueError('Binarizacion no admitida.')
    pdf=Path(config['pdf']);output=Path(config['salida'])
    json_name=validar_nombre(config.get('nombre_json') or 'resultado_pendiente.json')
    if output.exists():raise FileExistsError('La carpeta de salida ya existe.')
    with pymupdf.open(pdf) as doc:
        if not doc.is_pdf or doc.needs_pass or not doc.page_count:raise ValueError('PDF ilegible, vacio o protegido.')
        selected=seleccionar_paginas(config.get('paginas') or None,doc.page_count)
    motor,version=tesseract(config)
    progress('Comprobando detector y modelos antes de extraer el PDF...',0,len(selected))
    detector=detector_factory(config)
    try:
        output.mkdir(parents=True)
        (output/'paginas').mkdir()
        source_hash=sha(pdf)
        result=dict(version_esquema='propuesta_tomo_02',tipo='tomo',tomo_id=None,numero_tomo=None,
            notario=dict(nombre=None,carne=None),total_paginas_incluidas=len(selected),paginas=[empty_page(n) for n in selected])
        report=dict(estado='en_proceso',fecha_utc=datetime.now(timezone.utc).isoformat(),
            fuente=dict(archivo=pdf.name,sha256=source_hash,paginas_seleccionadas=selected),
            configuracion={k:config.get(k) for k in ('variante','binarizacion','guardar_txt')},
            archivo_json=json_name,nombre_json_origen='etiqueta_tecnica_configurada' if config.get('nombre_json') else 'pendiente_por_falta_de_etiqueta',
            version_tesseract=version,detector=detector.info,paginas=[],cabecera={},
            limitacion='Experimental: cajas imperfectas, posibles residuos/cortes; sin selector automatico de claridad validado.')
        numbers=[];names=[];cards=[];folios=[]
        def save():
            guardar_json(output/json_name,result);guardar_json(output/'ejecucion.json',report)
        save()
        with pymupdf.open(pdf) as doc:
            for index,number in enumerate(selected):
                if cancel.is_set():break
                progress(f'Pagina {number}: extraccion y segmentacion',index,len(selected))
                folder=output/'paginas'/f'page_{number:03}';folder.mkdir()
                detail=dict(pagina_pdf=number,estado='en_proceso')
                page=empty_page(number,'error_pagina')
                try:
                    image_path=folder/'original.png'
                    pix=doc[number-1].get_pixmap(dpi=300,colorspace=pymupdf.csRGB,alpha=False,annots=True);pix.save(image_path);del pix
                    raw=cv2.imdecode(np.fromfile(image_path,np.uint8),1)
                    predicted=detector.predict(image_path)
                    guardar_json(folder/'detecciones.json',predicted)
                    processed,params=transformar(raw,config.get('variante','original'))
                    if processed.ndim==2:processed=cv2.cvtColor(processed,cv2.COLOR_GRAY2BGR)
                    guardar_imagen(folder/'procesada.png',processed)
                    progress(f'Pagina {number}: OCR y campos',index,len(selected))
                    hold=retencion(source_hash,number)
                    if hold:
                        _,_,allowed,boxes=masks(raw.shape,predicted['predicciones'],.35)
                        rows=[];numbering=dict(estado='retenido',renglones=[],motivo=hold)
                    else:
                        rows,numbering,boxes,allowed=body(raw,processed,predicted['predicciones'],folder,motor,
                            2 if config.get('binarizacion')=='sauvola' else 0,cancel)
                    meta=metadata(raw,boxes,allowed,rows,folder,motor,detector,bool(config.get('modelo_carnet')),cancel)
                    physical=numbering['estado']=='propuesta'
                    text='\n'.join(r.get('texto') or '' for r in rows) if any(r.get('texto') is not None for r in rows) else None
                    page=empty_page(number)
                    page.update(texto=text,papel_seguridad={k:meta['papel_seguridad'][k] for k in ('numero','serie')},
                        organizacion_texto=dict(unidad='renglon_fisico' if physical else 'region_propuesta',cantidad=len(rows)),
                        alertas=[dict(codigo='flujo_provisional',mensaje='Posibles omisiones, cortes y manuscritos residuales; no garantiza exactitud.'),
                            dict(codigo='actos_no_extraidos',mensaje='Lista vacia no indica ausencia de actos.'),
                            dict(codigo='carnet_'+meta['carnet']['estado'],mensaje='Lectura de carnet limitada al recorte especifico.')])
                    if not physical:page['alertas'].append(dict(codigo='numeracion_no_resuelta',mensaje='Regiones sin numero fisico; no se inventan30renglones.'))
                    if hold:
                        page['organizacion_texto']=dict(unidad='cuerpo_retenido',cantidad=0)
                        page['alertas'].append(dict(codigo='retencion_conservada',mensaje=hold))
                    for row in rows:
                        if row['estado']!='texto_recuperado':page['alertas'].append(dict(codigo=row['estado'],region_id=row['id'],bbox=row['bbox']))
                    openings=meta['apertura']
                    if openings['numero_tomo'] is not None:numbers.append(openings['numero_tomo'])
                    if openings['nombre']:names.append(openings['nombre'])
                    for match in re.finditer(r'\bAnte m[\u00edi],?\s+([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1 ]{5,80})\s+Notario P[\u00fau]blico',text or ''):
                        names.append(match.group(1).strip())
                    if meta['carnet']['valor']:cards.append(meta['carnet']['valor'])
                    meta.update(pagina_pdf=number,sha256_pdf=source_hash,dimensiones=[raw.shape[1],raw.shape[0]])
                    folios.append(meta)
                    detail.update(estado='procesado_experimental',sha256_imagen=sha(image_path),dimensiones=[raw.shape[1],raw.shape[0]],
                        preprocesamiento=params,renglones=rows,numeracion=numbering,metadatos=meta,
                        regiones_no_transcritas=[b for b in boxes if b['label'] in (2,3)])
                    if any(r['estado'] in ('error','cancelado') for r in rows) or meta['errores'] or meta['carnet']['estado']=='error':
                        detail['estado']='incompleto'
                    if hold:detail.update(estado='retenido',retencion=hold)
                    for error in meta['errores']:
                        page['alertas'].append(dict(codigo='error_ocr_cabecera',mensaje=error))
                    del raw,processed,allowed
                except Exception as exc:
                    detail.update(estado='error',error=f'{type(exc).__name__}: {exc}')
                    page['alertas'].append(dict(codigo='error_pagina',mensaje=detail['error']))
                result['paginas'][index]=page
                guardar_json(folder/'evidencia.json',detail)
                report['paginas'].append(dict(pagina_pdf=number,estado=detail['estado'],evidencia=f'paginas/page_{number:03}/evidencia.json'))
                save();progress(f'Pagina {number} terminada',index+1,len(selected))
        for index in range(len(report['paginas']),len(selected)):
            result['paginas'][index]=empty_page(selected[index],'cancelado')
        resolved=resolve(folios)
        by_number={r['pagina_pdf']:r for r in resolved}
        for page in result['paginas']:
            if page['pagina_pdf'] in by_number:page['folio']=by_number[page['pagina_pdf']]['folio']
            if page['folio']['numero'] is None:page['alertas'].append(dict(codigo='folio_no_resuelto',mensaje='No se infiere folio por posicion PDF.'))
        for values,key in ((numbers,'numero_tomo'),(names,'nombre'),(cards,'carne')):
            unique=list(dict.fromkeys(values));report['cabecera'][key]=dict(candidatos=unique,estado='lecturas_en_conflicto' if len(unique)>1 else 'leido_ocr_no_verificado' if unique else 'no_reconocido')
            if len(unique)==1:
                if key=='numero_tomo':result.update(numero_tomo=unique[0],tomo_id=f'tomo_{unique[0]:02d}')
                else:result['notario'][key]=unique[0]
            elif len(unique)>1:
                for page in result['paginas']:page['alertas'].append(dict(codigo='conflicto_'+key,mensaje='Lecturas discrepantes; campo nulo.'))
        report['estado']='cancelado' if cancel.is_set() else 'incompleto' if any(p['estado'] in ('error','incompleto','retenido') for p in report['paginas']) else 'finalizado_experimental'
        report['resultado']='parcial_no_certificado'
        guardar_json(output/'evidencia_folios.json',resolved)
        save()
        for index,page in enumerate(result['paginas']):
            page_html(page,output/'paginas'/f'page_{page["pagina_pdf"]:03}.html',selected[index-1] if index else None,selected[index+1] if index+1<len(selected) else None)
        links=''.join('<li><a href="paginas/page_'+f'{p["pagina_pdf"]:03}'+'.html">Pagina PDF '+str(p['pagina_pdf'])+'</a></li>' for p in result['paginas'])
        (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Resultado E1</title><h1>Resultado provisional</h1>'
            '<p>'+html.escape(report['estado'])+'; revisar alertas. Sin garantia de exactitud.</p><p><a href="'+json_name+'">JSON completo</a></p><ol>'+links+'</ol>',encoding='utf-8')
        if config.get('guardar_txt'):
            with (output/'revision.txt').open('w',encoding='utf-8') as stream:
                for page in result['paginas']:
                    stream.write(f'\n=== Pagina PDF {page["pagina_pdf"]} ===\n'+(page['texto'] or '[Sin texto publicado; consultar alertas]')+'\n')
        return dict(salida=str(output),estado=report['estado'],paginas=len(selected),json=str(output/json_name),visor=str(output/'index.html'))
    finally:
        detector.close()
