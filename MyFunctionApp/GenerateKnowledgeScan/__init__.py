import logging
import os
import uuid
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.cosmos import CosmosClient
from collections import defaultdict
from common import summary
import json

def generate_knowledge_scan(query, doc_ids):
    search_endpoint = os.getenv('SEARCH_SERVICE_ENDPOINT')
    search_key = os.getenv('SEARCH_SERVICE_ADMIN_KEY')
    index_name = os.getenv('SEARCH_INDEX_NAME')
    cosmos_db_connection_string = os.getenv('COSMOS_DB_CONNECTION_STRING')
    cosmos_db_name = os.getenv('COSMOS_DB_DATABASE_NAME')
    cosmos_container_name = os.getenv('COSMOS_DB_CONTAINER_NAME')
    aoai_url = os.getenv('AOAI_URL')
    aoai_key = os.getenv('AOAI_KEY')
    model = os.getenv('MODEL')
    aoai_version_completion = os.getenv('AOAI_VERSION_COMPLETION')

    if not all([search_endpoint, search_key, index_name, cosmos_db_connection_string, cosmos_db_name, cosmos_container_name, aoai_url, aoai_key, model, aoai_version_completion]):
        raise ValueError("One or more required environment variables are missing.")

    # Initialize Search Client
    search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=AzureKeyCredential(search_key))

    # Initialize Cosmos Client using the connection string
    cosmos_client = CosmosClient.from_connection_string(cosmos_db_connection_string)
    database = cosmos_client.get_database_client(cosmos_db_name)
    container = database.get_container_client(cosmos_container_name)

    # Grouping documents by their source PDF (using the `file_name` field)
    doc_groups = defaultdict(list)

    for doc_id in doc_ids:
        result = search_client.get_document(key=doc_id)
        pdf_name = result['file_name'].split('_chunk_')[0]  # Extracting the base file name without chunk details
        doc_groups[pdf_name].append(result)

    combined_summaries = []
    full_content_texts = []
    keywords = set()
    resources_searched = set()
    references = []

    for i, (pdf_name, docs) in enumerate(doc_groups.items(), 1):
        # Combine summaries and content texts for each PDF
        pdf_summaries = [doc['summary'] for doc in docs]
        pdf_content_texts = [doc['content_text'] for doc in docs]

        # Combine summaries using OpenAI for each group of chunks from the same PDF
        combined_summary_prompt = "Can you please summarize these documents based on the user query: '{}'?".format(query) + " ".join(pdf_summaries)
        combined_summary = summary.generate_prompt(combined_summary_prompt, "You are an AI assistant that summarizes texts.", aoai_key, aoai_url, model, aoai_version_completion)

        combined_summaries.append({
            "pdf_name": pdf_name,
            "summary": combined_summary
        })

        # Add reference for superscript
        references.append(f"{pdf_name} ({i})")

        full_content_texts.extend(pdf_content_texts)

        # Extracting keywords and resources (assuming they exist in the metadata)
        for doc in docs:
            if 'keywords' in doc:
                keywords.update(doc['keywords'])
            if 'resource' in doc:
                resources_searched.add(doc['resource'])

    # Generate overall summary by concatenating summaries
    overall_summary_prompt = "Can you generate an overall summary based on the following document summaries, adding a superscript reference number for each document when applicable?\n\n"
    for i, summary_info in enumerate(combined_summaries, 1):
        overall_summary_prompt += f"{summary_info['summary']} [{i}]\n"

    # Get overall summary from GPT
    overall_summary = summary.generate_prompt(
        overall_summary_prompt,
        "You are an AI assistant that generates overall summaries.",
        aoai_key,
        aoai_url,
        model,
        aoai_version_completion
    )

    # Build the final knowledge scan response
    knowledge_scan = {
        "id": str(uuid.uuid4()),  # Generate a unique ID for each knowledge scan
        "query": query,
        "combined_summaries": combined_summaries,
        "overall_summary": overall_summary,
        "references": references,  # References for superscripts
        "content_texts": full_content_texts,
        "doc_ids": doc_ids,
        "general_notes": f"Generated based on query: {query}. This scan covers documents from various sources and provides a summarized overview.",
        "keywords": list(keywords),
        "resources_searched": list(resources_searched)
    }

    try:
        response = container.create_item(body=knowledge_scan)
        logging.info(f"Knowledge scan saved to Cosmos DB. Response: {response}")
    except Exception as e:
        logging.error(f"Error saving knowledge scan to Cosmos DB: {e}")
        raise

    return knowledge_scan

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()

        query = data.get("query")
        doc_ids = data.get("documents")

        if not query or not doc_ids:
            return func.HttpResponse(
                "Please pass both 'query' and 'documents' in the request body.",
                status_code=400
            )

        knowledge_scan = generate_knowledge_scan(query, doc_ids)
        knowledge_scan_json = json.dumps(knowledge_scan, ensure_ascii=False)

        # Return a successful response
        return func.HttpResponse(
            knowledge_scan_json,
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in GenerateKnowledgeScan function: {e}")
        return func.HttpResponse(f"Error: {e}", status_code=500)
