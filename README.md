## Project Setup & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch Infrastructure
```bash
docker-compose up -d
```

### 3. Initialize & Ingest
```bash
python setup/postgres_ingest.py
python setup/es_sync.py
```

### 4. Verify Counts/Success

#### Postgres count:
```bash
docker-compose exec postgres psql -U user -d wikidb -c "SELECT COUNT(*) FROM articles;"
```

#### Elasticsearch count:
```bash
curl -X GET "localhost:9200/_cat/indices/wikipedia_articles?v&h=docs.count"
```

---

**Storage Monitoring (Optional)**

#### Postgres Database Size:
```bash
docker-compose exec postgres psql -U user -d wikidb -c "SELECT pg_size_pretty(pg_database_size('wikidb'));"
```

#### Elasticsearch Index Size:
```bash
curl -X GET "localhost:9200/_cat/indices/wikipedia_articles?v&h=dataset.size"
```

## Running the Frontend

### 5. Start the Flask API
```bash
python app/app.py
```

### 6. Open the Frontend
Mac
```bash
open app/index.html
```

Windows
```bash
start app/index.html
```

Linux
```bash
xdg-open app/index.html
```

The status dot in the top-right corner of the app turns green when Flask can reach both databases. You can now search articles and view recommendations.

## Stopping & Resuming
To stop:
```CTRL+C``` in the terminal running app.py, then ```docker-compose down```.

To resume after a restart (data is already ingested, no need to re-run steps 3–4):

```bash
docker-compose up -d
python app/app.py
```

Then open the frontend (step 6).