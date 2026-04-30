import psycopg2

def setup_postgres():
    # connect to the Postgres database running in Docker
    conn = psycopg2.connect(dbname="wikidb", user="user", password="password", host="127.0.0.1", port="5433")
    
    # Automatically commit the transaction
    conn.autocommit = True 
    cursor = conn.cursor()

    # The SQL command from Step 2
    create_table_query = """
    CREATE TABLE IF NOT EXISTS articles (
        article_id SERIAL PRIMARY KEY,
        title VARCHAR(255) UNIQUE NOT NULL,
        raw_content TEXT NOT NULL,
        url VARCHAR(512)
    );
    """
    
    cursor.execute(create_table_query)
    print("Table 'articles' created successfully in PostgreSQL!")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    setup_postgres()