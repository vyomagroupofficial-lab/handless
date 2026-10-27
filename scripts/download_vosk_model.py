"""Helper script to download the default offline English Vosk speech model (~40MB)."""

import sys
from pathlib import Path
import urllib.request
import zipfile

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
TARGET_DIR = Path("models")
MODEL_NAME = "vosk-model-small-en-us-0.15"


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    dest_folder = TARGET_DIR / MODEL_NAME
    if dest_folder.exists():
        print(f"Model already present at {dest_folder.resolve()}")
        return

    zip_file = TARGET_DIR / f"{MODEL_NAME}.zip"
    print(f"Downloading {MODEL_NAME} from {MODEL_URL}...")
    urllib.request.urlretrieve(MODEL_URL, zip_file)
    print("Extracting...")
    with zipfile.ZipFile(zip_file, "r") as z:
        z.extractall(TARGET_DIR)
    if zip_file.exists():
        zip_file.unlink()
    print(f"Model successfully installed to {dest_folder.resolve()}!")


if __name__ == "__main__":
    main()
