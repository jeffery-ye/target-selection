import xml.etree.ElementTree as ET
import re
import requests
import time
from Bio import Entrez
import urllib.error

# downloads pubmed central paper using Entrez
def entrez_retrieval(self, pmc_id, retries=3, delay=1):
    for attempt in range(retries):
        try:
            handle = Entrez.efetch(db="pmc", id=pmc_id, retmode="xml")
            data = handle.read().decode('utf-8')
            return data
        except urllib.error.HTTPError as e:
            if e.code == 400:
                print(f"HTTP 400 for {pmc_id}, attempt {attempt+1}/{retries}")
                time.sleep(delay)
            else:
                raise
        except Exception as e:
            print(f"Unexpected error for {pmc_id}: {e}")
            time.sleep(delay)
    print(f"Failed to retrieve {pmc_id} after {retries} attempts.")
    return ""

def parse_article(self, xml_article):
    tree = ET.ElementTree(ET.fromstring(xml_article))
    root = tree.getroot()

    pmcid_element = root.find(".//article-id[@pub-id-type='pmcid']")
    pmcid = pmcid_element.text if pmcid_element is not None else 'Not Found'

    title_element = root.find('.//article-title') # Traverse to <article-title>
    if title_element is not None:
        # Title cleanup
        article_title = "".join(title_element.itertext()).strip() 
        article_title = re.sub(r'\s+', ' ', article_title).strip()

    # Extract abstract
    abstract_text = 'N/A'
    abstract = root.find('.//abstract')

    if abstract is not None:
        for element in abstract:
            if element.tag == 'p': 
                p_text = "".join(element.itertext()).strip()
                p_text = re.sub(r'\s+', ' ', p_text).strip()
                if p_text:
                    abstract_text = p_text

    # Extract body text
    text_segments = []
    body = root.find('.//body')

    if body is not None:
        for element in body:
            if element.tag == 'sec':
                sec_title_text = None
                title_tag = element.find('./title')
                if title_tag is not None:
                    raw_title = "".join(title_tag.itertext()).strip()
                    cleaned_title = re.sub(r'\s+', ' ', raw_title).strip()
                    if cleaned_title:
                            sec_title_text = cleaned_title

                if sec_title_text:
                    text_segments.append(f"## {sec_title_text} ##")

                for p_tag in element.findall('.//p'):
                    p_text = "".join(p_tag.itertext()).strip()
                    p_text = re.sub(r'\s+', ' ', p_text).strip()
                    if p_text:
                        text_segments.append(p_text)

            elif element.tag == 'p': 
                p_text = "".join(element.itertext()).strip()
                p_text = re.sub(r'\s+', ' ', p_text).strip()
                if p_text:
                    text_segments.append(p_text)

    if text_segments[0]:
        full_text = "\n".join(segment for segment in text_segments if segment)
    else:
        full_text = 'N/A'
        
    # Find Materials and methods
    pattern = r"##\s*(.*?)\s*##(.*?)(?=(?:##|$))"
    methods = None
    
    for match in re.finditer(pattern, full_text, re.DOTALL):
        title = match.group(1).strip()
        if "method".lower() in title.lower():
            methods = (match.group(2).strip())

    return {
        'pmcid': pmcid,
        'title': article_title,
        'abstract': abstract_text,
        'full_text': full_text,
        'methods': methods
    }
