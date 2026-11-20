#!/usr/bin/env bash
set -e

pkg update -y
pkg install -y python tesseract termux-api x11-repo
pkg update -y
pkg install -y opencv-python || pkg install -y opencv

pip install --upgrade pip
pip install pytesseract pillow

python -c "import cv2; print('OpenCV-Version:', cv2.__version__)"
echo "Verfuegbare Tesseract-Sprachen:"
tesseract --list-langs

termux-setup-storage

echo ""
echo "Installation fertig."
echo "1) Termux:API-App aus derselben Quelle wie Termux installieren (F-Droid empfohlen)"
echo "   und in den App-Einstellungen die Kamera-Berechtigung erlauben."
echo "2) Falls 'deu' nicht in der Sprachliste auftaucht: deu.traineddata nach"
echo "   \$PREFIX/share/tessdata/ kopieren (z. B. aus dem tessdata-GitHub-Repo)."
echo "3) Starten:  python ocr_mobile.py --camera --lang deu+eng"
