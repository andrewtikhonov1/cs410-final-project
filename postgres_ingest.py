import psycopg2
from psycopg2.extras import execute_values
from datasets import load_dataset
from tqdm import tqdm

TARGET_ARTICLES = 400000
BATCH_SIZE = 500

def ingest_to_db():
    print("Connecting to PostgreSQL Vault...")
    conn = psycopg2.connect(dbname="wikidb", user="user", password="password", host="127.0.0.1", port="5433")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            article_id SERIAL PRIMARY KEY,
            title TEXT UNIQUE NOT NULL,
            raw_content TEXT NOT NULL,
            url TEXT
        );
    """)

    print(f"Streaming {TARGET_ARTICLES} articles from Hugging Face...")
    dataset = load_dataset("wikimedia/wikipedia", "20231101.en", split="train", streaming=True)
    dataset = dataset.shuffle(seed=42, buffer_size=20000)
    
    batch = []
    count = 0
    
    with tqdm(total=TARGET_ARTICLES, desc="Vault Ingestion", unit="art") as pbar:
        for article in dataset:
            if count >= TARGET_ARTICLES:
                break
            
            batch.append((article['title'], article['text'], article['url']))
            
            if len(batch) >= BATCH_SIZE:
                execute_values(cur, "INSERT INTO articles (title, raw_content, url) VALUES %s ON CONFLICT (title) DO NOTHING;", batch)
                count += len(batch)
                pbar.update(len(batch))
                batch = []

        if batch:
            execute_values(cur, "INSERT INTO articles (title, raw_content, url) VALUES %s ON CONFLICT (title) DO NOTHING;", batch)
            pbar.update(len(batch))

    cur.close()
    conn.close()
    print("\nMain store is fully loaded.")

if __name__ == "__main__":
    ingest_to_db()