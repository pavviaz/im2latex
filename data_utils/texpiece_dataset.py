import argparse
import os
import re
import multiprocessing
from glob import glob
import subprocess

# DEBUG ONLY
import sys

sys.path.append("/Users/pavelvyaznikov/Documents/DeepScriptum")

import yaml
import numpy as np
from munch import munchify
from pdf2image import convert_from_path

from training_pipeline.detecting_manager import ModelManager as DM
from multiprocess_funcs import compute_threads_work
import config


PIX_IN_BP = 0.36
SYNCTEX_LINE_REGEX = r"\nLine:\d+\n"


class TexPieceDataset:
    def __init__(self, cfg):
        with open(cfg) as c:
            self.cfg = munchify(yaml.load(c, Loader=yaml.FullLoader))

        self.dm = DM(
            model_id=self.cfg.main.detector_id,
            inference_device=self.cfg.main.detector_device,
        )

    def worker(self, pap_list, lock):
        for ppr in pap_list:
            cur_dir = os.path.dirname(ppr)
            try:
                # -cd = change dir for tex containing
                # -pdf = pdf output
                # -f force, necessary for cites correct render
                subprocess.run(
                    ["latexmk", "-cd", "-pdf", "-f", "-synctex=-1", ppr],
                    timeout=config.LATEXMK_TIMEOUT,
                )
            except Exception as e:
                print(f"Error '{e}' while rendering {ppr}")
                continue

            pdf_name = os.path.join(
                cur_dir, f"{os.path.basename(ppr).split('.')[0]}.pdf"
            )
            if not os.path.exists(pdf_name):
                print("PDF 'pdf_name' was not generated")
                continue

            with open(ppr) as f:
                latex = [el.rstrip("\n") for el in f.readlines()]

            # convert to BGR
            try:
                pdf_imgs = [
                    np.array(el)[..., ::-1]
                    for el in convert_from_path(pdf_name, dpi=self.cfg.main.pdf_dpi)
                ]
            except:
                print(f"PDF '{pdf_name}' is broken")
                continue

            for bbox, _cls, crop, pn in self.dm.predict(
                pdf_imgs,
                iou=self.cfg.main.detector_iou,
                conf=self.cfg.main.detector_conf,
            ):
                x_c = PIX_IN_BP * (bbox[0] + bbox[2]) / 2
                y_c = PIX_IN_BP * (bbox[1] + bbox[3]) / 2

                result = subprocess.run(
                    ["synctex", "edit", "-o", f"{pn + 1}:{x_c}:{y_c}:{pdf_name}"],
                    timeout=config.LATEXMK_TIMEOUT,
                    capture_output=True,
                    text=True,
                )

                # TODO
                if _cls == "":
                    pass

                block_line = re.findall(SYNCTEX_LINE_REGEX, result.stdout)

                if result.stderr or not block_line:
                    print(result.stderr)
                    print(result.stdout)
                    continue

                block_line = int(block_line[0].strip("\n").split(":")[-1])
                block_latex = latex[block_line - 1]

                print()

    def main(self):
        if not os.path.exists(self.cfg.main.paper_dir):
            raise OSError(f"'{self.cfg.main.paper_dir}' doesn't exist")

        # if os.path.exists(self.cfg.main.output):
        #     raise OSError(f"Output dir is already exists")
        os.makedirs(self.cfg.main.output_dir, exist_ok=True)

        pps = [
            os.path.join(self.cfg.main.paper_dir, el)
            for el in os.listdir(self.cfg.main.paper_dir)
        ]
        pps = list(filter(os.path.isdir, pps))
        pps = [
            os.path.join(el, tex[0])
            for el in pps
            if len(tex := glob(os.path.join(el, "*.tex"))) == 1
            and len(glob(os.path.join(el, "*.bib"))) == 1
        ]
        # pps = list(filter(lambda x: len(glob(os.path.join(x, "*.tex"))) == 1, pps))

        lock = multiprocessing.Lock()
        # multiprocessing.set_start_method("spawn")
        threads = [
            multiprocessing.Process(
                target=self.worker, args=((pps[arg[0] : arg[1]], lock))
            )
            for arg in compute_threads_work(len(pps), self.cfg.main.workers)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c",
        "--config-path",
        type=str,
        help="TexPiece dataset config path",
        required=True,
    )

    args = parser.parse_args()

    ds = TexPieceDataset(args.config_path)
    ds.main()
