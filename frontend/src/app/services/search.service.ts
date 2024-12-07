import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";
import { switchMap, map } from "rxjs/operators";

interface Document {
  id: string;
  publishedDate: string;
  fileName: string;
  summary: string;
  relevance: string;
  selected?: boolean;
}

@Injectable({
  providedIn: "root",
})
export class SearchService {
  constructor(private http: HttpClient) {}

  mapScoreToRelevance(score: number): string {
    if (score > 0.03) {
      return 'Great';
    } else if (score >= 0.02 && score <= 0.03) {
      return 'Good';
    } else {
      return 'Fair';
    }
  }

  // SearchDocument API
  searchDocument(query: string): Observable<Document[]> {
    // Prepare the embedding body
    const embeddingBody = {
      input: query,
    };

    // Call the server endpoint to get embedding
    return this.http
      .post<any>('/api/get-embedding', embeddingBody)
      .pipe(
        switchMap((embeddingResponse) => {
          const embeddingVector = embeddingResponse.data[0].embedding;

          // Prepare the search body
          const searchBody = {
            search: query,
            vectorQueries: [
              {
                kind: "vector",
                vector: embeddingVector,
                k: 5,
                fields: "vector",
              },
            ],
            select: "file_name,summary,id",
          };

          // Call the server endpoint to search documents
          return this.http.post<any>('/api/search-documents', searchBody);
        }),
        map((searchResponse) => {
          const documents: Document[] = searchResponse.value.map(
            (item: any) => ({
              id: item.id,
              publishedDate: "2022-03-11", // TODO: Update with actual date
              fileName: item.file_name,
              summary: item.summary,
              relevance: this.mapScoreToRelevance(item["@search.score"]),
              selected: false,
            })
          );
          return documents;
        })
      );
  }

  // GenerateSynthesis API
  generateSynthesis(requestBody: any): Observable<any> {
    console.log("API Request Body: ", requestBody);
    return this.http.post<any>('/api/generate-synthesis', requestBody);
  }
}
