import cv2
import pytesseract
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from PIL import Image, ImageTk, ExifTags
import os
import time
from difflib import SequenceMatcher
import re

# If Tesseract is not in PATH, uncomment and adjust:
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Linux example
# or leave it commented → let user set it via env var or install properly

def clean_text_japanese(text):
    """Removes extra characters, spaces, and joins fragmented words in Japanese text."""
    cleaned_text = re.sub(r'[^a-zA-Z0-9\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\s\.,!?\'"()-]', '', text)
    cleaned_text = re.sub(r'\s*([、。！？.,!?])\s*', r'\1', cleaned_text)
    cleaned_text = re.sub(r'(?<=\w)\s+(?=\w)', '', cleaned_text)
    cleaned_text = re.sub(r'(?<![\u30a0-\u30ff])ー(?![\u30a0-\u30ff])', '', cleaned_text)
    cleaned_text = re.sub(r'([ー]{2,})', 'ー', cleaned_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    return cleaned_text

def clean_text_english(text):
    """Cleans extra characters, joins broken words for English text,
    adds spaces after punctuation marks and removes extra spaces."""
    cleaned_text = re.sub(r'[^a-zA-Z0-9\s\.,!?\'"-]', '', text)
    cleaned_text = re.sub(r'(?<=\w)\s+(?=\w)', ' ', cleaned_text)
    cleaned_text = re.sub(r'([.,!?])(?=\S)', r'\1 ', cleaned_text)
    cleaned_text = re.sub(r'\s*([.,!?])\s*', r'\1 ', cleaned_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

def clean_text_ukrainian(text):
    """Cleans extra characters, joins broken words for Ukrainian text,
    adds spaces after punctuation marks and removes extra spaces."""
    cleaned_text = re.sub(r'[^a-zA-Zа-яА-ЯіІї ЇєЄ0-9\s\.,!?\'"-]', '', text)
    cleaned_text = re.sub(r'(?<=\w)\s+(?=\w)', ' ', cleaned_text)
    cleaned_text = re.sub(r'([.,!?])(?=\S)', r'\1 ', cleaned_text)
    cleaned_text = re.sub(r'\s*([.,!?])\s*', r'\1 ', cleaned_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    return cleaned_text

def clean_text(text, language):
    if language == 'jpn':
        return clean_text_japanese(text)
    elif language == 'eng':
        return clean_text_english(text)
    elif language == 'ukr':
        return clean_text_ukrainian(text)
    else:
        return text

def calculate_similarity(reference_text, recognized_text):
    matcher = SequenceMatcher(None, reference_text, recognized_text)
    correct_chars = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            correct_chars += (i2 - i1)
        elif tag == 'replace':
            correct_chars += min(i2 - i1, j2 - j1)
    total_chars = len(reference_text)
    if total_chars == 0:
        return 0.0
    accuracy_percentage = (correct_chars / total_chars) * 100
    return accuracy_percentage

def check_image_size(image_path):
    file_size = os.path.getsize(image_path)
    if file_size > 5 * 1024 * 1024:  # 5 MB
        return False
    return True

def adjust_gamma(image, gamma=1.0):
    """Gamma correction function."""
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)


def remove_shadows(image):
    """Function to remove shadows from the image."""
    rgb_planes = cv2.split(image)  # Split into RGB channels

    result_planes = []
    for plane in rgb_planes:
        # Using morphological closing to estimate background
        dilated_img = cv2.dilate(plane, np.ones((7, 7), np.uint8))
        bg_img = cv2.medianBlur(dilated_img, 21)
        # Subtract background from original image
        diff_img = 255 - cv2.absdiff(plane, bg_img)
        result_planes.append(diff_img)

    result = cv2.merge(result_planes)  # Merge processed channels
    return result

def ocr_from_image(image_path, language='ukr'):
    """Main function for image processing and text recognition."""
    image = cv2.imread(image_path)          # Load image
    shadow_removed = remove_shadows(image)  # Remove shadows
    gray = cv2.cvtColor(shadow_removed, cv2.COLOR_BGR2GRAY)     # Convert to grayscale
    gamma_corrected = adjust_gamma(gray, gamma=4)     # Gamma correction to reduce overexposure
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))     # Apply CLAHE to improve contrast
    enhanced_image = clahe.apply(gamma_corrected)
    blurred = cv2.GaussianBlur(enhanced_image, (3, 3), 0)     # Blur image (to reduce noise)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)     # Binarization for clear text
    kernel = np.ones((1, 1), np.uint8)     # Apply morphological operations to improve text objects
    dilated = cv2.dilate(binary, kernel, iterations=1)
    eroded = cv2.erode(dilated, kernel, iterations=1)

    cv2.imwrite('processed_image.png', eroded)
    if is_vertical and language == 'jpn':
        custom_config = f'--oem 3 --psm 5 -l jpn_vert -c preserve_interword_spaces=1'
    else:
        custom_config = f'--oem 3 --psm 6 -l {language}'
    text = pytesseract.image_to_string(eroded, config=custom_config)

    return text

