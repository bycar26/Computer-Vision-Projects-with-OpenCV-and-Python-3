# MobileOCR – Schrifterkennung (OCR) direkt auf dem Handy

Eine kleine OCR-Software in **Python + OpenCV**, die komplett auf dem Smartphone läuft
(100 % offline, keine Cloud, keine Internetverbindung nötig).

Ablauf: Foto mit der Handykamera aufnehmen (oder vorhandenes Foto laden) → mit OpenCV
vorverarbeiten (Graustufen, Entrauschen, Kontrast, Binarisierung) → mit Tesseract den
Text auslesen → erkannter Text und annotiertes Bild werden gespeichert.

## Dateien

| Datei | Zweck |
| ----- | ----- |
| `ocr_mobile.py` | Das eigentliche Programm (Kamera + Vorverarbeitung + OCR + Ausgabe) |
| `install_termux.sh` | Installationsskript für Termux (Android) |
| `requirements.txt` | Python-Pakete zum Testen auf dem PC |

## Voraussetzungen (Android)

- **Termux** (Terminal-App, am besten von [F-Droid](https://f-droid.org/packages/com.termux/))
- **Termux:API** (App aus derselben Quelle wie Termux, z. B. F-Droid) – nur nötig für `--camera`
- Dieser Ordner auf dem Handy, z. B. nach `~/MobileOCR` kopieren

## Installation auf dem Handy (Termux)

```bash
cd ~
# Repo bzw. diesen Ordner auf das Handy übertragen, dann:
cd MobileOCR
bash install_termux.sh
```

Das Skript installiert Python, Tesseract, Termux:API und OpenCV (`pkg install opencv-python`)
sowie die Python-Pakete `pytesseract` und `Pillow` und richtet den Speicherzugriff ein
(`termux-setup-storage` → Berechtigung im Popup erlauben).

**Wichtig für die Kamera:** Die Termux:API-App installieren und in den Android-Einstellungen
unter *Apps → Termux:API → Berechtigungen* die **Kamera** erlauben. Beim ersten
`termux-camera-photo` wird ebenfalls danach gefragt.

**Deutsche Sprache:** Termux installiert evtl. nur englische Tesseract-Sprachdaten.
Prüfen mit `tesseract --list-langs`. Falls `deu` fehlt, `deu.traineddata` (aus dem
[tessdata-Repo](https://github.com/tesseract-ocr/tessdata)) nach
`$PREFIX/share/tessdata/` kopieren, z. B.:

```bash
curl -L -o "$PREFIX/share/tessdata/deu.traineddata" \
  https://github.com/tesseract-ocr/tessdata_fast/raw/main/deu.traineddata
```

## Benutzung

```bash
cd ~/MobileOCR

# 1) Foto direkt mit der Handykamera aufnehmen und erkennen
python ocr_mobile.py --camera --lang deu+eng

# 2) Vorhandenes Foto aus der Galerie erkennen (nach termux-setup-storage erreichbar)
python ocr_mobile.py --image ~/storage/DCIM/Camera/foto.jpg --lang deu+eng

# 3)Nur englischer Text, andere Binarisierung
python ocr_mobile.py --image foto.jpg --lang eng --thresh adaptive
```

Wichtige Optionen (alle mit `python ocr_mobile.py --help`):

| Option | Bedeutung | Default |
| ------ | --------- | ------- |
| `--image PFAD` | Vorhandenes Foto statt Kamera | – |
| `--camera` | Foto mit der Kamera aufnehmen | aktiv, wenn `--image` fehlt |
| `--lang` | Tesseract-Sprachen | `deu+eng` |
| `--psm` | Tesseract Page Segmentation Mode | `3` |
| `--thresh` | `otsu`, `adaptive` oder `none` | `otsu` |
| `--max-dim` | Bild wird auf max. Kantenlänge skaliert (schneller auf dem Handy) | `1600` |
| `--out` | Ausgabeverzeichnis | `ocr_output` |

## Ausgabe

Nach jedem Lauf liegen im Ausgabeverzeichnis (Default `ocr_output/`):

- `ocr_text.txt` – der erkannte Text (auch in der Konsole ausgegeben)
- `ocr_annotated.jpg` – das Foto mit grün eingezeichneten erkannten Wörtern
- `ocr_preprocessed.jpg` – das OpenCV-vorverarbeitete Bild, das an Tesseract ging

## Funktionsweise (Pipeline in `ocr_mobile.py`)

1. **Bildquelle:** `termux-camera-photo` (Handykamera via Termux:API) oder Fallback
   `cv2.VideoCapture` (z. B. Webcam am PC).
2. **Vorverarbeitung mit OpenCV:** Verkleinern auf `--max-dim`, Graustufen,
   Median-Filter (Entrauschen), CLAHE (Kontrast), Otsu- bzw. adaptive Binarisierung.
3. **OCR:** `pytesseract` (Tesseract) liefert Text und Wort-Positionen (Confidence > 60).
4. **Ausgabe:** Textdatei + annotiertes Bild.

## Alternativen

- **Pydroid 3** (Google Play/F-Droid): Python-IDE fürs Handy mit vorinstalliertem `cv2`.
  Dort `pip install pytesseract pillow`, Tesseract-Binary fehlt allerdings – daher ist
  Termux die empfohlene Variante für die Kamera.
- **PC-Test:** `pip install -r requirements.txt` und `sudo apt install tesseract-ocr`,
  dann z. B. `python ocr_mobile.py --image foto.jpg` (mit `--camera` Webcam-Test).

## Troubleshooting

- `Fehler: Tesseract wurde nicht gefunden` → `pkg install tesseract` (Termux) bzw.
  `sudo apt install tesseract-ocr` (PC).
- `Fehler: Keine Kamera erreichbar` → Termux:API-App installiert? Kamera-Berechtigung
  erteilt? `pkg install termux-api` nicht vergessen. Alternativ `--image` nutzen.
- `termux-camera-photo` hängt → Berechtigungs-Popup in der Termux:API-App bestätigen
  bzw. Berechtigung in den Android-App-Einstellungen setzen.
- Schlechte Erkennung → anderes `--thresh` probieren, `--psm 6` für einzelne Textblöcke,
  `--max-dim 2400` für mehr Details, Foto mit besserem Licht/gerader Perspektive.
- `deu` fehlt in `tesseract --list-langs` → siehe Abschnitt „Deutsche Sprache" oben;
  das Programm fällt automatisch auf `eng` zurück.

## Datenschutz

Alles läuft lokal auf dem Gerät: Kamera, Bildverarbeitung und OCR erfolgen vollständig
offline auf dem Handy. Es werden keine Bilder oder Texte an einen Server übertragen.
