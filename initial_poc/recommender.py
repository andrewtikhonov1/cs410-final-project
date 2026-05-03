import wikipedia
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# obtain article from Wikipedia
def fetch_wikipedia_data(titles):
    print("Fetching articles...")
    data = []
    for title in titles:
        try:
            full_text = wikipedia.page(title, auto_suggest=False).content
            data.append({"Title": title, "Text": full_text})
            print(f"Successfully fetched: {title}")
        except wikipedia.exceptions.DisambiguationError:
            print(f"Skipping {title}")
        except wikipedia.exceptions.PageError:
            print(f"Skipping {title}")
            
    return pd.DataFrame(data)

# returns the top n most similar articles given an article title
def get_recommendations(title, df, similarity_matrix, top_n=4):
    if title not in df['Title'].values:
        return f"'{title}' was not found."
        
    idx = df.index[df['Title'] == title][0]

    # get the pairwise similarity scores of all articles with that article and sort, returning the top n
    sim_scores = list(enumerate(similarity_matrix[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    top_articles_indices = [i[0] for i in sim_scores[1:top_n+1]]
    top_articles_scores = [i[1] for i in sim_scores[1:top_n+1]]

    recommendations = pd.DataFrame({
        'Recommended Article': df['Title'].iloc[top_articles_indices].values,
        'Similarity Score': top_articles_scores
    })
    
    return recommendations

# fetch the example test articles
sample_titles = [
    "Artificial intelligence", "Machine learning", "Deep learning", "Supercomputer",
    "Quantum mechanics", "General relativity", "Black hole",
    "Pizza", "Sushi", "Pasta", "Italy",
    "Dog", "Cat", "Lion", "Rabbit",
    "Illinois Fighting Illini men's basketball", "Indiana Hoosiers men's basketball", "Connecticut Huskies men's basketball", "Illinois Fighting Illini football"
]
df = fetch_wikipedia_data(sample_titles)

# remove stop words and create the TF-IDF matrix
tfidf = TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf.fit_transform(df['Text'])

# use cosine similarity as the relevance measure
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

# results
test_article = "Machine learning"
print(f"\nRecommendations for '{test_article}':")
print(get_recommendations(test_article, df, cosine_sim))

test_article_2 = "Pizza"
print(f"\nRecommendations for '{test_article_2}':")
print(get_recommendations(test_article_2, df, cosine_sim))

test_article_3 = "Illinois Fighting Illini men's basketball"
print(f"\nRecommendations for '{test_article_3}':")
print(get_recommendations(test_article_3, df, cosine_sim))