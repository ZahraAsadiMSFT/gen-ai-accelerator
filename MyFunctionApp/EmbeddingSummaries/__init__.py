import logging
import os
import fitz  # PyMuPDF
import uuid
from azure.functions import InputStream
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient
from common import embedding, summary

def generate_embeddings_and_summaries(blob_content, blob_name):
    search_endpoint = os.getenv('SEARCH_SERVICE_ENDPOINT')
    search_key = os.getenv('SEARCH_SERVICE_ADMIN_KEY')
    index_name = os.getenv('SEARCH_INDEX_NAME')
    aoai_url = os.getenv('AOAI_URL')
    aoai_key = os.getenv('AOAI_KEY')
    embedding_model = os.getenv('EMBEDDING_MODEL')
    aoai_version_embedding = os.getenv('AOAI_VERSION_EMBEDDING')
    aoai_version_completion = os.getenv('AOAI_VERSION_COMPLETION')
    model = os.getenv('MODEL')

    if not all([search_endpoint, search_key, index_name, aoai_url, aoai_key, embedding_model, aoai_version_embedding, aoai_version_completion, model]):
        raise ValueError("One or more required environment variables are missing.")

    search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=AzureKeyCredential(search_key))

    try:
        logging.info(f"Processing blob: {blob_name}")

        data = ""
        pdf_document = fitz.open(stream=blob_content, filetype="pdf")
        for page in pdf_document:
            data += page.get_text()

        parts = blob_name.split('_')
        chunk_number = parts[1]
        page_range = parts[3].split('.')[0]
        file_name_chunk = f"{chunk_number}_{page_range}"

        embedding_vec = embedding.get_new_embedding(data, aoai_url, aoai_key, embedding_model, aoai_version_embedding)

        with open('common/summary-prompt.txt', 'r') as file:
            prompt_template = file.read()

        prompt = prompt_template + data
        summary_str = summary.generate_prompt(prompt, "You are an AI assistant that produces comprehensive, structured summaries of academic or informational texts. Your summaries should provide clear background context, methodological details, main findings, and conclusions, similar to a scholarly abstract.", aoai_key, aoai_url, model, aoai_version_completion)

        document = {
            "id": str(uuid.uuid4()),  # Generate a unique ID for each document
            "file_name": blob_name,
            "file_name_chunk": file_name_chunk,
            "content_text": data,
            "summary": summary_str,
            "vector": embedding_vec['data'][0]['embedding']
        }

        result = search_client.upload_documents(documents=[document])
        logging.info(f"Uploaded document {blob_name} to the search index with result: {result}")
        for res in result:
            logging.info(f"Indexing result: {res}")

    except Exception as e:
        logging.error(f"Error processing blob {blob_name}: {e}")

def main(myblob: InputStream):
    try:
        generate_embeddings_and_summaries(myblob.read(), myblob.name)
    except Exception as e:
        logging.error(f"Error in main function: {e}")
        raise


