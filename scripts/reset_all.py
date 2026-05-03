import psycopg2
from elasticsearch import Elasticsearch

# Do not run unless trying to rest both the main store and the Elasticsearch index
def reset_all():
    # Reset PostgreSQL
    print("Connecting to PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(
            dbname="wikidb", 
            user="user", 
            password="password", 
            host="127.0.0.1", 
            port="5433"
        )
        pg_conn.autocommit = True
        pg_cursor = pg_conn.cursor()

        print("Clearing PostgreSQL 'articles' table...")
        pg_cursor.execute("DROP TABLE IF EXISTS articles CASCADE;")
        pg_cursor.execute("""
            CREATE TABLE articles (
                article_id SERIAL PRIMARY KEY,
                title TEXT UNIQUE NOT NULL,
                raw_content TEXT NOT NULL,
                url TEXT
            );
        """)
        print("PostgreSQL reset and schema recreated.")
        pg_cursor.close()
        pg_conn.close()
    except Exception as e:
        print(f"PostgreSQL Reset Failed: {e}")

    # Reset Elasticsearch
    print("\nConnecting to Elasticsearch...")
    try:
        es = Elasticsearch("http://localhost:9200", timeout=60)

        print("Nuking Elasticsearch index 'wikipedia_articles'...")
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
        print("Elasticsearch reset and index recreated.")
    except Exception as e:
        print(f"Elasticsearch Reset Failed: {e}")

    print("\nAll systems zeroed out and ready for ingestion.")

if __name__ == "__main__":
    reset_all()