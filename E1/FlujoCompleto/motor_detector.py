"""Proceso persistente del detector; protocolo JSON por stdin/stdout, sin red."""
import json
import sys


def emit(value):
    print(json.dumps(value, ensure_ascii=True, allow_nan=False), flush=True)


def run():
    # Delayed imports ensure dependency errors become explicit protocol errors.
    import torch
    from PIL import Image
    from torchvision.transforms.functional import pil_to_tensor
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
    from arquitectura import make_model
    from recetas import sha
    config = json.loads(sys.stdin.readline())
    device = torch.device(config.get('device', 'cuda') if torch.cuda.is_available() else 'cpu')
    torch.set_num_threads(4)
    torch.manual_seed(20261021)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    models = {}
    provenance = {}
    for name in ('global', 'carnet'):
        path = config.get(name)
        if not path:
            continue
        digest = sha(path)
        expected = config[name + '_sha256']
        if digest != expected:
            raise ValueError('El checkpoint ' + name + ' no corresponde al modelo conservado.')
        state = torch.load(path, map_location='cpu', weights_only=True)
        model = make_model(state['config'], initial_weights=False)
        if name == 'carnet':
            model.roi_heads.box_predictor = FastRCNNPredictor(model.roi_heads.box_predictor.cls_score.in_features, 2)
        model.load_state_dict(state['model'], strict=True)
        models[name] = model.to(device).eval()
        provenance[name] = dict(sha256=digest, arquitectura=state['config']['architecture'])
    if 'global' not in models:
        raise ValueError('Falta el detector global.')
    emit(dict(ok=True, dispositivo=str(device), torch=torch.__version__, modelos=provenance))
    for line in sys.stdin:
        request = json.loads(line)
        if request.get('op') == 'cerrar':
            break
        try:
            with Image.open(request['imagen']) as source:
                image = source.convert('RGB')
            width, height = image.size
            if request['modelo'] == 'global':
                image.thumbnail((2200, 2200), Image.Resampling.BILINEAR)
            sx, sy = image.width / width, image.height / height
            with torch.inference_mode():
                pred = models[request['modelo']]([pil_to_tensor(image).float().div(255).to(device)])[0]
            boxes = []
            for box, label, score in zip(pred['boxes'].cpu().tolist(), pred['labels'].cpu().tolist(), pred['scores'].cpu().tolist()):
                if score >= .01:
                    boxes.append(dict(bbox=[box[0]/sx,box[1]/sy,box[2]/sx,box[3]/sy],label=int(label),score=float(score)))
            emit(dict(ok=True, predicciones=boxes, dimensiones_cache=list(image.size), escala=[sx,sy]))
        except Exception as exc:
            emit(dict(ok=False, error=f'{type(exc).__name__}: {exc}'))


if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        emit(dict(ok=False, error=f'{type(exc).__name__}: {exc}. No se sustituye el detector ni se descarga otro modelo.'))
        raise SystemExit(1)
