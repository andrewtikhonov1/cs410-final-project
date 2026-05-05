import psycopg2
from psycopg2.extras import DictCursor
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm

# Push 400 articles at a time from Postgres to ES
BATCH_SIZE = 400

def sync_pg_to_index():
    print("Connecting to databases...")
    pg_conn = psycopg2.connect(dbname="wikidb", user="user", password="password", host="127.0.0.1", port="5433")
    es = Elasticsearch("http://localhost:9200", timeout=60)

    # Reset Elasticsearch client if it exists
    print("Recreating Elasticsearch index...")
    es.options(ignore_status=[400, 404]).indices.delete(index="wikipedia_articles")

    # Initialize the storage options, making it searchable but excluding the full raw content for size
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

    # Stream from Postgres to ES with a named cursor
    pg_cur = pg_conn.cursor(name="es_sync_cursor", cursor_factory=DictCursor)
    pg_cur.execute("SELECT article_id, title, raw_content FROM articles;")
    print("Syncing records...")
    with tqdm(desc="Postgres -> ES", unit="articles") as pbar:
        while True:
            # Get the entire batch
            rows = pg_cur.fetchmany(BATCH_SIZE)
            if not rows:
                break
            
            # Format the Postgres rows into Elasticsearch bulk actions and execute
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