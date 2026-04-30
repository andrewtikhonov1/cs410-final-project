import psycopg2
from elasticsearch import Elasticsearch
import json

# Suggests an article based on a query and then recommends similar articles. To be expanded.
def test_pipeline(query_text="programming language"):
    print(f"--- Testing Pipeline for: '{query_text}' ---")
    
    es = Elasticsearch("http://localhost:9200")
    pg_conn = psycopg2.connect(dbname="wikidb", user="user", password="password", host="127.0.0.1", port="5433")
    pg_cur = pg_conn.cursor()

    # Search Elasticsearch
    print("\n1. Searching Elasticsearch Index...")
    search_query = {
        "query": {
            "match": {
                "content": query_text
            }
        }
    }
    res = es.search(index="wikipedia_articles", body=search_query, size=3)
    
    hits = res['hits']['hits']
    if not hits:
        print("No results found in Elasticsearch.")
        return

    top_id = hits[0]['_id']
    top_title = hits[0]['_source']['title']
    print(f"Found top match: ID {top_id} - '{top_title}'")

    # Fetch full text from Postgres
    print("\n2. Fetching Full Text from Postgres Vault...")
    pg_cur.execute("SELECT raw_content FROM articles WHERE article_id = %s;", (top_id,))
    content = pg_cur.fetchone()
    
    if content:
        print(f"Successfully retrieved {len(content[0])} characters from Postgres.")
        print(f"Snippet: {content[0][:100]}...")
    else:
        print("ID found in ES but missing in Postgres! Sync is broken.")

    # Test similarity
    print(f"\n3. Finding articles similar to '{top_title}'...")
    mlt_query = {
        "query": {
            "more_like_this": {
                "fields": ["content", "title"],
                "like": [{"_index": "wikipedia_articles", "_id": top_id}],
                "min_term_freq": 1,
                "max_query_terms": 10
            }
        }
    }
    sim_res = es.search(index="wikipedia_articles", body=mlt_query, size=3)
    sim_hits = sim_res['hits']['hits']
    
    if sim_hits:
        print("Similar articles found:")
        for s_hit in sim_hits:
            print(f"   - {s_hit['_source']['title']} (Score: {s_hit['_score']:.2f})")
    else:
        print("No similar articles found. Check if 'term_vector' is enabled.")

    pg_cur.close()
    pg_conn.close()

if __name__ == "__main__":
    test_pipeline("Michigan Wolverines")