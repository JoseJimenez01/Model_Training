"""Constructor de inferencia reutilizado, sin descargas ni datos de entrenamiento."""
from pathlib import Path
import torch
from torchvision.models import mobilenet_v3_large
from torchvision.models.detection import FasterRCNN
from torchvision.models.detection.anchor_utils import AnchorGenerator
from torchvision.models.detection.backbone_utils import _mobilenet_extractor
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.rpn import RPNHead
from torchvision.ops.misc import FrozenBatchNorm2d
from recetas import sha
def make_model(config, initial_weights=True):
    """Replica el constructor oficial, evitando toda descarga implícita."""
    backbone = mobilenet_v3_large(weights=None, norm_layer=FrozenBatchNorm2d)
    backbone = _mobilenet_extractor(backbone, True, config['trainable_backbone_layers'])
    anchors = AnchorGenerator(((32, 64, 128, 256, 512),)*3, ((.5, 1., 2.),)*3)
    model = FasterRCNN(backbone, num_classes=91, rpn_anchor_generator=anchors,
        min_size=tuple(config['min_size']), max_size=config['max_size'],
        box_score_thresh=.01, box_detections_per_img=100,
        rpn_pre_nms_top_n_train=2000, rpn_post_nms_top_n_train=1000,
        rpn_pre_nms_top_n_test=1000, rpn_post_nms_top_n_test=1000)
    if initial_weights:
        path = Path(config['weights'])
        if not path.exists():
            raise FileNotFoundError('Faltan pesos preentrenados locales: ' + str(path))
        if not sha(path).startswith(config['weights_sha256_prefix']):
            raise ValueError('Hash de pesos preentrenados incorrecto.')
        model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
    feature_profile = config.get('feature_profile', 'default')
    if feature_profile == 'fine16':
        # Mantiene página completa; sustituye el primer mapa de paso 32 por
        # uno de paso 16. No reutilizar por índice pesos de canales distintos.
        finer = _mobilenet_extractor(
            mobilenet_v3_large(weights=None, norm_layer=FrozenBatchNorm2d),
            True, config['trainable_backbone_layers'], returned_layers=[3, 5])
        finer.body.load_state_dict(model.backbone.body.state_dict(), strict=True)
        for block in ('inner_blocks', 'layer_blocks'):
            getattr(finer.fpn, block)[1].load_state_dict(
                getattr(model.backbone.fpn, block)[1].state_dict(), strict=True)
        model.backbone = finer
    elif feature_profile != 'default':
        raise ValueError('Perfil de características desconocido.')
    model.roi_heads.box_predictor = FastRCNNPredictor(model.roi_heads.box_predictor.cls_score.in_features, 4)
    if config['anchor_profile'] in ('document', 'document_small'):
        # Razones alto/ancho: títulos planos, bloques, firmas y columnas altas.
        sizes = (8, 24, 96, 256, 512) if config['anchor_profile'] == 'document_small' else (32, 96, 256, 512)
        model.rpn.anchor_generator = AnchorGenerator((sizes,)*3,
                                                      ((.04, .2, 1., 5., 64.),)*3)
        model.rpn.head = RPNHead(model.backbone.out_channels, len(sizes)*5)
    elif config['anchor_profile'] != 'default':
        raise ValueError('Perfil de anchors desconocido.')
    if config.get('object_balanced_rpn', False):
        from muestreo_objetos_v34 import install_object_sampler
        install_object_sampler(model)
    return model