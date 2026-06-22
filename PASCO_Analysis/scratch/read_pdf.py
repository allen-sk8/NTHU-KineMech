import os
import sys

def try_extract_pypdf(pdf_path):
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"pypdf failed: {e}"

def try_extract_pdfplumber(pdf_path):
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"pdfplumber failed: {e}"

def main():
    # 尋找 refer_results/sj/SJ Report 下的一個 PDF
    pdf_dir = r"c:\Users\allensk8\vscode-all-in-one\Local_workspace\NTHU-KineMech\PASCO_Analysis\refer_results\sj\SJ Report"
    if not os.path.exists(pdf_dir):
        print(f"Directory {pdf_dir} does not exist")
        return
        
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
    if not pdf_files:
        print("No PDF files found")
        return
        
    sample_pdf = os.path.join(pdf_dir, pdf_files[0])
    print(f"Analyzing PDF: {sample_pdf}")
    
    # 嘗試安裝 pypdf 以便讀取
    try:
        import pypdf
    except ImportError:
        print("pypdf not installed, trying to install...")
        os.system("pip install pypdf")
        
    text = try_extract_pypdf(sample_pdf)
    print("\n--- Extracted Text ---")
    print(text[:3000])  # 印出前 3000 個字

if __name__ == "__main__":
    main()
