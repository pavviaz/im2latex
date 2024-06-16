import argparse
import os
import multiprocessing
import tarfile
import gzip

import yaml
from munch import munchify
import arxiv
from tqdm import tqdm

from multiprocess_funcs import compute_threads_work


class ArxivDownloader:
    def __init__(self, cfg):
        with open(cfg) as c:
            self.cfg = munchify(yaml.load(c, Loader=yaml.FullLoader))

    def worker(self, ids):
        for _id in tqdm(ids):
            try:
                s = arxiv.Client().results(arxiv.Search(id_list=[_id]))
                p = next(s).download_source(
                    dirpath=self.cfg.output_dir, filename=f"{_id}.tar.gz"
                )
            except:
                print(f"Download error for {_id}")
                continue

            ex_dir = os.path.join(self.cfg.output_dir, _id)
            try:
                with tarfile.open(p) as tar:
                    tar.extractall(path=ex_dir)
            except:
                print(f"Decompressing error for {_id}, trying gzip")
                try:
                    with open(p, "rb") as tar:
                        f = gzip.decompress(tar.read())
                        if rb"\begin{document}" in f:
                            os.makedirs(ex_dir)
                            with open(
                                os.path.join(ex_dir, f"main.tex"), "wb+"
                            ) as tex:
                                tex.write(f)
                except:
                    print("Gzip didn't work, so either file is corrupted, or it's not tex")
                    continue
            finally:
                os.remove(p)

    def main(self):
        if not os.path.exists(self.cfg.ids_path):
            raise OSError(f"'{self.cfg.ids_path}' doesn't exist")

        # if os.path.exists(self.cfg.output_dir):
        #     raise OSError(f"Output dir is already exists")
        # os.makedirs(self.cfg.output_dir)

        with open(self.cfg.ids_path) as i:
            ids = [el.rstrip("\n") for el in i.readlines()]

        # limit = (
        #     None if (not "limit" in self.cfg or not self.cfg.limit) else self.cfg.limit
        # )
        # if limit:
        ids = ids[self.cfg.limit_from : self.cfg.limit_to]

        multiprocessing.set_start_method("spawn")
        threads = [
            multiprocessing.Process(target=self.worker, args=((ids[arg[0] : arg[1]],)))
            for arg in compute_threads_work(len(ids), self.cfg.workers)
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
        help="Arxiv downloader config path",
        required=True,
    )

    args = parser.parse_args()

    ad = ArxivDownloader(args.config_path)
    ad.main()
