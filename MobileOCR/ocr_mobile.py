import argparse
import os
import shutil
import subprocess
import sys
import tempfile

import cv2


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="OCR direkt auf dem Handy: Foto aufnehmen oder vorhandenes Bild laden, "
        "mit OpenCV vorverarbeiten und per Tesseract auslesen."
    )
    parser.add_argument("--image", help="Pfad zu einem vorhandenen Foto (z. B. /sdcard/DCIM/foto.jpg)")
    parser.add_argument("--camera", action="store_true",
                        help="Foto mit der Kamera des Geraets aufnehmen (Standard, wenn --image fehlt)")
    parser.add_argument("--camera-id", type=int, default=0, help="Kamera-ID (0 = meist Hauptkamera)")
    parser.add_argument("--lang", default="deu+eng", help="Tesseract-Sprachen, z. B. deu, eng, deu+eng")
    parser.add_argument("--psm", type=int, default=3, help="Tesseract Page Segmentation Mode (Default: 3)")
    parser.add_argument("--thresh", choices=["otsu", "adaptive", "none"], default="otsu",
                        help="Binarisierung nach der Vorverarbeitung")
    parser.add_argument("--max-dim", type=int, default=1600,
                        help="Laengere Bildkante wird auf diesen Wert skaliert (Default: 1600)")
    parser.add_argument("--out", default="ocr_output", help="Ausgabeverzeichnis (Default: ocr_output)")
    return parser.parse_args(argv)


def capture_with_termux(path, camera_id):
    if shutil.which("termux-camera-photo") is None:
        return False
    result = subprocess.run(
        ["termux-camera-photo", "-c", str(camera_id), path],
        capture_output=True, text=True,
    )
    return result.returncode == 0 and os.path.isfile(path)


def capture_with_cv2(path, camera_id):
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        return False
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return False
    return cv2.imwrite(path, frame)


def capture_photo(path, camera_id):
    if capture_with_termux(path, camera_id):
        return "termux-camera-photo (Handykamera)"
    if capture_with_cv2(path, camera_id):
        return "cv2.VideoCapture (Webcam)"
    return None


def load_and_resize(path, max_dim):
    image = cv2.imread(path)
    if image is None:
        raise ValueError(f"Bild konnte nicht geladen werden: {path}")
    h, w = image.shape[:2]
    scale = max_dim / float(max(h, w))
    if scale < 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return image


def preprocess(image, method):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    if method == "otsu":
        _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif method == "adaptive":
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
        )
    return gray


def check_tesseract():
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def run_ocr(image, lang, psm):
    import pytesseract
    from pytesseract import Output
    config = f"--psm {psm}"
    try:
        text = pytesseract.image_to_string(image, lang=lang, config=config)
        data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=Output.DICT)
    except pytesseract.TesseractError as exc:
        message = str(exc).lower()
        if lang != "eng" and ("lang" in message or "traineddata" in message or "data" in message):
            print(f"Hinweis: Sprachdaten fuer '{lang}' nicht gefunden, "
                  f"falle auf 'eng' zurueck.", file=sys.stderr)
            text = pytesseract.image_to_string(image, lang="eng", config=config)
            data = pytesseract.image_to_data(image, lang="eng", config=config, output_type=Output.DICT)
        else:
            raise
    return text.strip(), data


def annotate(image, data):
    annotated = image.copy()
    for i in range(len(data["text"])):
        word = str(data["text"][i]).strip()
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if word and conf > 60:
            x, y = data["left"][i], data["top"][i]
            w, h = data["width"][i], data["height"][i]
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return annotated


def main(argv=None):
    args = parse_args(argv)
    if args.image is None and not args.camera:
        args.camera = True

    if not check_tesseract():
        print("Fehler: Tesseract wurde nicht gefunden oder ist nicht installiert.", file=sys.stderr)
        print("Auf dem Handy (Termux):  pkg install tesseract", file=sys.stderr)
        print("Auf dem PC:              sudo apt install tesseract-ocr", file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        if args.image is not None:
            if not os.path.isfile(args.image):
                print(f"Fehler: Datei nicht gefunden: {args.image}", file=sys.stderr)
                return 2
            photo_path = args.image
            source = "Datei"
        else:
            photo_path = os.path.join(tmpdir, "capture.jpg")
            source = capture_photo(photo_path, args.camera_id)
            if source is None:
                print("Fehler: Keine Kamera erreichbar.", file=sys.stderr)
                print("Termux: 'pkg install termux-api', Termux:API-App installieren "
                      "und Kamera-Berechtigung erlauben.", file=sys.stderr)
                print("Oder vorhandenes Foto nutzen: --image PFAD", file=sys.stderr)
                return 2

        print(f"Bildquelle: {source}")
        original = load_and_resize(photo_path, args.max_dim)
        processed = preprocess(original, args.thresh)
        text, data = run_ocr(processed, args.lang, args.psm)
        annotated = annotate(original, data)

        text_path = os.path.join(args.out, "ocr_text.txt")
        annotated_path = os.path.join(args.out, "ocr_annotated.jpg")
        processed_path = os.path.join(args.out, "ocr_preprocessed.jpg")
        with open(text_path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        cv2.imwrite(annotated_path, annotated)
        cv2.imwrite(processed_path, processed)

    print("-" * 50)
    print(text if text else "(kein Text erkannt)")
    print("-" * 50)
    print(f" erkannter Text:       {text_path}")
    print(f" annotiertes Bild:      {annotated_path}")
    print(f" vorverarbeitetes Bild: {processed_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
