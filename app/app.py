from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras
from elasticsearch import Elasticsearch
import os
import requests
import re
 
app = Flask(__name__)
CORS(app)
 
# ── Config ─────────────────────────────────────────────────────────────────────
PG_DSN = os.getenv(
    "PG_DSN",
    "host=127.0.0.1 port=5433 dbname=wikidb user=user password=password"
)
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_INDEX = "wikipedia_articles"
 
# ── Helpers ────────────────────────────────────────────────────────────────────
 
def get_pg():
    return psycopg2.connect(PG_DSN, cursor_factory=psycopg2.extras.RealDictCursor)
 
def get_es():
    return Elasticsearch(ES_HOST, request_timeout=30)
 
# ── Routes ─────────────────────────────────────────────────────────────────────
 
@app.route("/api/search")
def search():
    """
    Full-text BM25 search via Elasticsearch.
    ES _source excludes 'content', so only 'title' comes back from ES.
    article_id is the document _id.
    """
    q = request.args.get("q", "").strip()
    size = int(request.args.get("size", 10))
    if not q:
        return jsonify({"error": "q is required"}), 400
 
    es = get_es()
    resp = es.search(
        index=ES_INDEX,
        size=size,
        query={
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": q,
                            "fields": ["title^3", "content"],
                            "type": "best_fields"
                        }
                    },
                    {
                        "match_phrase": {
                            "title": {
                                "query": q,
                                "boost": 5
                            }
                        }
                    },
                    {
                        "term": {
                            "title.keyword": {
                                "value": q,
                                "boost": 10
                            }
                        }
                    }
                ]
            }
        },
        _source=True,
    )
 
    hits = [
        {
            "id": int(h["_id"]),
            "title": h["_source"].get("title", ""),
            "score": round(h["_score"], 4),
        }
        for h in resp["hits"]["hits"]
    ]
    return jsonify({"results": hits, "total": resp["hits"]["total"]["value"]})

@app.route("/api/article/<int:article_id>")
def get_article(article_id):
    """Fetch full article from Wikipedia using article_id with Postgres store as a fallback."""
    es = get_es()
    
    # Retrieve title from Elasticsearch
    try:
        es_resp = es.get(index=ES_INDEX, id=str(article_id))
        title = es_resp["_source"].get("title")
    except Exception:
        return jsonify({"error": "Article ID not found"}), 404

    # Try to fetch the prettified content using Wikipedia API
    wiki_action_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": title,
        "format": "json",
        "prop": "text|categories",
        "redirects": "1",
        "disableeditsection": "1"
    }
    
    headers = {
        'User-Agent': 'WikiRecDiscoveryApp/1.0 (https://github.com/andrewtikhonov1/cs410-final-project)'
    }

    use_fallback = False
    html_content = ""
    source = "wikipedia_parse_api"

    try:
        resp = requests.get(wiki_action_url, params=params, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if "error" not in data:
                # Disambiguation edge case check
                categories = data.get("parse", {}).get("categories", [])
                is_disambig = any("disambiguation" in c.get("*", "").lower() for c in categories)

                if is_disambig:
                    use_fallback = True
                else:
                    html_content = data.get("parse", {}).get("text", {}).get("*", "No content found.")
            else:
                use_fallback = True
        else:
            use_fallback = True
            
    except (requests.RequestException, ValueError):
        use_fallback = True

    # PostgreSQL Fallback
    if use_fallback:
        source = "local_db_fallback"
        try:
            conn = get_pg()
            cur = conn.cursor()
            cur.execute(
                "SELECT raw_content FROM articles WHERE article_id = %s",
                (article_id,)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()

            if row and row["raw_content"]:
                html_content = f"<div class='fallback-content'>{row['raw_content']}</div>"
            else:
                html_content = "<p>Error: Article content could not be retrieved.</p>"
        except Exception as e:
            html_content = f"<p>Local Retrieval Error: {str(e)}</p>"

    # # Remove images and figure tags
    if html_content and source == "wikipedia_parse_api":
        html_content = re.sub(r'<img\b[^>]*>', '', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'<figure\b[^>]*>.*?</figure>', '', html_content, flags=re.IGNORECASE | re.DOTALL)

    return jsonify({
        "id": article_id,
        "title": title,
        "html": html_content,
        "source": source
    })
 
 
@app.route("/api/recommend/<int:article_id>")
def recommend(article_id):
    """
    Find similar articles using Elasticsearch More-Like-This on 'content'.
    Falls back to title-based match if MLT fails.
    """
    size = int(request.args.get("size", 6))
 
    conn = get_pg()
    cur = conn.cursor()
    cur.execute("SELECT title FROM articles WHERE article_id = %s", (article_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
 
    if not row:
        return jsonify({"error": "article not found"}), 404
 
    source_title = row["title"]
    es = get_es()
 
    try:
        resp = es.search(
            index=ES_INDEX,
            size=size + 1,
            query={
                "more_like_this": {
                    "fields": ["title", "content"],
                    "like": [{"_index": ES_INDEX, "_id": str(article_id)}],
                    "min_term_freq": 1,
                    "max_query_terms": 25,
                    "min_doc_freq": 1,
                }
            },
            _source=True,
        )
    except Exception:
        # Fallback: BM25 on title words
        resp = es.search(
            index=ES_INDEX,
            size=size + 1,
            query={"match": {"title": source_title}},
            _source=True,
        )
 
    recs = [
        {
            "id": int(h["_id"]),
            "title": h["_source"].get("title", ""),
            "score": round(h["_score"], 4),
        }
        for h in resp["hits"]["hits"]
        if int(h["_id"]) != article_id
    ][:size]
 
    return jsonify({
        "article_id": article_id,
        "source_title": source_title,
        "recommendations": recs,
    })
 
 
@app.route("/api/random")
def random_article():
    """Return a random article_id + title from Postgres."""
    conn = get_pg()
    cur = conn.cursor()
    cur.execute("SELECT article_id, title FROM articles ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify({"error": "no articles in database"}), 404
    return jsonify({"id": row["article_id"], "title": row["title"]})
 
 
@app.route("/api/health")
def health():
    """Status check for database connections."""
    checks = {}
 
    try:
        conn = get_pg()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM articles")
        cnt = cur.fetchone()["cnt"]
        cur.close()
        conn.close()
        checks["postgres"] = f"ok ({cnt} articles)"
    except Exception as e:
        checks["postgres"] = f"error: {e}"
 
    try:
        es = get_es()
        if es.ping():
            info = es.cat.count(index=ES_INDEX, format="json")
            doc_count = info[0]["count"] if info else "?"
            checks["elasticsearch"] = f"ok ({doc_count} docs)"
        else:
            checks["elasticsearch"] = "unreachable"
    except Exception as e:
        checks["elasticsearch"] = f"error: {e}"
 
    ok = all(v.startswith("ok") for v in checks.values())
    return jsonify(checks), 200 if ok else 503
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)