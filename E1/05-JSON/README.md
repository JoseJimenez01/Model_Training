# 05 — Registro de resultados en JSON

**El formato elegido para tomos es `propuesta_tomo_02`: cabecera del documento
y texto unido por página PDF.** El detalle de renglones, regiones y lecturas OCR
se conserva en evidencia separada. El acuerdo definitivo de intercambio con
E3 sigue pendiente.

Se puede ver el cuerpo en el archivo `ejemplo_tomo.json`

Esta etapa organiza lo obtenido; no corrige la transcripción ni completa
datos faltantes por contexto. Un JSON válido puede contener lecturas parciales
o equivocadas: el formato no garantiza la calidad del OCR.

**Para el índice aún está pendiente.**

## Qué se ha probado

- Exportación del flujo OCR a vista compacta y adaptación de propuestas temporales.
- Organización por página, con texto unido y cabecera de tomo/notario.
- Recuperación de campos mediante recortes de metadatos delimitados y, después,
  pruebas de localización automática para separar ambos alcances.
- Integración del carnet leído en un recorte específico del sello.
- Folio/frente desde OCR e inferencia del vuelto consecutivo compatible.
- Conservación de páginas pendientes, posiciones sin lectura y alertas técnicas.
- Separación de contenido público y evidencia con texto literal, coordenadas,
  confianza, transformaciones y comandos.

## Qué formato se conserva y por qué

| Salida probada | Decisión |
| --- | --- |
| Propuestas `dataset_temporal` | Antecedentes de coordinación, no referencias verificadas ni contrato definitivo. |
| JSON con objetos públicos por línea | No es el formato de consumo elegido para tomos; ese detalle se conserva en evidencia. |
| `propuesta_tomo_02`, texto unido por página | Formato operativo elegido para continuar. Conserva cabecera, organización y alertas. |
| Rellenar campos con valores de ejemplo o del nombre del PDF | No admitido. Un campo sin lectura suficiente queda pendiente. |

No es una comparación de precisión entre formatos: se elige una estructura
que conserva el contenido y permite distinguir sus límites.

## Qué se ha conseguido registrar

En el ensayo de cinco páginas de Salvador se integraron nombre del notario,
carnet leído en cinco sellos claros, folios reconocidos y vueltos inferidos.
Tomo, identificador, papel y serie siguen nulos cuando falta lectura suficiente.
Los metadatos de esa muestra se reutilizaron en sus exportaciones posteriores;
no se ejecutaron de nuevo al regenerar cada JSON.

Estado del último ejemplo parcial conservado:

| Página PDF | Texto registrado | Límite |
| --- | --- | --- |
| 1 | Nulo | Numeración pendiente; no declara página vacía. |
| 2 | Fragmentos en15 posiciones | Conserva30 posiciones físicas. |
| 3 | Fragmento del renglón27 | Resto retenido por manuscritos residuales/cobertura. |
| 4 | Texto en30 posiciones | Solo seis renglones tienen comparación textual confirmada en este protocolo. |
| 5 | Fragmentos en26 posiciones | Quedan posiciones pendientes. |

Son72 posiciones con fragmentos OCR, **no72 transcripciones verificadas** ni
una medida de exactitud. No se libera una página completa por haber recuperado
un fragmento local. Los errores y omisiones permanecen visibles en la evidencia.

## Cómo se representan los datos

- **Cabecera:** tipo, tomo, identificador técnico y nombre/carnet del notario.
- **Página:** posición PDF, folio, frente/vuelto, papel/serie, texto y alertas.
- **Dato no recuperado:** `null` y su motivo disponible en alertas/evidencia.
- **Texto:** un campo por página; si hay30 renglones físicos, se mantienen sus
  posiciones con saltos de línea, incluidos los no reconocidos.
- **Dato inferido:** procedencia explícita. El vuelto solo se infiere de un
  frente anterior leído y una secuencia consecutiva compatible.
- **Lista de actos vacía:** no significa que no existan actos; la extracción
  de ese campo está pendiente y se señala con alerta.

Los saltos de línea del OCR no determinan por sí solos los renglones físicos.
Si solo se conocen regiones, se declara esa organización sin inventar30 filas.

## Índices

Se requiere organización por página, período y registros, transcribiendo tomo,
folio, número, fecha, hora, acto/contrato y partes tal como aparecen. Su contrato
JSON definitivo sigue pendiente con E3; no se presenta aquí un esquema de índices
como si estuviera acordado. Ausencia de instrumentos solo ante declaración
explícita, no por lecturas vacías o fallidas.

## Qué conservar por ahora

**Contenido, alertas y evidencia separados; campos desconocidos explícitos y
procedencia de los datos.** No tomar información de una plantilla, del nombre
del archivo o de la paridad de página para completar el documento.

Pendiente acordar el contrato definitivo con E3, el esquema de índices, la
inclusión final de coordenadas y la invocación conjunta de las cinco etapas.
El exportador autónomo para el repositorio grupal se preparará por separado.

[Campos y reglas](FORMATO.md) · [Ejemplo sintético](ejemplo_tomo.json).
El ejemplo es ficticio y solo ilustra la estructura; no contiene OCR documental.
