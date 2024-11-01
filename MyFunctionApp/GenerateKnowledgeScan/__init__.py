import logging
import os
import uuid
import json
import requests
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.cosmos import CosmosClient
from collections import defaultdict
from common import summary

def generate_knowledge_scan(query, doc_ids):
    try:
        # Fetch environment variables
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
        bibliography_url = os.getenv('BIBLIOGRAPHY_FUNCTION_URL')  # URL for Bibliography function

        # Validate environment variables
        if not all([search_endpoint, search_key, index_name, cosmos_db_connection_string, cosmos_db_name, cosmos_container_name, aoai_url, aoai_key, model, aoai_version_completion, bibliography_url]):
            logging.error("One or more required environment variables are missing.")
            raise ValueError("One or more required environment variables are missing.")

        # Initialize clients
        logging.info("Initializing Search and Cosmos clients.")
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=AzureKeyCredential(search_key))
        cosmos_client = CosmosClient.from_connection_string(cosmos_db_connection_string)
        database = cosmos_client.get_database_client(cosmos_db_name)
        container = database.get_container_client(cosmos_container_name)

        # Call the Bibliography function via HTTP to get the bibliographies
        logging.info("Calling Bibliography function via HTTP.")
        bibliography_response = requests.post(bibliography_url, json={"documents": doc_ids})
        
        if bibliography_response.status_code != 200:
            logging.error(f"Failed to get bibliographies. Status Code: {bibliography_response.status_code}")
            raise ValueError("Failed to retrieve bibliographies.")
        
        # Ensure bibliographies is a list of strings
        bibliographies = bibliography_response.json().get("bibliographies", [])
        logging.info(f"Received Bibliographies: {bibliographies}")

        # Group documents by their source PDF (using file_name field)
        doc_groups = defaultdict(list)
        for doc_id in doc_ids:
            result = search_client.get_document(key=doc_id)
            pdf_name = result['file_name'].split('_chunk_')[0]
            doc_groups[pdf_name].append(result)

        combined_summaries = []
        for i, (pdf_name, docs) in enumerate(doc_groups.items()):
            # Combine summaries for each PDF
            pdf_summaries = [doc['summary'] for doc in docs]
            combined_summary_prompt = f"Can you summarize these documents based on the user query: '{query}'? " + " ".join(pdf_summaries)
            combined_summary = summary.generate_prompt(combined_summary_prompt, "You are an AI assistant that summarizes texts.", aoai_key, aoai_url, model, aoai_version_completion)

            # Retrieve the correct bibliography for each main PDF, ensuring it's treated as a string
            bibliography_entry = str(bibliographies[i]) if i < len(bibliographies) else "No bibliography available"

            # Add combined summary with bibliography
            combined_summaries.append({
                "pdf_name": pdf_name,
                "summary": combined_summary,
                "bibliography": bibliography_entry
            })

        overall_summary_prompt = "Can you generate an overall summary based on the following document summaries, adding a superscript reference number for each document when applicable?\n\n"
        for i, summary_info in enumerate(combined_summaries, 1):
            overall_summary_prompt += f"{summary_info['summary']} [{i}]\n"

        overall_summary = summary.generate_prompt(overall_summary_prompt, "You are an AI assistant that generates overall summaries.", aoai_key, aoai_url, model, aoai_version_completion)

        # Build the final knowledge scan response
        knowledge_scan = {
            "id": str(uuid.uuid4()),
            "query": query,
            "combined_summaries": combined_summaries,
            "overall_summary": overall_summary,
            "general_notes": f"Generated based on query: {query}. This scan covers documents from various sources and provides a summarized overview."
        }

        # Save the knowledge scan to Cosmos DB
        try:
            response = container.create_item(body=knowledge_scan)
            logging.info(f"Knowledge scan saved to Cosmos DB. Response: {response}")
        except Exception as e:
            logging.error(f"Error saving knowledge scan to Cosmos DB: {e}")
            raise

        return knowledge_scan

    except Exception as e:
        logging.error(f"Error in generate_knowledge_scan: {e}")
        raise

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

        return func.HttpResponse(
            knowledge_scan_json,
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in GenerateKnowledgeScan function: {e}")
        return func.HttpResponse(f"Error: {e}", status_code=500)