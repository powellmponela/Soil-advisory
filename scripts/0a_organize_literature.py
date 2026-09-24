import os
import re
import shutil

import fitz
import pdfminer.high_level
import pdfplumber
import pypdf
from _project_paths import BASE_DIR

# Configuration
LIT_DIR = BASE_DIR / "Literature"

def clean_name(filename):
    # Remove .pdf and sanitize
    name = filename.replace(".pdf", "")
    name = re.sub(r'[^\w\s-]', '', name).strip()
    name = name.replace(" ", "_")
    return name[:50] # Limit folder name length

def extract_text_all_methods(pdf_path, folder_path):
    methods = {
        "fitz": lambda p: "\n".join([page.get_text() for page in fitz.open(p)]),
        "pdfplumber": lambda p: "\n".join([page.extract_text() or "" for page in pdfplumber.open(p).pages]),
        "pypdf": lambda p: "\n".join([page.extract_text() or "" for page in pypdf.PdfReader(p).pages]),
        "pdfminer": lambda p: pdfminer.high_level.extract_text(p)
    }
    
    results = {}
    for name, func in methods.items():
        try:
            print(f"  Extracting with {name}...")
            text = func(pdf_path)
            results[name] = text
            text_path = os.path.join(folder_path, f"extracted_text_{name}.txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:  # noqa: BLE001 -- each extractor is an independent fallback
            print(f"  {name} failed: {e!s}")
            results[name] = ""
    
    # Return the "best" one (using fitz as primary)
    return results.get("fitz") or results.get("pdfplumber") or results.get("pypdf") or results.get("pdfminer") or ""

def analyze_text(text):
    # Simple keyword search for efficiency factors
    indicators = {
        "AE": r"AE\s*[:=]?\s*(\d+\.?\d*)",
        "NUE": r"NUE\s*[:=]?\s*(\d+\.?\d*)",
        "Yield": r"yield\s*[:=]?\s*(\d+\.?\d*)",
        "PFP": r"PFP\s*[:=]?\s*(\d+\.?\d*)"
    }
    found = {}
    for key, pattern in indicators.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            found[key] = matches[:3] # Keep top 3 matches
    return found

def main():
    if not os.path.exists(LIT_DIR):
        print(f"Directory {LIT_DIR} not found.")
        return

    # Find all PDFs recursively
    pdf_files = []
    for root, dirs, files in os.walk(LIT_DIR):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, f))
    
    print(f"Found {len(pdf_files)} PDFs to process.")

    for file_path in pdf_files:
        filename = os.path.basename(file_path)
        # If it's already in a subfolder (not root LIT_DIR), use that folder
        current_dir = os.path.dirname(file_path)
        if current_dir == LIT_DIR:
            folder_name = clean_name(filename)
            folder_path = os.path.join(LIT_DIR, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            new_pdf_path = os.path.join(folder_path, filename)
            try:
                shutil.copy2(file_path, new_pdf_path)
                os.remove(file_path)
                print(f"Moved and Processing: {filename}")
            except OSError as e:
                print(f"Could not move {filename}: {e}")
                new_pdf_path = file_path # Process in place if move fails
        else:
            folder_path = current_dir
            new_pdf_path = file_path
            print(f"Processing in place: {filename}")

        try:
            
            # Extract Text with all methods
            text = extract_text_all_methods(new_pdf_path, folder_path)
            # Also save a 'best' combined version as extracted_text.txt
            text_path = os.path.join(folder_path, "extracted_text.txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text)

            # Basic Analysis
            metrics = analyze_text(text)
            if metrics:
                summary_path = os.path.join(folder_path, "metrics_summary.txt")
                with open(summary_path, "w", encoding="utf-8") as f:
                    f.writelines(f"{k}: {', '.join(v)}\n" for k, v in metrics.items())
            
            # Remove original if copy succeeded
            try:
                os.remove(file_path)
                print(f"Removed original: {filename}")
            except PermissionError:
                print(f"Warning: Could not remove {filename} (file in use).")

        except Exception as e:  # noqa: BLE001 -- continue processing remaining PDFs
            print(f"Error processing {filename}: {e!s}")

if __name__ == "__main__":
    main()
