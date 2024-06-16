import os
import pickle
import codecs
import yaml
import re

import mlflow
import torch
from mlflow import MlflowClient
from mlflow.artifacts import download_artifacts
from munch import munchify

from meta_dicts import TYPE_TO_CLS


MLFLOW_RUN_ID_REGEX = r"[a-f0-9]{32}"


class ModelManager:
    def __init__(
        self,
        model_id=None,
        config_path=None,
        inference_device="cpu",
        mlflow_host="http://127.0.0.1:5000",
    ):
        if all(not el for el in [config_path, model_id]):
            error_msg = "Either 'model_id' or 'config_path' \
                must be specified"
            self.__invoke_exception(error_msg, ValueError)

        self.inf_device = inference_device

        os.environ["MLFLOW_TRACKING_URI"] = mlflow_host
        os.environ["MLFLOW_EXPERIMENT_NAME"] = "Default"
        self.client = MlflowClient()

        if re.fullmatch(MLFLOW_RUN_ID_REGEX, model_id):
            run_id = model_id
        elif os.path.exists(model_id):
            weight_path = model_id
        else:
            run_name = model_id

        if weight_path:
            self.__load_pt_model(weight_path)
            return

        if run_name or run_id:
            _ = self.__load_mlflow_model(run_name, run_id)
            return

        config = self.__config_reader(config_path)
        self.cfg = munchify(config)

        if len(self.cfg) > 2:
            error_msg = f"Only 'general' key with one of following \
            keys must be specified in the config: {TYPE_TO_CLS.keys()}"
            self.__invoke_exception(error_msg, OSError)

        model_type = [el for el in self.cfg if el != "general"][0]
        self.model_manager = TYPE_TO_CLS[model_type]()

        if not os.path.exists(self.cfg.general.dataset_cfg_path):
            error_msg = f"Dataset cfg on '{self.cfg.general.dataset_cfg_path}' \
                          does not exist"
            self.__invoke_exception(error_msg, OSError)

        self.cfg.general.device = self.__enable_gpu(self.cfg.general.device)

    @staticmethod
    def __enable_gpu(device):
        if "cuda" in device and torch.cuda.is_available():
            torch.cuda.set_device(0)
            return device
        return "cpu"

    def __config_reader(self, config_path):
        if not os.path.exists(config_path):
            error_msg = f"Config file on {config_path} path does not exist"
            self.__invoke_exception(error_msg, OSError)

        with open(config_path) as c:
            config = yaml.load(c, Loader=yaml.FullLoader)

        return config

    def __invoke_exception(self, msg, exc):
        mlflow.end_run()

        raise exc(msg)

    def __load_pt_model(self, weight_path):
        # /home/user/yolo_model.py
        ckpt_name = os.path.basename(weight_path)
        match ckpt_name.split("_")[0]:
            case "yolo":
                self.model_manager = TYPE_TO_CLS["yolo"](
                    weight_path, device=self.inf_device
                )
            case "detectron":
                pass

    def __load_mlflow_model(self, name, run_id):
        try:
            filter_string = (
                f"attributes.run_id='{run_id}'"
                if run_id
                else f"attributes.run_name='{name}'"
            )
            run = self.client.search_runs(
                experiment_ids=0, filter_string=filter_string, max_results=1
            )[0]

            run_id = run.info.run_id
            model_type = run.data.tags["model_type"]

            weights = download_artifacts(run_id=run_id, artifact_path="last.pt")
            with open(weights) as w:
                buf = w.read()
            model = pickle.loads(codecs.decode(buf.encode(), "base64"))

            match model_type:
                case "yolo":
                    self.model_manager = TYPE_TO_CLS["yolo"](
                        model, device=self.inf_device
                    )
                case "detectron":
                    pass

            return run_id
        except:
            error_msg = f"Run named {name} or having id {run_id} is not found"
            self.__invoke_exception(error_msg, OSError)

    def train(self):
        self.model_manager.train(self.cfg)

    def predict(self, imgs, iou, conf):
        return self.model_manager.inference(imgs, iou, conf)

    def get_model(self):
        return self.model


if __name__ == "__main__":
    manager = ModelManager(
        model_id="/Users/pavelvyaznikov/Documents/DeepScriptum/trained_weights/yolo_v8m_dln.pt",
        mlflow_host="localhost",
    )

    l = manager.predict(["cptr2.png"], 0.01, 0.5)
    print(list(l))
