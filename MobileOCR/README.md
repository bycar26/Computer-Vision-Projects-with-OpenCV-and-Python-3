# MobileOCR – Schrifterkennung (OCR) direkt auf dem Handy

Eine kleine OCR-Software in **Python + OpenCV**, die komplett auf dem Smartphone läuft
(100 % offline, keine Cloud – nach der einmaligen Installation bzw. dem einmaligen
Modell-Download ist keine Internetverbindung mehr nötig).

**Basis: Pydroid 3** (Python-IDE für Android). Alternativ funktioniert das Programm auch
in **Termux** – siehe unten.

Ablauf: Foto mit der Handykamera aufnehmen (oder vorhandenes Foto laden) → mit OpenCV
vorverarbeiten (Graustufen, Entrauschen, Kontrast, Binarisierung) → per OCR-Engine den
Text auslesen → erkannter Text und annotiertes Bild werden gespeichert.

## Dateien

| Datei | Zweck |
| ----- | ----- |
| `ocr_mobile.py` | Das eigentliche Programm (Kamera + Vorverarbeitung + OCR + Ausgabe) |
| `requirements-pydroid.txt` | Python-Pakete für **Pydroid 3** (EasyOCR als OCR-Engine, plyer für die Kamera) |
| `install_termux.sh` | Installationsskript für die Termux-Alternative (Tesseract als Engine) |
| `requirements.txt` | Python-Pakete zum Testen auf dem PC |

## Installation auf dem Handy mit Pydroid 3 (empfohlen)

1. **Pydroid 3** installieren (Google Play oder F-Droid).
2. Diesen Ordner auf das Handy übertragen (z. B. `MobileOCR` in den internen Speicher
   oder nach `/sdcard/Documents/Pydroid3/` kopieren) und in Pydroid 3 öffnen.
3. Im Terminal von Pydroid 3 (unten das Terminal-Icon) ausführen:

   ```bash
   pip install -r requirements-pydroid.txt
   ```

   Damit werden installiert: `opencv-python` (cv2), **easyocr** (OCR-Engine, reines Python,
   läuft komplett auf dem Handy), `plyer` (Kamerazugriff), Pillow, numpy.
   *Hinweis:* `easyocr` lädt beim **ersten Start** automatisch die OCR-Modelle
   (ca. 100 MB) nach `~/.EasyOCR` – dafür ist einmalig Internet nötig. Danach
   funktioniert alles offline. `pip install easyocr` installiert auch PyTorch
   (groß, ~200 MB) – Pydroid 3 lädt die passenden Pakete automatisch.
4. Pydroid 3 in den Android-App-Einstellungen die **Kamera-Berechtigung** geben
   (und ggf. Speicherzugriff, falls Fotos aus der Galerie geladen werden sollen).

## Benutzung

In Pydroid 3 das Skript `ocr_mobile.py` öffnen und ausführen (Play-Button), oder im
Terminal:

```bash
cd /sdcard/Documents/Pydroid3/MobileOCR   # Pfad an deine Ablage anpassen

# 1) Foto direkt mit der Handykamera aufnehmen und erkennen (Pydroid 3)
python ocr_mobile.py --camera --engine easyocr --lang de+en

# 2) Vorhandenes Foto aus der Galerie erkennen
python ocr_mobile.py --image /sdcard/DCIM/Camera/foto.jpg --lang de+en

# 3) Engine automatisch waehlen (easyocr in Pydroid, tesseract in Termux/PC)
python ocr_mobile.py --camera --lang deu+eng
```

Wichtige Optionen (alle mit `python ocr_mobile.py --help`):

| Option | Bedeutung | Default |
| ------ | --------- | ------- |
| `--image PFAD` | Vorhandenes Foto statt Kamera | – |
| `--camera` | Foto mit der Kamera aufnehmen | aktiv, wenn `--image` fehlt |
| `--engine` | `easyocr` (Pydroid 3), `tesseract` (Termux/PC) oder `auto` | `auto` |
| `--lang` | Sprachen: `de+en` (EasyOCR) bzw. `deu+eng` (Tesseract) | `deu+eng` |
| `--psm` | Tesseract Page Segmentation Mode (nur Tesseract) | `3` |
| `--thresh` | `otsu`, `adaptive` oder `none` | `otsu` |
| `--max-dim` | Bild wird auf max. Kantenlänge skaliert (schneller auf dem Handy) | `1600` |
| `--out` | Ausgabeverzeichnis | `ocr_output` |

