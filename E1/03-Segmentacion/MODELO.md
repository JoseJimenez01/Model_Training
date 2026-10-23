# Modelo de referencia y preparación

| Dato | Valor |
| --- | --- |
| Modelo conservado | v32 control, perfil documento |
| Arquitectura | Faster R-CNN MobileNetV3-Large FPN |
| Clases | 1 impreso;2 escritura_mano;3 sello;0 fondo |
| Época elegida | 54 |
| Umbral operativo conservado | 0,35 |
| Formato de coordenadas | `[x1,y1,x2,y2]`, imagen fuente |
| Hash SHA256 del checkpoint | `9f1e80f26c7e0b4301810c5d620b054d10c83423125b7f4f2d1e0bfeb5f99f2a` |

Antes de inferencia se convierte a RGB y se reduce proporcionalmente con
Pillow BILINEAR a lado máximo2200px. La transformación interna del modelo
mantiene su configuración original; las predicciones se devuelven a las
coordenadas de la fuente. Cambiar este orden, el redondeo o el realce exige
validación: no asumir equivalencia con una entrada procesada de etapa02.

El entorno utilizado fue PyTorch2.7.1+cu118, TorchVision0.22.1+cu118 y GPU
GTX1650. 

La siguiente integración debe generar regiones, categorías, confianza,
coordenadas y errores por página. Las propuestas manuscritas/sellos son
exclusiones experimentales, no garantía de que el resto esté libre de manuscrito.
No debe transcribirlas, rellenar impresión oculta ni declarar vacío lo no detectado.
