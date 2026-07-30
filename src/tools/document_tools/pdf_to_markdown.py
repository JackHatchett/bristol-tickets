#!/usr/bin/env python3
import os
import subprocess
import shutil

def run_cmd(cmd):
    """Run a shell command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

def process_pdf(pdf_path, output_dir):
    """Run OCR + pdftotext on a single PDF."""
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    ocr_pdf = os.path.join(output_dir, f"{base}_OCR.pdf")
    md_file = os.path.join(output_dir, f"{base}.md")

    # Step 1: OCR
    ocr_cmd = f'ocrmypdf --skip-text --tagged-pdf-mode ignore "{pdf_path}" "{ocr_pdf}"'
    ok_ocr, ocr_msg = run_cmd(ocr_cmd)
    if not ok_ocr:
        return False, f"OCR failed: {ocr_msg}"

    # Step 2: Convert OCR PDF → Markdown
    txt_cmd = f'pdftotext -layout "{ocr_pdf}" "{md_file}"'
    ok_txt, txt_msg = run_cmd(txt_cmd)
    if not ok_txt:
        return False, f"pdftotext failed: {txt_msg}"

    return True, "Success"

def main():
    print("Enter the directory containing your PDFs:")
    target_dir = input("> ").strip()

    if not os.path.isdir(target_dir):
        print("Error: directory does not exist.")
        return

    processed_dir = os.path.join(target_dir, "processed_pdfs")
    os.makedirs(processed_dir, exist_ok=True)

    pdfs = [f for f in os.listdir(target_dir) if f.lower().endswith(".pdf")]

    if not pdfs:
        print("No PDFs found in that directory.")
        return

    print(f"Found {len(pdfs)} PDFs. Beginning processing...\n")

    for pdf in pdfs:
        pdf_path = os.path.join(target_dir, pdf)
        print(f"Processing: {pdf}")

        ok, msg = process_pdf(pdf_path, target_dir)

        if ok:
            print(f"✓ {pdf} processed successfully.")
            shutil.move(pdf_path, os.path.join(processed_dir, pdf))
        else:
            print(f"✗ {pdf} failed: {msg}")

    print("\nDone.")
    print(f"Successful PDFs moved to: {processed_dir}")
    print("Markdown files are in the same directory you provided.")

if __name__ == "__main__":
    main()