def select_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.jpeg;*.png")])
    if file_path:
        if not check_image_size(file_path):
            messagebox.showwarning("Warning", "Image size exceeds 5 MB.")
            return
        image_path.set(file_path)
        load_image(file_path)

def load_image(image_path):
    img = Image.open(image_path)
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = img._getexif()
        if exif is not None:
            orientation_value = exif.get(orientation, None)
            if orientation_value == 3:
                img = img.rotate(180, expand=True)
            elif orientation_value == 6:
                img = img.rotate(270, expand=True)
            elif orientation_value == 8:
                img = img.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        pass

    available_width = int(root.winfo_width() * 0.6)
    available_height = int(root.winfo_height() * 0.85)

    img_width, img_height = img.size
    ratio = min(available_width / img_width, available_height / img_height)
    new_width = int(img_width * ratio)
    new_height = int(img_height * ratio)

    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    img_tk = ImageTk.PhotoImage(img)
    image_label.config(image=img_tk)
    image_label.image = img_tk


def perform_ocr():
    if not image_path.get():
        messagebox.showwarning("Warning", "Please select an image.")
        return
    start_time = time.time()
    language = languages[language_combobox.get()]
    recognized_text = ocr_from_image(image_path.get(), language)
    recognized_text = clean_text(recognized_text, language)
    end_time = time.time()
    processing_time = end_time - start_time
    recognized_text_box.delete(1.0, tk.END)
    recognized_text_box.insert(tk.END, recognized_text)
    print(f"Time taken for OCR: {processing_time:.2f} seconds")
    reference_text = simpledialog.askstring("Reference Text", "Enter the reference text for comparison:")
    if reference_text:
        accuracy = calculate_similarity(reference_text, recognized_text)
        messagebox.showinfo("OCR Accuracy", f"Accuracy of recognition: {accuracy:.2f}%")
    with open("recognized_text.txt", "w", encoding='utf-8') as f:
        f.write(recognized_text)

is_vertical = False

def toggle_vertical_text():
    global is_vertical
    is_vertical = not is_vertical
    if is_vertical:
        vertical_status_label.config(text="Vertical Text Mode: Enabled", foreground='green')
    else:
        vertical_status_label.config(text="Vertical Text Mode: Disabled", foreground='red')

root = tk.Tk()
root.title("📄 OCR Text Recognition")
root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}")
root.state('zoomed')
root.configure(bg='#2C3E50')

image_path = tk.StringVar()

languages = {
    'English': 'eng',
    'Ukrainian': 'ukr',
    'Japanese': 'jpn',
}

left_frame = ttk.Frame(root, padding=20, style='TFrame')
left_frame.place(relx=0, rely=0, relwidth=0.4, relheight=1)

right_frame = ttk.Frame(root, padding=20, style='TFrame')
right_frame.place(relx=0.4, rely=0, relwidth=0.6, relheight=1)

select_button = ttk.Button(
    left_frame, text="🖼 Select Image", command=select_image, style='Accent.TButton'
)
select_button.pack(pady=20)

language_label = ttk.Label(left_frame, text="Select Language:", font=('Helvetica', 14, 'bold'), background='#2C3E50', foreground='white')
language_label.pack(pady=10)

language_combobox = ttk.Combobox(left_frame, values=list(languages.keys()), font=('Helvetica', 12))
language_combobox.set("English")
language_combobox.pack(pady=10)

# Add a checkbox to toggle vertical text recognition
vertical_text_var = tk.BooleanVar()  # Variable to store the state of the checkbox
vertical_checkbox = ttk.Checkbutton(
    left_frame, text="Enable Vertical Text", variable=vertical_text_var, command=toggle_vertical_text,
    style='Accent.TButton'
)
vertical_checkbox.pack(pady=10)

vertical_status_label = ttk.Label(left_frame, text="Vertical Text Mode: Disabled", font=('Helvetica', 12), background='#2C3E50', foreground='red')
vertical_status_label.pack(pady=10)

ocr_button = ttk.Button(
    left_frame, text="🔍 Perform OCR", command=perform_ocr, style='Accent.TButton'
)
ocr_button.pack(pady=20)

recognized_text_label = ttk.Label(left_frame, text="Recognized Text:", font=('Helvetica', 14, 'bold'), background='#2C3E50', foreground='white')
recognized_text_label.pack(pady=10)

recognized_text_box = tk.Text(left_frame, wrap='word', font=('Helvetica', 24), height=15, width=40, background='#34495E', foreground='white')
recognized_text_box.pack(pady=10, fill='both', expand=True)

image_label = ttk.Label(right_frame, background='#34495E', foreground='#2C3E50', font=('Helvetica', 10), anchor='center')
image_label.pack(pady=10, fill='both', expand=True)

style = ttk.Style()
style.theme_use('clam')
style.configure('TFrame', background='#2C3E50')
style.configure('TLabel', background='#2C3E50', foreground='white', font=('Helvetica', 12))
style.configure('Accent.TButton', background='#3498DB', foreground='white', font=('Helvetica', 14, 'bold'),
                borderwidth=0)
style.map('Accent.TButton', background=[('active', '#2980B9')])

root.mainloop()
