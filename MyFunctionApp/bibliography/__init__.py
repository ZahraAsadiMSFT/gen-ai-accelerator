import logging
import os
import json
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from collections import defaultdict
from common import summary  # Assuming summary.generate_prompt is defined in common

def fetch_first_chunk(search_client, base_pdf_name):
    try:
        first_chunk_filter = f"file_name eq '{base_pdf_name}_chunk_1_pages_1_to_10.pdf'"
        results = search_client.search(search_text="", filter=first_chunk_filter)

        for result in results:
            logging.info(f"Content of first chunk for base PDF: {base_pdf_name}")
            return result['content_text']

        logging.warning(f"No first chunk found for base PDF: {base_pdf_name}")
        return ""

    except Exception as e:
        logging.error(f"Error in fetch_first_chunk: {e}")
        return ""

def extract_bibliography_from_chunk(content_text, aoai_key, aoai_url, model, aoai_version_completion):
    bibliography_prompt = (
        "Extract the title, authors, and publication date from the following document content. "
        "Return the result in the format: 'Authors (Year). Title. Institution/Publisher.'. "
        "If any information is missing, leave those fields blank but keep the format. "
        "Content:\n\n"
        f"{content_text[:1000]}"
    )

    try:
        bibliography_response = summary.generate_prompt(
            bibliography_prompt,
            "You are an AI assistant that extracts title, authors, and publication date in a structured bibliography format.",
            aoai_key,
            aoai_url,
            model,
            aoai_version_completion
        )

        # Extracting details from response
        title = ""
        authors = []
        publication_date = ""
        institution = ""

        if "(" in bibliography_response and ")" in bibliography_response:
            authors_section = bibliography_response.split("(", 1)[0].strip()
            authors = [author.strip() for author in authors_section.split(",")]
            publication_date = bibliography_response.split("(", 1)[1].split(")", 1)[0].strip()
            remainder = bibliography_response.split(")", 1)[1].strip().split(". ")
            if len(remainder) >= 2:
                title = remainder[0].strip()
                institution = remainder[1].strip()
            elif len(remainder) == 1:
                title = remainder[0].strip()

        return {
            "title": title,
            "authors": authors,
            "publication_date": publication_date,
            "institution": institution
        }

    except Exception as e:
        logging.error(f"Error parsing GPT response: {e}")
        return {
            "title": "",
            "authors": [],
            "publication_date": "",
            "institution": ""
        }

def format_bibliography_entry(bibliography):
    authors = ", ".join(bibliography.get("authors", []))
    title = bibliography.get("title", "").strip()
    publication_date = bibliography.get("publication_date", "").strip()
    institution = bibliography.get("institution", "").strip()

    # Construct the bibliography entry only with available fields
    formatted_entry_parts = []

    if authors:
        formatted_entry_parts.append(authors)
    if publication_date:
        formatted_entry_parts.append(f"({publication_date})")
    if title:
        formatted_entry_parts.append(title)
    if institution:
        formatted_entry_parts.append(institution)

    # Join all parts with a period and space
    formatted_entry = ". ".join(formatted_entry_parts) + "."
    return formatted_entry


def generate_bibliographies(doc_ids):
    search_endpoint = os.getenv('SEARCH_SERVICE_ENDPOINT')
    search_key = os.getenv('SEARCH_SERVICE_ADMIN_KEY')
    index_name = os.getenv('SEARCH_INDEX_NAME')
    aoai_url = os.getenv('AOAI_URL')
    aoai_key = os.getenv('AOAI_KEY')
    model = os.getenv('MODEL')
    aoai_version_completion = os.getenv('AOAI_VERSION_COMPLETION')

    search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=AzureKeyCredential(search_key))

    # Group doc_ids by their main PDF name
    doc_groups = defaultdict(list)
    for doc_id in doc_ids:
        result = search_client.get_document(key=doc_id)
        pdf_name = result['file_name'].split('_chunk_')[0]
        doc_groups[pdf_name].append(doc_id)

    bibliographies = []
    for pdf_name in doc_groups.keys():
        # Fetch the first chunk content for each main PDF
        first_chunk_content = fetch_first_chunk(search_client, pdf_name)

        if not first_chunk_content:
            logging.info(f"No first chunk found for base PDF: {pdf_name}")
            bibliographies.append("No bibliography available")
            continue

        bibliography_entry = extract_bibliography_from_chunk(first_chunk_content, aoai_key, aoai_url, model, aoai_version_completion)
        formatted_entry = format_bibliography_entry(bibliography_entry)
        bibliographies.append(formatted_entry)

    return {"bibliographies": bibliographies}

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        doc_ids = data.get("documents")

        if not doc_ids:
            return func.HttpResponse(
                "Please provide a list of 'documents' in the request body.",
                status_code=400
            )

        result = generate_bibliographies(doc_ids)
        result_json = json.dumps(result, ensure_ascii=False)

        return func.HttpResponse(
            result_json,
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in bibliography generation function: {e}")
        return func.HttpResponse(f"Error: {e}", status_code=500)