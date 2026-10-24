"""Recetas reutilizadas de experimentos E1; procedencia en procedencia_recetas.json."""

import csv, io, json, math, re, subprocess, time, hashlib

from pathlib import Path

import cv2

import numpy as np

def guardar_json(path, value):
    """Reemplazo atomico del registro de esta ejecucion; nunca pisa otra corrida."""
    temporal = path.with_suffix(".tmp")
    temporal.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporal.replace(path)

def guardar_imagen(path, image):
    ok, data = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(f"No se pudo codificar {path}")
    data.tofile(path)

def reconocer(image, bbox, folder, identifier, motor, language, psm, scale, timeout):
    """Conserva texto y TSV de una misma invocacion; confianza no valida exactitud."""
    x1, y1, x2, y2 = bbox
    crop = image[y1:y2, x1:x2]
    resized = cv2.resize(crop, (max(1, round(crop.shape[1]*scale)), max(1, round(crop.shape[0]*scale))),
                         interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    padded = cv2.copyMakeBorder(resized, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    path = folder / f"{identifier}.png"
    guardar_imagen(path, padded)
    output = folder / identifier
    command = [motor, str(path), str(output), "-l", language, "--psm", str(psm), "txt", "tsv"]
    input_status = inspect_input(padded)
    if not input_status['ejecutar_ocr']:
        # Se conserva PNG y comando planificado; no hay OCR original nuevo.
        # Cadena vacia mantiene compatibilidad, estado explicito evita llamarla vacio.
        return {"texto_original": "", "palabras": [], "comando": command,
                "comando_ejecutado": False, "ocr_ejecutado": False, "estado_entrada": input_status['estado_entrada'],
                "ocupacion_fuente": "no_determinada", "stderr": "", "segundos": 0,
                "recorte": str(path), "psm": psm, "escala": scale,
                "dimensiones_ocr_sin_margen": [resized.shape[1], resized.shape[0]], "margen": 20}
    start = time.perf_counter()
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=timeout, check=True)
    text = output.with_suffix(".txt").read_text(encoding="utf-8")
    tsv = output.with_suffix(".tsv").read_text(encoding="utf-8")
    words = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
        if row["level"] != "5" or not row["text"].strip():
            continue
        left, top, width, height = (int(row[key]) for key in ("left", "top", "width", "height"))
        # Usa escala efectiva tras redondear las dimensiones, con limites originales.
        sx, sy = resized.shape[1]/crop.shape[1], resized.shape[0]/crop.shape[0]
        words.append({"texto": row["text"], "confianza": float(row["conf"]),
                      "bbox": [max(x1, round(x1+(left-20)/sx)), max(y1, round(y1+(top-20)/sy)),
                               min(x2, round(x1+(left+width-20)/sx)), min(y2, round(y1+(top+height-20)/sy))]})
    return {"texto_original": text, "palabras": words, "comando": command,
            "comando_ejecutado": True, "ocr_ejecutado": True, "estado_entrada": input_status['estado_entrada'],
            "stderr": result.stderr, "segundos": round(time.perf_counter()-start, 3),
            "recorte": str(path), "psm": psm, "escala": scale,
            "dimensiones_ocr_sin_margen": [resized.shape[1], resized.shape[0]], "margen": 20}

def masks(shape, predictions, threshold):
    """Unión de impresos menos exclusiones; evita transcribir duplicados de cajas."""
    h, w = shape[:2]
    printed = np.zeros((h, w), dtype=bool)
    excluded = np.zeros_like(printed)
    boxes = []
    for index, obj in enumerate(predictions):
        if obj['score'] < threshold:
            continue
        b = obj['bbox']
        x1, y1 = max(0, int(np.floor(b[0]))), max(0, int(np.floor(b[1])))
        x2, y2 = min(w, int(np.ceil(b[2]))), min(h, int(np.ceil(b[3])))
        if not 0 <= x1 < x2 <= w or not 0 <= y1 < y2 <= h:
            raise ValueError('Caja predicha fuera de dimensiones válidas.')
        if obj['label'] not in (1, 2, 3):
            raise ValueError('Clase desconocida.')
        target = printed if obj['label'] == 1 else excluded
        target[y1:y2, x1:x2] = True
        boxes.append(dict(id=f'deteccion_{index:03d}', bbox=[x1,y1,x2,y2], **{
            'label':obj['label'], 'score':obj['score']}))
    return printed, excluded, printed & ~excluded, boxes

def fallback_regions(allowed):
    """Componentes de la unión de cajas, sin inventar numeración física."""
    count, _, stats, _ = cv2.connectedComponentsWithStats(allowed.astype(np.uint8))
    boxes = sorted(([int(x),int(y),int(x+w),int(y+h)]
                    for x,y,w,h,area in stats[1:] if area > 0), key=lambda b:(b[1],b[0]))
    return [dict(id=f'region_{i:03d}', renglon_fisico=None, bbox=b,
                 metodo='union_predicciones_impreso_menos_exclusiones') for i,b in enumerate(boxes,1)]

def candidatos(image):
    """Localiza componentes morados pequenos en la zona izquierda de la hoja."""
    if image.ndim != 3:
        raise ValueError("Este detector necesita imagen en color; no se ha validado en grises.")
    h, w = image.shape[:2]
    b, g, r = cv2.split(image.astype(np.int16))
    mask = ((r-g > 15) & (b-g > 5) & (g < 190)).astype(np.uint8)*255
    mask[:, round(w*0.35):] = 0
    joined = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (max(2, round(w*0.008)), 1)))
    _, _, stats, _ = cv2.connectedComponentsWithStats(joined)
    boxes = [[int(x), int(y), int(x+width), int(y+height)] for x, y, width, height, area in stats[1:]
             if h*0.003 < height < h*0.02 and w*0.002 < width < w*0.05 and area > h*w*0.000003]
    return sorted(boxes, key=lambda box: box[1])

