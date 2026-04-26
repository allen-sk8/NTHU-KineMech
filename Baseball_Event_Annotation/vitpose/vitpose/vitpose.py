import logging
from pathlib import Path
from enum import Enum, auto

import torch
import torch.nn as nn

from .model_settings import vitmoe_setting, coco17_head_setting, coco133_head_setting
from .components.utils import count_parameters
from .components.vit_moe import ViTMoE
from .components.simple_head import SimpleHead

logger = logging.getLogger(__name__)

class ViTPose(nn.Module):
    class OutputMode(Enum):
        coco17 = auto()
        coco133 = auto()
        hybrid = auto() # coco17 with coco133

    kinemetic_tree = [[1, 3], [1, 0], [0, 2], [2, 4], [3, 5], [4, 6], [5, 6], [5, 7], [7, 9], [6, 8], [8, 10], [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16]]

    def __init__(self, weights_path:Path=None, output_mode:OutputMode=OutputMode.hybrid):
        super().__init__()
        self.output_mode = output_mode
        self.backbone = ViTMoE(**vitmoe_setting)
        self.coco17_head = SimpleHead(**coco17_head_setting)
        self.coco133_head = SimpleHead(**coco133_head_setting)
        self.init_weights(weights_path)

    def init_weights(self, weights_path):
        weights_path = Path(weights_path) if isinstance(weights_path, str) else weights_path
        if weights_path is None or not weights_path.is_file():
            logger.info("Using random initialization")
            # TODO: init randomly for training
            return
        
        state_dict:dict[str, torch.Tensor] = torch.load(weights_path, map_location="cpu", weights_only=True)["state_dict"]
        
        logger.debug(f"Keys in ViTPose, from {weights_path.resolve()}")
        #logger.debug(f"\n{str(state_dict.keys()).replace(", ", "\n")}")
        #logger.debug(f"\n{str(state_dict.keys()).replace(', ', '\n')}")
        logger.debug("\n" + str(state_dict.keys()).replace(", ", "\n"))

        backbone_weights = {key.replace("backbone.", ""):val for key, val in state_dict.items() if key.startswith("backbone.")}
        coco17_head_weights = {key.replace("keypoint_head.", ""):val for key, val in state_dict.items() if key.startswith("keypoint_head.")}
        coco133_head_weights = {key.replace("associate_keypoint_heads.4.", ""):val for key, val in state_dict.items() if key.startswith("associate_keypoint_heads.4.")}
        
        result = self.backbone.load_state_dict(backbone_weights, strict=True)
        logger.info(f"ViTPose.backbone: {result}")
        result = self.coco17_head.load_state_dict(coco17_head_weights, strict=True)
        logger.info(f"ViTPose.coco17_head: {result}")
        result = self.coco133_head.load_state_dict(coco133_head_weights, strict=True)
        logger.info(f"ViTPose.coco133_head: {result}")
        logger.info(f"Trainable paremeters: {count_parameters(self):,}")
        
    def forward(self, x:torch.Tensor):
        heatmaps = None
        batch_size = x.shape[0]
        if self.output_mode == self.OutputMode.coco17:
            moe_ids = torch.zeros((batch_size), dtype=torch.long, device=x.device)
            features = self.backbone(x, moe_ids)
            heatmaps = self.coco17_head(features)

        elif self.output_mode == self.OutputMode.coco133:
            moe_ids = torch.zeros((batch_size), dtype=torch.long, device=x.device) + 5
            features = self.backbone(x, moe_ids)
            heatmaps = self.coco133_head(features)

        elif self.output_mode == self.OutputMode.hybrid: # passing backbone twice without data duplication is faster than passing backbone once but duplicates data
            moe_ids = torch.zeros((batch_size), dtype=torch.long, device=x.device)
            features_17 = self.backbone(x, moe_ids)
            heatmaps_17 = self.coco17_head(features_17)
            moe_ids += 5
            features_133 = self.backbone(x, moe_ids)
            heatmaps_133 = self.coco133_head(features_133)
            heatmaps = torch.cat([heatmaps_17, heatmaps_133[:, 17:]], dim=1)

        return heatmaps

    @staticmethod
    def heatmaps_to_keypoints(heatmaps:torch.Tensor, to_image_shape:bool=True):
        """
        heatmaps: (batch, n_joints, height, width)
        """
        height = heatmaps.shape[2]
        width = heatmaps.shape[3]
        flattened_heatmaps = heatmaps.reshape(*heatmaps.shape[:-2], -1)
        max_index = torch.argmax(flattened_heatmaps, dim=2, keepdim=True)
        coordinates = torch.tile(max_index, (1, 1, 2)).to(torch.float32)

        coordinates[:, :, 0] = (coordinates[:, :, 0]) % width
        coordinates[:, :, 1] = torch.floor((coordinates[:, :, 1]) / width)

        # post processing
        if to_image_shape:
            for b in range(coordinates.shape[0]):
                for j in range(coordinates.shape[1]):
                    heatmap = heatmaps[b][j]
                    px = int(torch.floor(coordinates[b][j][0] + 0.5))
                    py = int(torch.floor(coordinates[b][j][1] + 0.5))
                    if 1 < px < width-1 and 1 < py < height-1:
                        # move towards gradient
                        diff = torch.tensor([heatmap[py][px+1] - heatmap[py][px-1], heatmap[py+1][px] - heatmap[py-1][px]], device=coordinates.device)
                        coordinates[b][j] += torch.sign(diff) * 0.25
            coordinates = coordinates.to(torch.float32) * 4

        # confidence
        max_values = torch.amax(flattened_heatmaps, dim=2, keepdim=True)
        sigmoid = torch.nn.Sigmoid()
        confidence = sigmoid(max_values)
        coordinates = torch.dstack((coordinates, confidence))

        return coordinates # (batch, n_joint, 2)