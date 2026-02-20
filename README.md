# Multilingual OCR Desktop App

Simple GUI tool for extracting text from images using Tesseract OCR + OpenCV preprocessing.  
Supports English, Ukrainian, Japanese (including vertical text).

## Features
- Shadow removal, gamma correction, CLAHE contrast enhancement
- Language-specific text cleaning
- Basic accuracy comparison against reference text
- Vertical Japanese mode toggle

## Requirements
- Python 3.8+
- `pip install opencv-python pytesseract pillow numpy`
- Tesseract OCR installed<a href="https://github.com/tesseract-ocr/tesseract" target="_blank" rel="noopener noreferrer nofollow"></a>
- On Windows you may need to set the tesseract.exe path manually

## Usage
1. Run `python main.py`
2. Select image → choose language → hit Perform OCR

<img width="1920" height="1040" alt="python_9UKOYC3NUc" src="https://github.com/user-attachments/assets/7b496e66-ff2f-408d-ab3a-6b42d7eed00f" />
