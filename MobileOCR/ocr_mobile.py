import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

import cv2

TESS_TO_EASYOCR = {
    "deu": "de", "eng": "en", "fra": "fr", "spa": "es", "ita": "it",
    "por": "pt", "nld": "nl", "rus": "ru", "pol": "pl", "tur": "tr",
    "ukr": "uk", "ara": "ar", "hin": "hi", "jpn": "ja", "kor": "ko",
    "chi_sim": "ch_sim", "chi_tra": "ch_tra",
}

_easy_reader = None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="OCR direkt auf dem Handy (Pydroid 3 oder Termux): Foto aufnehmen oder "
        "vorhandenes Bild laden, mit OpenCV vorverarbeiten und per OCR-Engine auslesen."
    )
    parser.add_argument("--image", help="Pfad zu einem vorhandenen Foto (z. B. /sdcard/DCIM/foto.jpg)")
    parser.add_argument("--camera", action="store_true",
                        help="Foto mit der Kamera des Geraets aufnehmen (Standard, wenn --image fehlt)")
    parser.add_argument("--camera-id", type=int, default=0, help="Kamera-ID (0 = meist Hauptkamera)")
    parser.add_argument("--engine", choices=["auto", "easyocr", "tesseract"], default="auto",
                        help="OCR-Engine: easyocr (Pydroid 3) oder tesseract (Termux/PC), auto = verfuegbare waehlen")
    parser.add_argument("--lang", default="deu+eng", help="Sprachen, z. B. deu+eng (Tesseract) bzw. de+en (EasyOCR)")
    parser.add_argument("--psm", type=int, default=3, help="Tesseract Page Segmentation Mode (Default: 3, nur Tesseract)")
    parser.add_argument("--thresh", choices=["otsu", "adaptive", "none"], default="otsu",
                        help="Binarisierung nach der Vorverarbeitung")
    parser.add_argument("--max-dim", type=int, default=1600,
                        help="Laengere Bildkante wird auf diesen Wert skaliert (Default: 1600)")
    parser.add_argument("--out", default="ocr_output", help="Ausgabeverzeichnis (Default: ocr_output)")
    return parser.parse_args(argv)


def capture_with_plyer(path):
    try:
        from plyer import camera
    except Exception:
        return False
    try:
        camera.take_picture(filename=path)
    except TypeError:
        try:
            camera.take_picture(path)
        except Exception:
            return False
    except Exception:
        return False
    for _ in range(300):
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return True
        time.sleep(0.1)
    return os.path.isfile(path) and os.path.getsize(path) > 0


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
    if capture_with_plyer(path):
        return "plyer (Pydroid 3 Kamera)"
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


def tesseract_available():
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def easyocr_available():
    try:
        import easyocr  # noqa: F401
        return True
    except Exception:
        return False


def select_engine(requested):
    if requested == "tesseract":
        if tesseract_available():
            return "tesseract"
        raise RuntimeError(
            "Tesseract wurde nicht gefunden. Termux: 'pkg install tesseract' | "
            "PC: 'sudo apt install tesseract-ocr' | Pydroid 3: --engine easyocr nutzen."
        )
    if requested == "easyocr":
        if easyocr_available():
            return "easyocr"
        raise RuntimeError(
            "easyocr ist nicht installiert. Pydroid 3: 'pip install easyocr' "
            "(legt die Modelle beim ersten Start automatisch in ~/.EasyOCR ab)."
        )
    if tesseract_available():
        return "tesseract"
    if easyocr_available():
        return "easyocr"
    raise RuntimeError(
        "Keine OCR-Engine gefunden. Installiere entweder Tesseract "
        "(Termux: pkg install tesseract / PC: apt install tesseract-ocr) "
        "oder easyocr (Pydroid 3: pip install easyocr)."
    )


def easyocr_langs(lang):
    return [TESS_TO_EASYOCR.get(part, part) for part in lang.split("+")]


def get_easy_reader(langs):
    global _easy_reader
    if _easy_reader is None:
        import easyocr
        _easy_reader = easyocr.Reader(langs, gpu=False)
    return _easy_reader


def run_ocr_tesseract(image, lang, psm):
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
    words = []
    for i in range(len(data["text"])):
        word = str(data["text"][i]).strip()
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if word:
            box = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
            words.append((word, conf, box))
    return text.strip(), words


def run_ocr_easyocr(image, lang):
    reader = get_easy_reader(easyocr_langs(lang))
    if image.ndim == 2:
        rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    else:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = reader.readtext(rgb)
    words = []
    texts = []
    for bbox, text, conf in results:
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]
        x, y = int(min(xs)), int(min(ys))
        box = (x, y, int(max(xs)) - x, int(max(ys)) - y)
        words.append((text, float(conf) * 100.0, box))
        texts.append(text)
    return " ".join(texts), words


def run_ocr(image, lang, psm, engine):
    if engine == "easyocr":
        return run_ocr_easyocr(image, lang)
    return run_ocr_tesseract(image, lang, psm)


def annotate(image, words):
    annotated = image.copy()
    for word, conf, (x, y, w, h) in words:
        if word and conf > 60:
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return annotated


def main(argv=None):
    args = parse_args(argv)
    if args.image is None and not args.camera:
        args.camera = True

    try:
        engine = select_engine(args.engine)
    except RuntimeError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2
    print(f"OCR-Engine: {engine}")

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
                print("Pydroid 3: 'pip install plyer' und Kamera-Berechtigung der App erlauben.", file=sys.stderr)
                print("Termux:    'pkg install termux-api' + Termux:API-App.", file=sys.stderr)
                print("Oder vorhandenes Foto nutzen: --image PFAD", file=sys.stderr)
                return 2

        print(f"Bildquelle: {source}")
        original = load_and_resize(photo_path, args.max_dim)
        processed = preprocess(original, args.thresh)
        text, words = run_ocr(processed, args.lang, args.psm, engine)
        annotated = annotate(original, words)

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
