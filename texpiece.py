import argparse
from data_utils.texpiece_dataset import TexPieceDataset


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

    td = TexPieceDataset(args.config_path)
    td.main()
    