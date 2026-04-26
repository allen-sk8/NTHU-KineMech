
import cv2
import torch
import numpy as np
from cv2.typing import MatLike


def preprocess_for_vitpose(images:list[MatLike], device:str="cpu"):
    """
    images: list of opencv bgr images
    """
    images = [images] if not isinstance(images, list) else images
    resized_images = []
    for image in images:
        x = cv2.resize(image, dsize=(192, 256))
        x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB).transpose(2, 0, 1) # (H, W, C) -> (C, H, W)
        x = x.astype(np.float32) / 255
        resized_images.append(x)

    resized_images = np.stack(resized_images, axis=0, dtype=np.float32)

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)   # from ImageNet
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)    # from ImageNet
    resized_images = (resized_images - mean) / std
    resized_images = torch.FloatTensor(resized_images).unsqueeze(0).to(device) if resized_images.ndim == 3 else torch.FloatTensor(resized_images).to(device)
    return resized_images