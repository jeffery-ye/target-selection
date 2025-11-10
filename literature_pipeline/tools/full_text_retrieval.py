import xml.etree.ElementTree as ET
import re
import requests
import time
from Bio import Entrez
import urllib.error
import logging

logger = logging.getLogger(__name__)
Entrez.email = "jeffery.ye@seattlechildrens.org"

# downloads pubmed central paper using Entrez
def retrieve_article(pmid, retries=3, delay=1):
    """
    Part of literature_ner_node

    This tool retrieves the full text of an article in xml form if it exists, None if it doesn't.
    """
    link_handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc_refs")
    link_result = Entrez.read(link_handle)
    link_handle.close()
    
    if not link_result[0]["LinkSetDb"]:
        logger.info(f"Error: No PMCID Found for {pmid}.")
        return
        
    pmcid = link_result[0]["LinkSetDb"][0]["Link"][0]["Id"]
    
    for attempt in range(retries):
        try:
            logger.info(f"Tool: Found PMCID {pmcid}. Fetching full text...")
            fetch_handle = Entrez.efetch(db="pmc", id=pmcid, rettype="xml", retmode="text")
            data = fetch_handle.read()
            fetch_handle.close()

            return parse_article(data)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                logger.error(f"HTTP 400 for {pmcid}, attempt {attempt+1}/{retries}")
                time.sleep(delay)
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error for {pmcid}: {e}")
            time.sleep(delay)
    logger.info(f"Failed to retrieve {pmcid} after {retries} attempts.")
    return ""

def parse_article(xml_article):
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

    if text_segments:
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
