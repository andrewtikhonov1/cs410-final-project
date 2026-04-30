1. Install Dependencies
pip install psycopg2-binary elasticsearch==8.13.0 datasets tqdm

2. Launch Infrastructure
docker-compose up -d

3. Initialize & Ingest
python setup_database.py
python postgres_ingest.py
python es_sync.py

4. Verify Counts/Success
Postgres count:
docker-compose exec postgres psql -U user -d wikidb -c "SELECT COUNT(*) FROM articles;"

Elasticsearch count:
curl -X GET "localhost:9200/_cat/indices/wikipedia_articles?v&h=docs.count"

---

Checking size:
docker-compose exec postgres psql -U user -d wikidb -c "SELECT pg_size_pretty(pg_database_size('wikidb'));"
curl -X GET "localhost:9200/_cat/indices/wikipedia_articles?v&h=dataset.size"