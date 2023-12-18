import os
from tqdm import tqdm
import streamlit as st
from elasticsearch import Elasticsearch

base_data_path = 'data/Результат/'


st.set_page_config(layout="wide")

@st.cache_resource
def load_es_connection():
    # Connect to Elasticsearch
    es = Elasticsearch(
        hosts=[f"http://elastic:9200"],
        basic_auth=('elastic', 'elastic'),
        verify_certs=False,)
    
    if not es.indices.exists(index="articles"):
        article_mappings = {
                "properties": {
                    "title": {
                        "type": "text",
                        "fields": {
                            "russian": {"type": "text", "analyzer": "russian"},
                            "english": {"type": "text", "analyzer": "english"},
                        },
                    },
                    "content": {
                        "type": "text",
                        "fields": {
                            "russian": {"type": "text", "analyzer": "russian"},
                            "english": {"type": "text", "analyzer": "english"},
                        },
                    }
                }
            }
        es.indices.create(index="articles", mappings=article_mappings)
        
        for csv_path in tqdm(os.listdir(base_data_path)):
            data = pd.read_csv(os.paht.join(base_data_path, csv_path))
            
            for i, row in tqdm(data.iterrows()):
                
                article = {'title': row['pdf'] , 
                           'content': row['Текст из pdf']}

                es.index(index="articles", document=article)
        
    return es


@st.cache_data
def load_glossary():
    glossary = pd.read_excel('data/Глоссарий.xlsx')
    return glossary

def search(query):
    # Customize the Elasticsearch query based on your index and requirements
    body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "title",
                    "title.russian",
                    "title.english",
                    "content",
                    "content.russian",
                    "content.english",
                ],
                "type": "most_fields",
            }
        }
    }

    # Execute the search
    results = es.search(index="article", body=body)

    # Extract hits from the results
    hits = results.get('hits', {}).get('hits', [])

    return hits


# Streamlit app
def main():
    es = load_es_connection()
    glossary = load_glossary()
        
    st.title("Глоссарий")  # TODO: ввести норм название и инструкцию пользователя
    
    # Input form
    st.header("Выберите Термин")
    
    termin = st.multiselect('Термин', glossary['Термин\xa0'].tolist() + ['Другое'], index=None)
    if termin == 'Другое':
        termin = st.text_input("Введите свой термин")
        
    st.write(termin)
    
    if st.button("Вывести результаты") and termin:
        result = search(termin)
        
    st.write(result)
    
        
if __name__ == "__main__":
    main()
