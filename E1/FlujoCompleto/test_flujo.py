"""Pruebas de integracion con PDF sintetico y doble explicito del detector.

No miden calidad v32 ni afirman una inferencia real: Tesseract/PDF si son reales.
"""
import json
from pathlib import Path
import tempfile
from threading import Event
import unittest
from unittest.mock import patch

import numpy as np
import pymupdf

import pipeline
from nombres import nombre_tomo, nombre_indice, sugerir_desde_pdf, validar_nombre
from recetas import guardar_json, resolve


class SyntheticDetector:
    fail_page = None
    def __init__(self, config):
        self.info = dict(prueba_sintetica=True, detector='doble de prueba; no inferencia real')
    def predict(self, path, name='global'):
        if self.fail_page and path.parent.name == self.fail_page:
            raise RuntimeError('Fallo de pagina simulado')
        return dict(predicciones=[dict(label=1, score=.99, bbox=[25,130,580,500]),
            dict(label=2, score=.99, bbox=[0,350,600,450])])
    def close(self):
        pass


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.pdf=self.root/'sintetico.pdf'
        with pymupdf.open() as doc:
            for n in range(3):
                page=doc.new_page(width=144,height=144)
                page.insert_text((10,45),'TEXTO DE PRUEBA',fontsize=10)
                page.insert_text((10,95),'NO TRANSCRIBIR',fontsize=9)
            doc.save(self.pdf)
        self.config=dict(pdf=str(self.pdf),salida=str(self.root/'salida'),modelo='solo-doble-prueba',
            modelo_carnet='',paginas='1-3',variante='original',binarizacion='otsu',guardar_txt=True)
    def tearDown(self):
        self.temp.cleanup()
    def test_end_to_end_continues_and_excludes(self):
        self.config['nombre_json']='tomo08_LeninRojas.json'
        class Failing(SyntheticDetector):fail_page='page_002'
        result=pipeline.run(self.config,lambda *p:None,Event(),Failing)
        self.assertEqual(result['estado'],'incompleto')
        root=Path(result['salida']);data=json.loads(Path(result['json']).read_text(encoding='utf-8'))
        self.assertEqual(Path(result['json']).name,'tomo08_LeninRojas.json')
        self.assertFalse((root/'formato.json').exists())
        self.assertIn('href="tomo08_LeninRojas.json"',(root/'index.html').read_text(encoding='utf-8'))
        self.assertIsNone(data['numero_tomo'])
        self.assertIsNone(data['notario']['nombre'])
        self.assertEqual([p['pagina_pdf'] for p in data['paginas']],[1,2,3])
        self.assertIsNone(data['paginas'][1]['texto'])
        self.assertIn('PRUEBA',data['paginas'][0]['texto'])
        self.assertIn('PRUEBA',data['paginas'][2]['texto'])
        self.assertNotIn('TRANSCRIBIR',json.dumps(data))
        self.assertTrue((root/'revision.txt').exists())
        self.assertTrue((root/'paginas/page_003.html').exists())
        self.assertTrue((root/'paginas/page_003/evidencia.json').exists())
    def test_cancel_keeps_selected_pages(self):
        cancel=Event()
        def progress(text,done,total):
            if done==1:cancel.set()
        self.config['guardar_txt']=False
        result=pipeline.run(self.config,progress,cancel,SyntheticDetector)
        self.assertEqual(result['estado'],'cancelado')
        root=Path(result['salida']);data=json.loads((root/'resultado_pendiente.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['paginas']),3)
        self.assertEqual(data['paginas'][2]['alertas'][0]['codigo'],'cancelado')
        self.assertFalse((root/'revision.txt').exists())
    def test_essential_failure_before_render(self):
        def unavailable(config):raise RuntimeError('Detector no disponible')
        with self.assertRaisesRegex(RuntimeError,'Detector no disponible'):
            pipeline.run(self.config,lambda *p:None,Event(),unavailable)
        self.assertFalse(Path(self.config['salida']).exists())
    def test_white_input_no_tesseract(self):
        with patch.object(pipeline.subprocess,'run') as command:
            result=pipeline.read_region(np.full((100,200,3),255,np.uint8),[0,0,200,100],self.root,'blanco','tesseract',7,0)
        command.assert_not_called()
        self.assertFalse(result['ocr_ejecutado'])
        self.assertFalse((self.root/'blanco.txt').exists())
    def test_known_hold_blocks_body_ocr(self):
        self.config['paginas']='1'
        with patch.object(pipeline,'retencion',return_value='Residuo conocido'),patch.object(pipeline,'body') as body:
            result=pipeline.run(self.config,lambda *p:None,Event(),SyntheticDetector)
        body.assert_not_called()
        self.assertEqual(result['estado'],'incompleto')
        data=json.loads((Path(result['salida'])/'resultado_pendiente.json').read_text(encoding='utf-8'))
        self.assertIsNone(data['paginas'][0]['texto'])
        self.assertTrue(any(a['codigo']=='retencion_conservada' for a in data['paginas'][0]['alertas']))
    def test_html_escapes_ocr_and_no_bulk_text(self):
        page=pipeline.empty_page(1);page['texto']='<script>alert(1)</script>'
        pipeline.page_html(page,self.root/'pagina.html')
        html=(self.root/'pagina.html').read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)
    def test_folio_not_inferred_over_gap(self):
        common=dict(sha256_pdf='synthetic',dimensiones=[600,600],cuerpo_inicio_predicho=150,errores=[])
        records=[dict(**common,pagina_pdf=1,candidatos=[dict(id='r',bbox=[450,20,550,60])],
            ocr_cabecera=[dict(id='r',texto_original='NO. 001')]),
            dict(**common,pagina_pdf=3,candidatos=[],ocr_cabecera=[])]
        self.assertIsNone(resolve(records)[1]['folio']['numero'])


class NamingTests(unittest.TestCase):
    def test_tomo_and_proposal_keep_all_name_parts(self):
        self.assertEqual(nombre_tomo(8,'Lenin Rojas'),'tomo08_LeninRojas.json')
        self.assertEqual(nombre_tomo(123,'Ana Mar\u00eda De La Cruz'),'tomo123_AnaMariaDeLaCruz.json')
        self.assertEqual(sugerir_desde_pdf('Tomo  8 Lenin Rojas Lopez.pdf'),'tomo08_LeninRojasLopez.json')
        self.assertEqual(sugerir_desde_pdf('documento.pdf'),'resultado_pendiente.json')
    def test_index_periods_are_supplied_not_inferred(self):
        for period in ('2017-2024','2019','2019-04','2019-04-Q1','2019-04-Q2'):
            self.assertEqual(nombre_indice(period,'Lenin Rojas'),f'indice{period}_LeninRojas.json')
        for period in ('2024-2017','2019-13','2019-04-Q3','enero'):
            with self.assertRaises(ValueError):nombre_indice(period,'Lenin')
    def test_invalid_or_reserved_names_rejected(self):
        for value in ('../tomo08_Lenin.json','ejecucion.json','evidencia_folios.json','CON.json','nombre.txt'):
            with self.assertRaises(ValueError):validar_nombre(value)


if __name__=='__main__':
    unittest.main()
