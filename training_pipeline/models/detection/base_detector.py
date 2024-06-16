import abc


class BaseDetector(abc.ABC):
    @abc.abstractmethod
    def train(self, cfg):
        pass

    @abc.abstractmethod
    def inference(self, imgs):
        # bgr
        pass

    @abc.abstractmethod
    def get_model(self):
        pass
    