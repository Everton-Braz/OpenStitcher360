from pypdf import PdfReader
import sys

try:
    reader = PdfReader("helper_docs/optical-flow-dual-fisheye-stitching-guide (1).pdf")
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    
    with open("helper_docs/guide_content.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("PDF content saved to helper_docs/guide_content.txt")
except Exception as e:
    print(f"Error reading PDF: {e}")