def bandas_desde_etiquetas(labels, width, height, expected=30):
    """No asigna numeros por posicion: exige lectura de cada etiqueta 1..N."""
    if len(labels) != expected or [item["numero"] for item in labels] != list(range(1, expected+1)):
        raise ValueError("No se reconocio una secuencia completa y ordenada; no se fuerzan renglones.")
    centers = np.array([(item["bbox"][1]+item["bbox"][3])/2 for item in labels])
    gaps = np.diff(centers)
    step = float(np.median(gaps))
    if step <= 0 or np.max(np.abs(gaps-step))/step > 0.2:
        raise ValueError("Espaciado irregular: revisar etiquetas; no se extrapolan bandas.")
    rights = np.array([item["bbox"][2] for item in labels])
    if np.ptp(rights) > width*0.05:
        raise ValueError("Etiquetas sin alineacion de margen compatible.")
    borders = np.rint(np.r_[centers[0]-step/2, (centers[:-1]+centers[1:])/2, centers[-1]+step/2]).astype(int)
    if borders[0] < 0 or borders[-1] > height or np.any(np.diff(borders) <= 0):
        raise ValueError("Bandas fuera de la imagen.")
    # Limite izquierdo despues de numeracion. Derecho conservador hasta borde:
    # evita cortar texto inclinado; no se presenta como deteccion de la regla derecha.
    margin = max(2, round(np.median([item["bbox"][3]-item["bbox"][1] for item in labels])*0.25))
    # Limite local por renglon: un maximo global puede cortar iniciales cuando
    # el margen se desplaza con la inclinacion de la pagina.
    rows = [{"id": f"renglon_{item['numero']:03d}", "renglon_fisico": item["numero"],
             "bbox": [item["bbox"][2]+margin, int(borders[i]), width, int(borders[i+1])],
             "metodo": "numeracion_morada_ocr", "bbox_numero": item["bbox"]} for i, item in enumerate(labels)]
    return {"cuerpo_bbox": [min(row["bbox"][0] for row in rows), int(borders[0]), width, int(borders[-1])], "renglones": rows,
            "espaciado_mediano": step,
            "limites": "Vertical desde etiquetas; izquierdo desde margen; derecho conservador al borde de imagen."}

