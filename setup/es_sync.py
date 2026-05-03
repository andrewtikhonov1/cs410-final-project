import psycopg2
from psycopg2.extras import DictCursor
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm

BATCH_SIZE = 400

def sync_pg_to_index():
    print("Connecting to databases...")
    pg_conn = psycopg2.connect(dbname="wikidb", user="user", password="password", host="127.0.0.1", port="5433")
    es = Elasticsearch("http://localhost:9200", timeout=60)

    # Reset Elasticsearch
    print("Recreating Elasticsearch Index...")
    es.options(ignore_status=[400, 404]).indices.delete(index="wikipedia_articles")
    es.indices.create(index="wikipedia_articles", mappings={
        "properties": {
            "title": {"type": "text", "store": True},
            "content": {
                "type": "text", 
                "index": True,
                "store": False,
                "term_vector": "yes"
            }
        },
        "_source": {
            "excludes": ["content"]
        }
    })

    # Stream from Postgres to ES using a named (server-side) cursor
    pg_cur = pg_conn.cursor(name="es_sync_cursor", cursor_factory=DictCursor)
    pg_cur.execute("SELECT article_id, title, raw_content FROM articles;")

    print("Syncing records...")
    with tqdm(desc="Vault -> Index", unit="art") as pbar:
        while True:
            rows = pg_cur.fetchmany(BATCH_SIZE)
            if not rows:
                break
            
            actions = [{
                "_index": "wikipedia_articles",
                "_id": row['article_id'],
                "_source": {
                    "title": row['title'],
                    "content": row['raw_content']
                }
            } for row in rows]
            
            helpers.bulk(es, actions)
            pbar.update(len(actions))

    pg_cur.close()
    pg_conn.close()
    print("\nElasticsearch Index is in sync with main store.")

if __name__ == "__main__":
    sync_pg_to_index()