## Ausgabe

Nach jedem Lauf liegen im Ausgabeverzeichnis (Default `ocr_output/`):

- `ocr_text.txt` – der erkannte Text (auch in der Konsole ausgegeben)
- `ocr_annotated.jpg` – das Foto mit grün eingezeichneten erkannten Wörtern
- `ocr_preprocessed.jpg` – das OpenCV-vorverarbeitete Bild, das an die OCR-Engine ging

## Funktionsweise (Pipeline in `ocr_mobile.py`)

1. **Bildquelle:** `plyer` (Pydroid 3, Kamera-App der Wahl) → `termux-camera-photo`
   (Termux) → `cv2.VideoCapture` (Webcam am PC).
2. **Vorverarbeitung mit OpenCV:** Verkleinern auf `--max-dim`, Graustufen,
   Median-Filter (Entrauschen), CLAHE (Kontrast), Otsu- bzw. adaptive Binarisierung.
3. **OCR-Engine:**
   - **EasyOCR** (Pydroid 3): reines Python/PyTorch, erkennt Text direkt on-device,
     liefert Wort-Positionen und Konfidenz.
   - **Tesseract** via `pytesseract` (Termux/PC): leichtgewichtig, braucht das
     Tesseract-Binary und Sprachdaten (`tesseract --list-langs`).
   - `auto` wählt automatisch die verfügbare Engine.
4. **Ausgabe:** Textdatei + annotiertes Bild (Wörter mit Konfidenz > 60).

## Alternative: Termux (statt Pydroid 3)

```bash
cd ~/MobileOCR
bash install_termux.sh        # installiert python, tesseract, termux-api, opencv-python
termux-setup-storage          # Speicherzugriff erlauben
# Termux:API-App aus derselben Quelle wie Termux installieren + Kamera-Berechtigung
python ocr_mobile.py --camera --engine tesseract --lang deu+eng
```

Falls `deu` in `tesseract --list-langs` fehlt: `deu.traineddata` (aus dem
[tessdata-Repo](https://github.com/tesseract-ocr/tessdata)) nach `$PREFIX/share/tessdata/`
kopieren. Bei EasyOCR genügt `--lang de+en` – die Modelle liegen nach dem ersten Start
in `~/.EasyOCR`.

## PC-Test

```bash
pip install -r requirements.txt
sudo apt install tesseract-ocr
python ocr_mobile.py --image foto.jpg            # Engine auto -> tesseract
python ocr_mobile.py --camera                    # Webcam-Test
```

## Troubleshooting

- `Fehler: easyocr ist nicht installiert` → in Pydroid 3: `pip install -r requirements-pydroid.txt`
  (dauert wegen PyTorch eine Weile, ca. 200 MB).
- `Fehler: Keine Kamera erreichbar` → in Pydroid 3 `pip install plyer` und der Pydroid-3-App
  die Kamera-Berechtigung geben; alternativ `--image PFAD` nutzen.
- EasyOCR-Fehler beim ersten Start (Download) → einmalig Internet erlauben; die Modelle
  liegen dann lokal in `~/.EasyOCR`.
- Schlechte Erkennung → anderes `--thresh` probieren, `--max-dim 2400` für mehr Details,
  Foto mit besserem Licht und gerader Perspektive aufnehmen.
- Tesseract: `deu` fehlt → siehe Termux-Abschnitt; das Programm fällt automatisch auf
  `eng` zurück.

## Datenschutz

Kamera, Bildverarbeitung und OCR laufen lokal auf dem Gerät. Nach der einmaligen
Installation der Pakete/Modelle werden keine Bilder oder Texte an einen Server
übertragen.