def limite_derecho(image, body, label_height):
    """Estima envolvente de tinta con dimensiones de glifos, sin reconocer texto.

    Excluye componentes altos/anchos como perforaciones. No clasifica manuscritos
    ni detecta una regla: la envolvente puede incluirlos y requiere inspeccion.
    """
    x1,y1,_,y2 = body
    width = image.shape[1]
    gray = cv2.cvtColor(image[y1:y2,x1:],cv2.COLOR_BGR2GRAY)
    threshold,ink = cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    _,_,stats,_ = cv2.connectedComponentsWithStats(ink)
    boxes = [[int(x),int(y),int(w),int(h)] for x,y,w,h,area in stats[1:]
             if label_height*0.5 <= h <= label_height*2.5 and 1 < w <= h*2
             and area >= h*w*0.15]
    info = {"metodo":"envolvente_componentes_tinta", "umbral_otsu":threshold,
            "componentes":len(boxes), "altura_relativa":[0.5,2.5],"aspecto_max":2,
            "ocupacion_min":0.15,"margen_altura_relativa":0.5}
    if len(boxes) < 50:
        return width,{**info,"estado":"sin_evidencia_suficiente","limite":width}
    right = min(width,max(x+w for x,y,w,h in boxes)+x1+round(label_height*0.5))
    return right,{**info,"estado":"propuesta","limite":right}

