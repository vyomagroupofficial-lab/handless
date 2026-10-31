"""Download the offline Whisper Base (English, int8) model used by the release build.

Extracts only the int8 encoder/decoder and tokens into models/sherpa-onnx-whisper-base.en/.
"""

from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-base.en.tar.bz2"
ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "models" / "sherpa-onnx-whisper-base.en"
WANTED = ("base.en-encoder.int8.onnx", "base.en-decoder.int8.onnx", "base.en-tokens.txt")


def main() -> None:
    if all((DEST / f).exists() for f in WANTED):
        print(f"Model already present at {DEST}")
        return
    DEST.mkdir(parents=True, exist_ok=True)
    archive = DEST.parent / "sherpa-onnx-whisper-base.en.tar.bz2"
    print(f"Downloading {URL} ...")
    urllib.request.urlretrieve(URL, archive)
    with tarfile.open(archive, "r:bz2") as tar:
        for member in tar.getmembers():
            name = Path(member.name).name
            if name in WANTED and member.isfile():
                member.name = name
                tar.extract(member, DEST)
    archive.unlink(missing_ok=True)
    missing = [f for f in WANTED if not (DEST / f).exists()]
    if missing:
        raise SystemExit(f"Archive did not contain: {', '.join(missing)}")
    print(f"Model installed to {DEST}")


if __name__ == "__main__":
    main()
