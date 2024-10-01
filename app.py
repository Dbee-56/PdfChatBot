import os
import re
import chromadb
import time
import streamlit as st
import numpy as np
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import google.generativeai as genai
from sentence_transformers import SentenceTransformer

load_dotenv()
GOOGLE_API_KEY=os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

def get_pdf_text(pdfs):
    text = ""
    count = []
    for pdf in pdfs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text+=page.extract_text()
        count.append(len(text))
    return text,count

def create_overlapping_chunks(text, chunk_size, overlap_size,count):
    chunks = []
    temp = []
    start = 0
    i = 0
    end = min(chunk_size, len(text))
    while start < len(text):
        chunks.append(text[start:end])
        if i<len(count) and start<count[i]:
            temp.append(i)
        elif i<len(count):
            i+=1
            temp.append(i)
        start += chunk_size - overlap_size
        end = min(start + chunk_size, len(text))
    return chunks,temp

def create_chromadb():
    client = chromadb.PersistentClient(path="./Database")
    try:
        client.delete_collection('vectoreStore')
    except Exception as e:
        print("Creating Collection...")
    vectoreStore = client.create_collection("vectoreStore")
    print("Collection created......")
    return vectoreStore

def add_values(vectoreStore,ids,embeddings,metadatas,chunks):
    vectoreStore.upsert(
        ids = ids,
        embeddings = embeddings['embedding'],
        metadatas=metadatas,
        documents = chunks
    )

def create_embeddings_and_metadata(chunks,temp):
    ids = []
    metadatas = []

    embeddings = genai.embed_content(
        model="models/embedding-001",
        content=chunks,
        task_type="SEMANTIC_SIMILARITY"
    )

    for i in range(1,len(chunks)+1):
        ids.append(str(i))
    for i in range(0,len(temp)):
        metadatas.append({'source':temp[i]+1})

    return ids,metadatas,embeddings

def get_collection():
    client = chromadb.PersistentClient(path="./Database")
    vectoreStore=client.get_collection("vectoreStore")
    return vectoreStore

def user_input(question,chunks):
    vectoreStore = get_collection()
    model = genai.GenerativeModel('gemini-pro')

    embedding = genai.embed_content(
        model="models/embedding-001",
        content = question,
        task_type = "SEMANTIC_SIMILARITY"
    )

    results = vectoreStore.query(
        query_embeddings=embedding['embedding'],
        n_results = 1
    )

    for chat in st.session_state['chat_history']:
        if len(st.session_state['prev_question'])>2:
            st.session_state['prev_question'].pop(0)
            st.session_state['prev_context'].pop(0)
        st.session_state['prev_question'].append(chat['question'])
        st.session_state['prev_context'] .append(chat['Context'])

    index = int(results['ids'][0][0])-1
    if (index+1)<len(chunks):
        context = chunks[index-1] + chunks[index] + chunks[index+1]
    else:
        context = chunks[index-1] + chunks[index]
    
    input_text=f"You are a chatbot iam providing the previous conversation:\n prev_questions:{st.session_state['prev_question']},prev_context:{st.session_state['prev_context']} if both are null then no prev conversation had taken place \n And New Question:\n new_question:{question},new_context:{context}\n Consider new_question,new_context,prev_question,prev_context then give answers for new_question \n Output should contain Answer nothing else" 

    response = model.generate_content(input_text)

    emb2 = genai.embed_content(
        model="models/embedding-001",
        content = response.text,
        task_type = "SEMANTIC_SIMILARITY"
    )

    results2 = vectoreStore.query(
        query_embeddings=emb2['embedding'],
        n_results = 1
    )

    st.session_state['chat_history'].append({'question':question,'Context':context,'Answer':response.text,'Source':results2['metadatas'][0][0]['source']-1,'Chunks':chunks[int(results2['ids'][0][0])-1]})
    return(response.text)


def response_generator(response):
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

def main():
    st.header("ChatBot🤖")
    st.subheader("Enter any question regarding the uploaded File..")
    with st.sidebar:
        st.title("Chat With PDFs")
        pdfs = st.file_uploader("Upload your PDF and click submit",type = "pdf",accept_multiple_files=True)
        st.session_state['pdfs'] = pdfs
        if st.button("Submit"):
            with st.spinner("Processing..."):
                text,count=get_pdf_text(pdfs)
                chunks,temp = create_overlapping_chunks(text,700,300,count)
                chunks=[re.sub(r'[\n]|(\.{2,})',' ',chunk)for chunk in chunks]
                st.session_state['chunks'] = chunks
                vectoreStore = create_chromadb()
                ids,metadatas,embeddings=create_embeddings_and_metadata(chunks,temp)
                add_values(vectoreStore,ids,embeddings,metadatas,chunks)
                st.success("File Uploaded ✔")

    for message in st.session_state['chat_history']:
        with st.chat_message("user"):
            st.markdown(message['question'])
        
        with st.chat_message("assistant"):
            st.markdown(message['Answer'])
            doc_name = st.session_state['pdfs'][message['Source']].name
            expander = st.expander("See Source Document")
            expander.markdown(f"Source Document is: {doc_name}")

    if query := st.chat_input("Enter your question.."):
        with st.chat_message("user"):
            st.markdown(query)
        chunks = st.session_state['chunks']
        with st.chat_message("assistant"):
            response = user_input(query,chunks)
            st.write(response)
            # response = st.write_stream(response_generator(response))
            doc_name=st.session_state['pdfs'][st.session_state['chat_history'][-1]['Source']].name
            expander = st.expander("See Source Document")
            expander.markdown(f"Source Document is: {doc_name}")

        
            
if __name__ == "__main__":

    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    if 'prev_question' not in st.session_state:
        st.session_state['prev_question'] = []
    if 'prev_context' not in st.session_state:
        st.session_state['prev_context'] = []

    main()