def detectar(image, folder, motor, expected=30):
    """Reconoce solo recortes de etiquetas candidatas, no OCR del cuerpo."""
    all_boxes = candidatos(image)
    selection = select_column(all_boxes, image.shape[1], COLUMN_PARAMS)
    boxes = [all_boxes[i] for i in selection["seleccionados"]]
    labels = []
    folder.mkdir(parents=True, exist_ok=True)
    h, w = image.shape[:2]
    typical_height = float(np.median([box[3]-box[1] for box in boxes])) if boxes else 0
    for i, bbox in enumerate(boxes, 1):
        x1, y1, x2, y2 = bbox
        # Componentes de tinta fuerte pueden omitir partes tenues del mismo digito.
        # Margen basado en altura mediana, no en el valor esperado del numero.
        padding = max(2, round(typical_height*0.6))
        crop = image[max(0,y1-padding):min(h,y2+padding), max(0,x1-padding):min(w,x2+padding)]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        enlarged = cv2.resize(binary, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
        padded = cv2.copyMakeBorder(enlarged,20,20,20,20,cv2.BORDER_CONSTANT,value=255)
        path = folder / f"numero_{i:03d}.png"
        ok, data = cv2.imencode(".png", padded)
        if not ok:
            raise ValueError("No se pudo guardar recorte de numero.")
        data.tofile(path)
        psm = "7" if x2-x1 > typical_height else "8"
        # Modelos fijos por geometria: nunca se elige una lectura por el numero
        # que le corresponderia en la secuencia. El cuerpo sigue usando spa.
        language = "eng" if psm == "7" else "spa"
        command = [motor,str(path),"stdout","-l",language,"--psm",psm,"-c","tessedit_char_whitelist=0123456789"]
        result = subprocess.run(command,capture_output=True,text=True,encoding="utf-8",check=True,timeout=30) if inspect_input(padded)["ejecutar_ocr"] else type("EmptyOCR", (), {"stdout":"", "stderr":""})()
        path.with_suffix(".txt").write_text(result.stdout,encoding="utf-8")
        value = result.stdout.strip()
        labels.append({"bbox": bbox, "numero": int(value) if value.isdigit() else None,
                       "ocr_original": result.stdout, "comando": command, "stderr": result.stderr})
    record = {"columna": selection, "etiquetas": labels, "parametros": {"r_menos_g":15,"b_menos_g":5,"g_max":190,
              "zona_izquierda_relativa":0.35,"union_horizontal_relativa":0.008,"cantidad_esperada":expected,
              "margen_altura_mediana":0.6,"escala_ocr":3,"idiomas_segun_ancho":"eng ancho; spa estrecho",
              "psm_segun_ancho": "7 si ancho supera altura mediana; 8 en otro caso"},
              "sha256_segmentador":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        record.update(bandas_desde_etiquetas(labels,w,h,expected), estado="propuesta")
        right,info = limite_derecho(image,record["cuerpo_bbox"],typical_height)
        record["limite_derecho"] = info
        record["cuerpo_bbox"][2] = right
        for row in record["renglones"]:
            row["bbox"][2] = right
        record["limites"] = "Vertical desde etiquetas; izquierdo local por renglon; derecho por envolvente de tinta compatible con glifos. Propuesta sin validacion."
    except ValueError as error:
        record.update(estado="no_resuelto", error=str(error), renglones=[])
    (folder / "deteccion.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    return record

def select_column(boxes, width, params):
    """Agrupa por extremo derecho con dispersion acotada, sin encadenamiento.

    Un grupo plausible requiere cantidad y paso regular; el OCR no interviene.
    Los indices preservan trazabilidad de candidatos seleccionados y descartados.
    """
    groups=[]
    for index in sorted(range(len(boxes)),key=lambda i:(boxes[i][2],boxes[i][1],i)):
        right=boxes[index][2]
        if not groups or right-boxes[groups[-1][0]][2]>params['dispersion_derecha_relativa']*width:
            groups.append([index])
        else:groups[-1].append(index)
    records=[]
    for group in groups:
        ordered=sorted(group,key=lambda i:boxes[i][1]);centers=np.array([(boxes[i][1]+boxes[i][3])/2 for i in ordered])
        gaps=np.diff(centers);step=float(np.median(gaps)) if len(gaps) else 0
        deviation=float(np.max(np.abs(gaps-step))/step) if step>0 else None
        enough=params['candidatos_min']<=len(group)<=params['candidatos_max']
        regular=deviation is not None and deviation<=params['desviacion_paso_max']
        records.append(dict(indices=ordered,cantidad=len(group),paso=step,desviacion_paso=deviation,
            plausible=bool(enough and regular),razon='plausible' if enough and regular else 'cantidad' if not enough else 'paso_irregular'))
    plausible=[g for g in records if g['plausible']]
    chosen=plausible[0]['indices'] if len(plausible)==1 else []
    return dict(estado='columna_unica' if len(plausible)==1 else 'columnas_ambiguas' if len(plausible)>1 else 'sin_columna_plausible',
        seleccionados=chosen,descartados=[i for i in range(len(boxes)) if i not in chosen],grupos=records)

def validate_labels(labels, width, height, params):
    """Primero geometria; despues lecturas completas, sin completar ni corregir."""
    selection=select_column([r['bbox'] for r in labels],width,params)
    result=dict(seleccion=selection,renglones=[],estado='no_resuelto')
    if selection['estado']!='columna_unica':
        result['error']=selection['estado'];return result
    selected=[labels[i] for i in selection['seleccionados']]
    try:result.update(bandas_desde_etiquetas(selected,width,height),estado='propuesta')
    except ValueError as exc:result['error']=str(exc)
    return result

def number_literal(literal):
    """Conversión técnica explícita; nunca modifica el literal conservado."""
    words={'UNO':1,'DOS':2,'TRES':3,'CUATRO':4,'CINCO':5,'SEIS':6,'SIETE':7,'OCHO':8,'NUEVE':9,'DIEZ':10}
    return int(literal) if literal.isdigit() else words.get(literal.upper())

def header(rows):
    """Busca tomo y notario solamente en la razón explícita de apertura."""
    text=' '.join((r.get('texto') or '') for r in rows)
    tomo=re.search(r'\bTOMO\s+n[úu]mero\s+(\d+|[A-ZÁÉÍÓÚÑ]+)\b',text,re.I)
    name=re.search(r'\bautoriza al Notario\s+P[úu]blico\s+([^,;\n]+),\s+quien\s+tambi[ée]n',text,re.I)
    literal=tomo.group(1) if tomo else None
    return dict(tomo_literal=literal,numero_tomo=number_literal(literal) if literal else None,
                nombre=name.group(1).strip() if name else None,fragmento_ocr=text)

def parse_field(field,text):
    patterns={'rotulo_numerico':r'(?i)^\s*NO\.?\s*([0-9]+)\s*$',
        'numero_papel':r'(?i)^\s*NO\.?\s*([0-9][0-9 ]*)\s*$',
        'serie':r'^\s*([A-Z]\s*[0-9]+)\s*$',
        'carnet':r'(?i)^\s*C\.?\s*([0-9]+)\s*$'}
    match=re.search(patterns[field],text)
    return re.sub(r'\s+','',match.group(1)) if match else None

def candidates(shape, boxes):
    """Cabeceras compactas anteriores al cuerpo alto predicho; regla geométrica fija."""
    h,w=shape[:2]
    tall=[b for b in boxes if b['label']==1 and b['bbox'][3]-b['bbox'][1]>=.35*h]
    if not tall:
        return [],None
    start=min(b['bbox'][1] for b in tall)
    found=[]
    for box in boxes:
        x1,y1,x2,y2=box['bbox']
        if box['label']==1 and y2<=start and y2-y1<=.06*h and x2-x1<=.5*w:
            # Una caja puede repetirse: conservar solo la de mayor score si IoU>=.8.
            if not any(iou(box['bbox'],old['bbox'])>=.8 for old in found):
                found.append(box)
    return sorted(found,key=lambda b:(b['bbox'][1],b['bbox'][0])),start

def assign_fields(readings):
    """Papel requiere rótulo NO y serie vecina a la derecha, sin valores esperados."""
    pairs=[]
    for left in readings:
        value=parse_field('numero_papel',left.get('texto_original',''))
        if not value:
            continue
        a,b,c,d=left['bbox']
        for right in readings:
            series=parse_field('serie',right.get('texto_original',''))
            x,y,z,t=right['bbox']
            overlap=max(0,min(d,t)-max(b,y))
            if series and x>=c and x-c<=2*(c-a) and overlap>=.5*min(d-b,t-y):
                pairs.append(dict(numero=value,serie=series,regiones=[left['id'],right['id']]))
    values=list(dict.fromkeys((p['numero'],p['serie']) for p in pairs))
    return dict(numero=values[0][0] if len(values)==1 else None,
                serie=values[0][1] if len(values)==1 else None,
                estado='leido_ocr_no_verificado' if len(values)==1 else 'lecturas_en_conflicto' if values else 'no_resuelto',
                candidatos=pairs)

def header_geometry(image,boxes):
    h,w=image.shape[:2]
    labels=candidatos(image)
    groups=[]
    for box in labels:
        cx=(box[0]+box[2])/2
        if cx>.25*w:
            continue
        group=next((g for g in groups if abs(cx-np.median([(b[0]+b[2])/2 for b in g]))<=.025*w),None)
        if group is None:
            groups.append([box])
        else:
            group.append(box)
    valid=[]
    for group in groups:
        ordered=sorted(group,key=lambda b:b[1])
        if not 20<=len(ordered)<=35:
            continue
        centers=np.array([(b[1]+b[3])/2 for b in ordered]);gaps=np.diff(centers)
        step=float(np.median(gaps))
        if step>0 and float(np.max(np.abs(gaps-step))/step)<=.25:
            valid.append((len(ordered),float(centers[0]-step/2),ordered,step))
    if valid:
        _,start,column,step=max(valid,key=lambda x:x[0])
        return dict(inicio_cuerpo=start,metodo='columna_geometrica_morada_sin_lectura',etiquetas=column,paso=step)
    broad=[b for b in boxes if b['label']==1 and b['bbox'][2]-b['bbox'][0]>=.5*w
           and b['bbox'][3]-b['bbox'][1]>=.12*h]
    if not broad:
        return dict(inicio_cuerpo=None,metodo='sin_evidencia')
    chosen=max(broad,key=lambda b:b['score'])
    return dict(inicio_cuerpo=float(chosen['bbox'][1]),metodo='bloque_ancho_predicho',bbox=chosen['bbox'])

def select_seal(shape,boxes,geometry):
    h,w=shape[:2];start=geometry['inicio_cuerpo']
    if start is None:
        return [],'sin_cabecera_resuelta'
    found=[]
    for box in boxes:
        a,b,c,d=box['bbox']
        # Contexto superior derecho, compacto y anterior al cuerpo. No se exige
        # que el sello quede a la izquierda del rótulo, que puede estar encima.
        if box['label']==3 and box['score']>=.35 and (a+c)/2>=.55*w and d<=start and b<=.2*h:
            found.append(box)
    return (found,'candidato_superior_unico') if len(found)==1 else ([], 'ninguno_o_varios_sellos_superiores')

def enhance(image,params):
    import cv2
    lab=cv2.cvtColor(image,cv2.COLOR_RGB2LAB)
    lab[:,:,0]=cv2.createCLAHE(clipLimit=params['clipLimit'],tileGridSize=tuple(params['tileGridSize'])).apply(lab[:,:,0])
    return cv2.cvtColor(lab,cv2.COLOR_LAB2RGB)

def expand(box,width,height,x_ratio=.5,y_ratio=.15):
    a,b,c,d=box
    if not (0<=a<c<=width and 0<=b<d<=height):
        raise ValueError('BBox original fuera del sello.')
    mx=max(1,round((d-b)*x_ratio));my=max(1,round((d-b)*y_ratio))
    return [max(0,a-mx),max(0,b-my),min(width,c+mx),min(height,d+my)]

def resolve(records):
    """Registros sin texto de referencia: posición, cajas y OCR de cada página."""
    ids=[(r['sha256_pdf'],r['pagina_pdf']) for r in records]
    if len(ids)!=len(set(ids)):
        raise ValueError('Página PDF duplicada.')
    result={}
    for r in records:
        key=(r['sha256_pdf'],r['pagina_pdf'])
        w,h=r['dimensiones']
        start=r.get('cuerpo_inicio_predicho')
        corners=[c for c in r['candidatos'] if (c['bbox'][0]+c['bbox'][2])/2>=.65*w
                 and c['bbox'][3]<=.2*h and start is not None and c['bbox'][3]<=start]
        accepted=[]
        for c in corners:
            reading=next((x for x in r['ocr_cabecera'] if x['id']==c['id']),None)
            if reading:
                match=re.fullmatch(r'\s*NO\.?\s*([0-9]+)\s*',reading['texto_original'],re.I)
                if match:
                    accepted.append(dict(numero=match.group(1),region_id=c['id'],bbox=c['bbox']))
        values=list(dict.fromkeys(x['numero'] for x in accepted))
        front=values[0] if len(values)==1 and not r['errores'] else None
        result[key]=dict(pagina_pdf=r['pagina_pdf'],sha256_pdf=r['sha256_pdf'],
            folio=dict(numero=front,lado='frente' if front else None,origen='leido_ocr' if front else 'no_determinado'),
            candidatos_esquina=corners,lecturas_frente=accepted,
            razon='rotulo_superior_derecho_ocr' if front else 'sin_frente_reconocido')
    by_id={key:r for key,r in zip(ids,records)}
    for key,r in by_id.items():
        out=result[key]
        if out['folio']['numero'] is not None:
            continue
        previous_key=(key[0],key[1]-1)
        previous=result.get(previous_key)
        if not previous or previous['folio']['lado']!='frente' or previous['folio']['origen']!='leido_ocr':
            out['razon']='sin_frente_ocr_inmediatamente_anterior'
            continue
        if r['errores'] or out['candidatos_esquina']:
            out['razon']='error_o_rotulo_sin_resolver_no_inferir'
            continue
        before=by_id[previous_key]
        w,h=r['dimensiones'];pw,ph=before['dimensiones']
        a,b=r.get('cuerpo_inicio_predicho'),before.get('cuerpo_inicio_predicho')
        if (a is None or b is None or abs((w/h)/(pw/ph)-1)>.02 or abs(a/h-b/ph)>.05):
            out['razon']='estructura_no_compatible'
            continue
        following=result.get((key[0],key[1]+1))
        if following and following['folio']['lado']=='frente' and int(following['folio']['numero'])!=int(previous['folio']['numero'])+1:
            out['razon']='numeracion_del_siguiente_frente_contradice_secuencia'
            continue
        out.update(folio=dict(numero=previous['folio']['numero'],lado='vuelto',origen='inferencia'),
                   razon='mismo_pdf_consecutivo_cabecera_sin_rotulo_y_cuerpo_compatible',pagina_frente=key[1]-1)
    return [result[k] for k in ids]

def render(image,bbox,branch,scale=.4):
    h,w=image.shape[:2];rw,rh=round(w*scale),round(h*scale);sx,sy=rw/w,rh/h
    x1,y1,x2,y2=bbox
    reduced=[math.floor(x1*sx),math.floor(y1*sy),math.ceil(x2*sx),math.ceil(y2*sy)]
    geometry=dict(bbox_fuente=bbox,bbox_en_pagina_reducida=reduced,escala_efectiva=[sx,sy],
        bbox_fuente_equivalente=[reduced[0]/sx,reduced[1]/sy,reduced[2]/sx,reduced[3]/sy])
    if branch=='recorte_luego_escala':
        padded=prepare_crop(image,bbox,scale)
    else:
        if branch=='pagina_soporte_bbox':
            source=np.full_like(image,255);source[y1:y2,x1:x2]=image[y1:y2,x1:x2]
        elif branch=='pagina_luego_recorte':
            source=image
        else:
            raise ValueError('Rama desconocida.')
        small=cv2.resize(source,(rw,rh),interpolation=cv2.INTER_AREA)
        a,b,c,d=reduced;crop=small[b:d,a:c]
        padded=cv2.copyMakeBorder(crop,20,20,20,20,cv2.BORDER_CONSTANT,value=(255,255,255))
    geometry['dimensiones_ocr_sin_margen']=[padded.shape[1]-40,padded.shape[0]-40]
    return padded,geometry

def prepare_crop(image,bbox,scale):
    x1,y1,x2,y2=bbox;crop=image[y1:y2,x1:x2]
    resized=cv2.resize(crop,(round(crop.shape[1]*scale),round(crop.shape[0]*scale)),interpolation=cv2.INTER_AREA)
    return cv2.copyMakeBorder(resized,20,20,20,20,cv2.BORDER_CONSTANT,value=(255,255,255))

def inspect_input(image):
    """Solo uint8 gris/RGB/BGR opaco. Un pixel254 impide declarar blanco exacto."""
    if not isinstance(image,np.ndarray) or image.dtype!=np.uint8 or image.size==0:
        raise ValueError('Entrada OCR debe ser imagen uint8 no vacia.')
    if image.ndim not in (2,3) or (image.ndim==3 and image.shape[2]!=3):
        raise ValueError('Entrada OCR debe ser gris o tres canales sin transparencia.')
    white=bool(np.all(image==255))
    return dict(imagen_totalmente_blanca=white,ejecutar_ocr=not white,
        estado_entrada='entrada_ocr_blanca' if white else 'entrada_ocr_no_blanca',
        ocupacion_fuente='no_determinada')

def iou(a,b):
    area=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-area
    return area/union if union else 0.

COLUMN_PARAMS = {'dispersion_derecha_relativa': 0.025, 'candidatos_min': 20, 'candidatos_max': 35, 'desviacion_paso_max': 0.25}

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()
