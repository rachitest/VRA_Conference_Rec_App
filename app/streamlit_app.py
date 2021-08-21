import base64
import importlib
import nltk
import pandas as pd
import pickle
import streamlit as st

from io import StringIO
from pathlib import Path

from gensim.models.doc2vec import Doc2Vec
from sklearn.metrics.pairwise import cosine_similarity
from cleaners.data_cleaning import preprocessSentences
from recommenders.bm25_rec import getBM25Ranks, getRecs
from recommenders.doc2vec_rec import getDoc2VecScores, getDoc2VecRecs
from recommenders.tfidf_rec import createVectorizer, createTFIDFModel, processQuery, getTFIDFRecs

st.set_page_config("Conference Recommendations", page_icon = "📚", layout = "wide")
st.title("Conference Recommendations")
st.sidebar.title("Recommender Options")

current_fp = Path(__file__)
current_root = current_fp.parents[0]
app_root = current_fp.parents[1]
token_corpus_path = app_root / "assets/wikicfp_corpus.pkl"
raw_corpus_path = app_root / "assets/wikicfp_corpus_raw.csv"
bm25_model_path = app_root / "assets/models/bm25Modelv0.1.pkl"
d2v_model_path = app_root / "assets/models/d2vModelv0.1.pkl"

# download nltk resources
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")
try:
    nltk.data.find("taggers/averaged_perceptron_tagger")
except LookupError:
    nltk.download("averaged_perceptron_tagger")
try:
    nltk.data.find("corpora/wordnet")
except LookupError:
    nltk.download("wordnet")
try:
    nltk.data.find("corpora/stopwords")
except:
    nltk.download("stopwords")
finally:
    importlib.reload(nltk)

# define download function
def get_table_download_link(df):
    df = df.copy()
    df = df[["Conference Title", "Conference Webpage"]]
    df["User Rating"] = None
    val = df.to_csv(index=False)
    b64 = base64.b64encode(val.encode()).decode()  
    return f'<a href="data:file/csv;base64,{b64}"> Download File </a>'

#check if tokenized corpus exists in directory
with st.spinner("Setting up corpus, can take up to 5 minutes for the first run..."):
    if token_corpus_path.is_file():
        csv_cols = ["Conference Title", "Conference Webpage", "Conference Date", "Conference Location", "WikiCFP Tags", "WikiCFP Link", "Conference Description"]
        wikicfp_corpus = pd.read_csv(raw_corpus_path, usecols = csv_cols)
        wiki_token = pd.read_pickle(token_corpus_path)
    else:
        st.error("Oh no, the corpus does not exist. Aborting app.")
        st.stop()

with st.expander("Raw Corpus Preview"):
    st.write("The following is a 1000 row preview of the raw corpus:")
    st.dataframe(wikicfp_corpus.head(1000))

with st.expander("Tokenized Corpus Preview"):
    st.write("The following is a 1000 row preview of the tokenized corpus:")
    st.dataframe(wiki_token.head(1000))

# define batch element for choosing which type of recommender to use
with st.sidebar.form(key = "form_1"):
    rec_type = st.radio("Choose a recommender", ("BM25", "Doc2Vec", "TF-IDF"))
    query_type = st.radio("Choose query format", ("File", "Textbox"))
    number_of_recs = st.number_input("How many reccomendations would you like", 5, 50, value = 10, step = 5) 
    submit_button = st.form_submit_button(label = "Submit")

# create recommendations based on recommender algorithm and input type
if rec_type == "BM25":
    try:
        bm25_model = pickle.load(open(bm25_model_path, "rb"))
    except (OSError, IOError) as e:
        st.error("Model does not exist. Aborting app.")
        st.stop()
    if query_type == "File":
        query = st.sidebar.file_uploader("Choose your query", type = ["txt"], help = "Please select the file you want conference recommendations for (must be a txt file)")
        if query:
            stringio = StringIO(query.getvalue().decode("utf-8"))
            query_string = stringio.read()
        else: 
            st.write("Please enter the query you want conference recommendations for")
            st.stop()
        with st.spinner("Calculating your recommendations!"):
            query_scores = getBM25Ranks(preprocessSentences, query_string, bm25_model)
            recs = getRecs(query_scores, number_of_recs, wikicfp_corpus).reset_index()
            recs.index += 1
            st.write(f"Here are the top {number_of_recs} recommendations for your query 🎉:")
            st.table(recs[["Conference Title", "Conference Webpage"]])

            with st.sidebar.form(key = "subform_1"):
                dl = st.radio("Do you want to download your recommendations?", ("Yes", "No"), help = "Will download file in csv format. Please add \".csv\" to file manually before saving")
                submit_button = st.form_submit_button(label = "Submit")
            
            if dl == "Yes":
                st.sidebar.markdown(get_table_download_link(recs), unsafe_allow_html=True)
            
            st.stop()
    elif query_type == "Textbox":
        query = st.sidebar.text_area("Enter your query", '', help = "Please enter the query you want conference recommendations for")
        if not query: 
            st.write("Please enter the query you want conference recommendations for")
            st.stop()
        with st.spinner("Calculating your recommendations!"):
            query_scores = getBM25Ranks(preprocessSentences, query, bm25_model)
            recs = getRecs(query_scores, number_of_recs, wikicfp_corpus).reset_index()
            recs.index += 1
            st.write(f"Here are the top {number_of_recs} recommendations for your query 🎉:")
            st.table(recs[["Conference Title", "Conference Webpage"]])

            with st.sidebar.form(key = "subform_2"):
                dl = st.radio("Do you want to download your recommendations?", ("Yes", "No"), help = "Will download file in csv format. Please add \".csv\" to file manually before saving")
                submit_button = st.form_submit_button(label = "Submit")
            
            if dl == "Yes":
                st.sidebar.markdown(get_table_download_link(recs), unsafe_allow_html=True)
            
            st.stop()
