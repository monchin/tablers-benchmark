from tablers import Document as TabDoc, find_tables
from pymupdf import Document as MuDoc
import pdfplumber
import time
from io import BytesIO
import matplotlib.pyplot as plt

pdf_bytes = open('boc_20220025_0001_p000.pdf', 'rb').read()

def benchmark_tablers():
    tic = time.time()
    with TabDoc(bytes=pdf_bytes) as doc:
        for page in doc.pages():
            tables = find_tables(page, extract_text=True)
    toc = time.time()
    return toc - tic

def benchmark_pymupdf():
    tic = time.time()
    with MuDoc(stream=pdf_bytes) as doc:
        for page in doc:
            tables = page.find_tables()
    toc = time.time()
    return toc - tic

def benchmark_pdfplumber():
    tic = time.time()
    with pdfplumber.open(BytesIO(pdf_bytes)) as doc:
        for page in doc.pages:
            tables = page.find_tables()
            page.close() # avoid memory leak
    toc = time.time()
    return toc - tic



if __name__ == "__main__":
    dur_tablers = benchmark_tablers()
    dur_pymupdf = benchmark_pymupdf()
    dur_pdfplumber = benchmark_pdfplumber()

    ratio_tablers = 1
    ratio_pymupdf = dur_pymupdf / dur_tablers
    ratio_pdfplumber = dur_pdfplumber / dur_tablers

    fig, ax = plt.subplots()
    bars = ax.bar(['tablers', 'pymupdf', 'pdfplumber'], [ratio_tablers, ratio_pymupdf, ratio_pdfplumber])
    
    for bar, ratio in zip(bars, [ratio_tablers, ratio_pymupdf, ratio_pdfplumber]):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{ratio:.2f}X',
                ha='center', va='bottom')
    
    ax.set_ylabel('Time (seconds)')
    ax.set_title('PDF Processing Time Comparison')
    
    plt.savefig("table_extraction_benchmark.png")