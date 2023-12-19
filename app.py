import os
from tqdm import tqdm
import streamlit as st
import pandas as pd
from elasticsearch import Elasticsearch

base_data_path = 'data/Результат/'
glossary_columns = ['Термин\xa0', 'Определение\xa0', 'Раздел', 'Бизнес-процесс', 'Роли и уровни управления данными\xa0']

st.set_page_config(layout="wide")

def create_index(es):
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
        data = pd.read_csv(os.path.join(base_data_path, csv_path))
        st.write(f"Добавляем данные из {csv_path}")
        
        for i, row in tqdm(data.iterrows()):
            
            article = {'title': row['pdf'] , 
                        'content': row['Текст из pdf']}

            es.index(index="articles", document=article)
            # st.write(f"add {row['pdf']}")

@st.cache_resource
def load_es_connection():
    # Connect to Elasticsearch
    es = Elasticsearch(
        hosts=[f"http://elastic:9200"],
        basic_auth=('elastic', 'elastic'),
        verify_certs=False,)     
    return es


@st.cache_data
def load_glossary():
    glossary = pd.read_excel('data/Глоссарий.xlsx')
    return glossary

def search(es, query):
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
    results = es.search(index="articles", body=body, size=10000)

    # Extract hits from the results
    hits = results.get('hits', {}).get('hits', [])

    return hits


# Streamlit app
def main():
    es = load_es_connection()
    glossary = load_glossary()
        
    st.title("Бизнес-глоссарий")  # TODO: ввести норм название и инструкцию пользователя
    
    # если индекс в эластике не построен (не существует) если не существуем выводим кнопку построения индекса
    # построение индекса требует час или около отого
    if not es.indices.exists(index="articles"):
        if st.button('Создать индекс'):
            create_index(es)
    
    st.header("Введите ключевые слова для поиска")
    termin = st.multiselect('Термин', glossary['Термин\xa0'].tolist() + ['Другое'])
    all_words = st.checkbox('по набору слов')
    
    if 'Другое' in termin:
        termin[termin.index('Другое')] = st.text_input("Введите свой термин")
    else:
        data_termins = glossary[glossary_columns][glossary['Термин\xa0'].isin(termin)].to_dict(orient='records')
        # st.write(data_termins)
        
    termin = [value.strip() for value in termin]
    
    if termin:       
        for data_term in data_termins:
            with st.expander(data_term[glossary_columns[0]]):
                # st.write(data_term[glossary_columns[1]])
                st.write(data_term)
            
                    
        if st.button("Вывести результаты") and termin:
            if not all_words:
                for value in termin:
                    result = search(es, value)
                    st.write(f'Для термина {value}')
                    st.write(f'Всего документов найдено - {len(result)}')
                    # st.write(result[:10])
                    out = pd.DataFrame([{'Наименование документа': value['_source']['title'], 
                            'Содержимое': value['_source']['content'][:200]}for value in result])
                    st.write(out)
                    
            if all_words:
                out = []
                intersect = []
                for value in termin:
                    result = search(es, value)
                    out += result
                    intersect.append(set(data['_id'] for data in result))
                
                intersection_ids = set.intersection(*intersect)
                # st.write(intersection_ids)
                result = [value for value in out if value['_id'] in intersection_ids]
                st.write(f'Для терминов {", ".join(termin)}')
                st.write(f'Всего документов найдено - {len(result)}')
                out = pd.DataFrame([{'Наименование документа': value['_source']['title'], 
                            'Содержимое': value['_source']['content'][:200]}for value in result])
                st.write(out)
                
    
        
if __name__ == "__main__":
    main()