elif rec_type == "Doc2Vec":
    try:
        d2v_model = Doc2Vec.load(str(d2v_model_path))
    except FileNotFoundError:
        st.error("Model does not exist. Aborting app.")
        st.stop()
    if query_type == "File":
        query = st.sidebar.file_uploader("Choose your query", type = ["txt"], help = "Please select the file you want conference recommendations for (must be a txt file)")
        if query:
            stringio = StringIO(query.getvalue().decode("utf-8"))
            query_string = stringio.read()
        else: 
            st.write("Please enter the query you want conference recommendations for")
            st.stop()
        with st.spinner("Calculating your recommendations!"):
            query_scores = getDoc2VecScores(preprocessSentences, query_string, d2v_model)
            recs = getDoc2VecRecs(query_scores, number_of_recs, wikicfp_corpus).reset_index()
            recs.index += 1
            st.write(f"Here are the top {number_of_recs} recommendations for your query 🎉:")
            st.table(recs[["Conference Title", "Conference Webpage"]])
            
            with st.sidebar.form(key = "subform_3"):
                dl = st.radio("Do you want to download your recommendations?", ("Yes", "No"), help = "Will download file in csv format. Please add \".csv\" to file manually before saving")
                submit_button = st.form_submit_button(label = "Submit")
            
            if dl == "Yes":
                st.sidebar.markdown(get_table_download_link(recs), unsafe_allow_html=True)
            
            st.stop()
    elif query_type == "Textbox":
        query = st.sidebar.text_area("Enter your query", '', help = "Please enter the query you want conference recommendations for")
        if not query: 
            st.write("Please enter the query you want conference recommendations for")
            st.stop()
        with st.spinner("Calculating your recommendations!"):
            query_scores = getDoc2VecScores(preprocessSentences, query, d2v_model)
            recs = getDoc2VecRecs(query_scores, number_of_recs, wikicfp_corpus).reset_index()
            recs.index += 1
            st.write(f"Here are the top {number_of_recs} recommendations for your query 🎉:")
            st.table(recs[["Conference Title", "Conference Webpage"]])
            
            with st.sidebar.form(key = "subform_4"):
                dl = st.radio("Do you want to download your recommendations?", ("Yes", "No"), help = "Will download file in csv format. Please add \".csv\" to file manually before saving")
                submit_button = st.form_submit_button(label = "Submit")
            
            if dl == "Yes":
                st.sidebar.markdown(get_table_download_link(recs), unsafe_allow_html=True)
            
            st.stop()
elif rec_type == "TF-IDF":
    try:
        tfidfvec = createVectorizer()
        tfidf_model = createTFIDFModel(wiki_token, "tokenized_soup", tfidfvec)
    except Exception:
        st.error("Oh no. Something broke. Aborting app.")
        st.stop()
    if query_type == "File":
        query = st.sidebar.file_uploader("Choose your query", type = ["txt"], help = "Please select the file you want conference recommendations for (must be a txt file)")
        if query:
            stringio = StringIO(query.getvalue().decode("utf-8"))
            query_string = stringio.read()
        else: 
            st.write("Please enter the query you want conference recommendations for")
            st.stop()
        with st.spinner("Calculating your recommendations!"):
            query = processQuery(query_string, preprocessSentences, tfidfvec)
            query_scores = cosine_similarity(query, tfidf_model).flatten()
            recs = getTFIDFRecs(query_scores, number_of_recs, wikicfp_corpus).reset_index()
            recs.index += 1
            st.write(f"Here are the top {number_of_recs} recommendations for your query 🎉:")
            st.table(recs[["Conference Title", "Conference Webpage"]])
            
            with st.sidebar.form(key = "subform_5"):
                dl = st.radio("Do you want to download your recommendations?", ("Yes", "No"), help = "Will download file in csv format. Please add \".csv\" to file manually before saving")
                submit_button = st.form_submit_button(label = "Submit")
            
            if dl == "Yes":
                st.sidebar.markdown(get_table_download_link(recs), unsafe_allow_html=True)
            
            st.stop()
    elif query_type == "Textbox":
        query = st.sidebar.text_area("Enter your query", '', help = "Please enter the query you want conference recommendations for")
        if not query: 
            st.write("Please enter the query you want conference recommendations for")
            st.stop()
        with st.spinner("Calculating your recommendations!"):
            query = processQuery(query, preprocessSentences, tfidfvec)
            query_scores = cosine_similarity(query, tfidf_model).flatten()
            recs = getTFIDFRecs(query_scores, number_of_recs, wikicfp_corpus).reset_index()
            recs.index += 1
            st.write(f"Here are the top {number_of_recs} recommendations for your query 🎉:")
            st.table(recs[["Conference Title", "Conference Webpage"]])
            
            with st.sidebar.form(key = "subform_6"):
                dl = st.radio("Do you want to download your recommendations?", ("Yes", "No"), help = "Will download file in csv format. Please add \".csv\" to file manually before saving")
                submit_button = st.form_submit_button(label = "Submit")
            
            if dl == "Yes":
                st.sidebar.markdown(get_table_download_link(recs), unsafe_allow_html=True)
            
            st.stop()
