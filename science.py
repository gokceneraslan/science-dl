from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
from builtins import range

import sys
import urllib.request, urllib.error, urllib.parse
import urllib.request, urllib.parse, urllib.error
import os
import difflib
import tempfile

# external modules
import PyPDF2
import scrapy.selector as sel

SCIENCE_BASE = 'http://www.sciencemag.org'


def download_mag(url, dir, out):
    sc = urllib.request.urlopen(url).read()
    root = sel.Selector(text=sc)

    articles = root.xpath("//li[contains(@class,'cit')]")
    pages = [x.xpath(".//span[contains(@class,'cit-first-page')]/text()").extract() for x in articles]
    links = [x.xpath(".//div[contains(@class,'cit-extra')]"
                     "//a[contains(@rel,'full-text.pdf')]/@href").extract() for x in articles]

    toc = root.xpath('//*[@id="pdf-matter"]/div[1]/ul/li/a[contains(text(), '
                     '"Print Table of Contents")]/@href').extract()

    #remove articles without links
    no_pdf = [i for i, x in enumerate(links) if not x]

    pages = [p[0] if p else None for i, p in enumerate(pages) if i not in no_pdf]
    links = [p[0] if p else None for i, p in enumerate(links) if i not in no_pdf]
    #articles = [p for i, p in enumerate(articles) if i not in no_pdf]


    #sort pdfs
    sorted_page_index = sort_pages(pages)

    #download pdfs
    if not dir:
        dir = download_pdfs([SCIENCE_BASE + x for x in links])

    #merge pdfs
    merge_pdfs([os.path.join(dir, os.path.basename(links[p])) for p in sorted_page_index], out)

    #remove duplicates
    remove_duplicates(out)

def download_pdfs(links):
    dir = tempfile.mkdtemp()

    for link in links:
        print('Downloading %s...' % link)
        urllib.request.urlretrieve(link, os.path.join(dir, os.path.basename(link)))

    return dir

def merge_pdfs(pdfs, out):
    merger = PyPDF2.PdfFileMerger()
    for p in pdfs:
        merger.append(PyPDF2.PdfFileReader(file(p, 'rb')))
    merger.write(out)

def sort_pages(page_list):
    new_list = page_list[:]
    last = 300
    for i, p in enumerate(page_list):
        if not p:
            new_list[i] = last
        else:
            last = new_list[i]
    return sorted(list(range(len(new_list))), key=lambda k: int(new_list[k]))


def find_duplicate_pages(pdf, similarity=0.9):
    duplicates = []
    #load all contents to memory for fast comparison
    page_contents = [p.extractText().lower() for p in pdf.pages]
    N = pdf.getNumPages()
    for p1 in range(N):
        print('%i / %i' % (p1+1, N))

        if "this copy is for your personal, non-commercial use only" in page_contents[p1]:
            duplicates.append(p1)
            continue

        for p2 in range(p1 + 1, N):
            ratio = difflib.SequenceMatcher(isjunk=lambda x: x in " \t\n",
                                            a=page_contents[p1],
                                            b=page_contents[p2]).ratio()
            #print ratio
            if ratio >= similarity:
                duplicates.append(p2)

    return duplicates


def remove_duplicates(pdf):
    output = PyPDF2.PdfFileWriter()
    input = PyPDF2.PdfFileReader(pdf)

    dups = find_duplicate_pages(input)

    for p in range(input.getNumPages()):
        if p not in dups:
            output.addPage(input.getPage(p))

    with open(pdf, 'wb') as f:
        output.write(f)

dir=None

if len(sys.argv) == 2:
    url = 'http://www.sciencemag.org/content/current'
    out = sys.argv[1]
elif len(sys.argv) == 3:
    url = sys.argv[1]
    out = sys.argv[2]
elif len(sys.argv) == 4:
    url = sys.argv[1]
    dir = sys.argv[2]
    out = sys.argv[3]

else:
    print('%s [url [dir]] outfile' % sys.argv[0])
    sys.exit(-1)

download_mag(url, dir, out)