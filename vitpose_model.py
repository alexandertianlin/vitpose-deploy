from __future__ import annotations
import os
import numpy as np
import torch
import torch.nn as nn
from mmpose.apis import inference_top_down_pose_model, init_pose_model, process_mmdet_results

class ViTPoseModel(object):
    MODEL_DICT = {
        'ViTPose+-G (multi-task train, COCO)': {
            'config': os.path.join(os.path.dirname(__file__),
                'configs/ViTPose_huge_wholebody_256x192.py'),
            'model': os.path.join(os.path.dirname(__file__),
                'weights/vitpose+_huge/wholebody.pth'),
        },
    }

    def __init__(self, device: str | torch.device):
        self.device = torch.device(device)
        self.model_name = 'ViTPose+-G (multi-task train, COCO)'
        self.model = self._load_model(self.model_name)

    def _load_model(self, name: str) -> nn.Module:
        dic = self.MODEL_DICT[name]
        return init_pose_model(dic['config'], dic['model'], device=self.device)

    def predict_pose(self, image: np.ndarray, det_results: list[np.ndarray],
                     box_score_threshold: float = 0.5) -> list[dict[str, np.ndarray]]:
        image = image[:, :, ::-1]  # RGB -> BGR for mmpose
        person_results = process_mmdet_results(det_results, 1)
        out, _ = inference_top_down_pose_model(self.model, image,
                                               person_results=person_results,
                                               bbox_thr=box_score_threshold,
                                               format='xyxy')
        return out
