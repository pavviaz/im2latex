import pickle
import codecs
import os

import mlflow
import torch
from ultralytics import YOLO, settings, nn
from ultralytics.utils.downloads import attempt_download_asset

from base_detector import BaseDetector


YOLO_TMP_DIR = "tmp/"
YOLO_DEFAULT_MODEL = "yolov8n.pt"


def model_type_callback(_):
    mlflow.set_tag("model_type", "yolo")


def logging_callback(trainer):
    mlflow.log_metrics(trainer.lr)
    mlflow.log_metrics(
        {k: v for k, v in zip(trainer.loss_names, list(trainer.tloss.cpu().numpy()))}
    )
    model_dump = codecs.encode(pickle.dumps(trainer.model), "base64").decode()
    mlflow.log_text(model_dump, "last.pt")


class YoloManager(BaseDetector):
    def __init__(self, weights=None, device="cpu"):
        attempt_download_asset(file=YOLO_DEFAULT_MODEL, dir=YOLO_TMP_DIR)
        self.model = YOLO(os.path.join(YOLO_TMP_DIR, YOLO_DEFAULT_MODEL))

        match device:
            case "cpu":
                self.model.to(device)
            case "cuda":
                if torch.cuda.is_available():
                    self.model.to(device)
                else:
                    self.model.to("cpu")
            case "mps":
                if torch.backends.mps.is_available():
                    self.model.to(device)
                else:
                    self.model.to("cpu")
            case _:
                self.model.to("cpu")

        if weights:
            if isinstance(weights, str):
                self.model = YOLO(weights)
            elif isinstance(weights, nn.tasks.DetectionModel):
                self.model.model = weights
                self.model.model.training = False
                self.model.training = False
            else:
                raise ValueError(f"YOLO weights bad type")

        settings.update(
            {
                "mlflow": True,
                "clearml": False,
                "clearml": False,
                "comet": False,
                "dvc": False,
                "hub": False,
                "neptune": False,
                "raytune": False,
                "tensorboard": False,
                "wandb": False,
            }
        )

    def train(self, cfg):
        self.model.to(cfg.general.device)

        self.model.add_callback("on_train_start", model_type_callback)
        self.model.add_callback("on_fit_epoch_end", logging_callback)

        self.model.train(
            data=cfg.general.dataset_cfg_path,
            seed=cfg.general.seed,
            project=cfg.general.export_path,
            name=cfg.general.model_name,
            device=cfg.general.device,
            save=False,
            plots=False,
            **cfg.yolo,
        )

    def inference(self, imgs, iou, conf):
        results = self.model.predict(
            imgs, iou=iou, conf=conf, agnostic_nms=True, verbose=False
        )
        for idx, r in enumerate(results):
            for box in r.boxes:
                yield (t := [int(el) for el in box.xyxy[0]]), self.model.names[
                    int(box.cls.item())
                ], r.orig_img[t[1] : t[3], t[0] : t[2], :], idx

    def get_model(self):
        return self.model
