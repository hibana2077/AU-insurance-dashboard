from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.system import SystemMessage
from langchain_groq.chat_models import ChatGroq
from langchain_openai.chat_models import ChatOpenAI
from langchain_ollama.chat_models import ChatOllama
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
import streamlit as st
import requests
import os

OLLAMA_SERVER = os.getenv("OLLAMA_SERVER", "http://localhost:11434")
BACKEND_SERVER = os.getenv("BACKEND_SERVER", "http://localhost:8081")
OPEN_API_KEY = os.getenv("OPENAI_API_KEY", "sk_test_1234567890")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "gsk_test_1234567890")
TRANSLATOR_PROVIDER = os.getenv("TRANSLATOR_PROVIDER", "google")
EXTRACT_PROMPT = ChatPromptTemplate.from_template(
    "You are an Top algorithm, you need to according to user input extract information from the content. user input: {user_input}, content: {content}"
)

if 'chat_model' not in st.session_state:
    st.session_state['chat_model'] = "llama-3.3-70b-versatile-groq"
    # st.session_state['chat_model'] = "llama-3.1-70b-versatile-groq"

def get_all_embeddings() -> list:
    response = requests.get(f"{BACKEND_SERVER}/embedding_count")
    if response.status_code == 200:
        return response.json()["embedding_names"]
    else:
        return []

def embeddings_search(user_input: str, embedding_name: str) -> dict:
    # user_input = ts.translate_text(user_input, translator=TRANSLATOR_PROVIDER, to_language="en")
    response = requests.post(f"{BACKEND_SERVER}/embed_query", json={"user_input": user_input, "embedding_name": embedding_name})
    if response.status_code == 200:
        return response.json()
    else:
        return {"embeddings": [], "time": 0}

def init_chat_history() -> ChatPromptTemplate:
    if 'chat_history' not in st.session_state:
        template = ChatPromptTemplate.from_messages([
            ('system', "You are an AI Teaching Assistant, you need to help students with their questions based on the extracted information."),
        ])
        st.session_state['chat_history'] = template
    else:
        template = st.session_state['chat_history']
    return template

header_col, embeddings_select_col = st.columns([0.7,0.3])

with header_col:
    st.header("Chat")

with embeddings_select_col:
    embeddings = get_all_embeddings()
    embeddings_select = st.selectbox("Select an embedding", embeddings, index=None)
    student_id = st.text_input("Student ID")

st.divider()

chat_tmp = init_chat_history()
# llm = ChatOllama(model=st.session_state['chat_model'], base_url=OLLAMA_SERVER)
if st.session_state['chat_model'][-4:] == "groq":
    llm = ChatGroq(model=st.session_state['chat_model'][0:-5], api_key=GROQ_API_KEY)
elif st.session_state['chat_model'][-6:] == "openai":
    llm = ChatOpenAI(model=st.session_state['chat_model'][0:-7], api_key=OPEN_API_KEY)
else:
    llm = ChatOllama(model=st.session_state['chat_model'], base_url=OLLAMA_SERVER)
user_input = st.chat_input("You can start a conversation with the AI Teaching Assistant here.")
chain = chat_tmp | llm | StrOutputParser()

if user_input:
    if embeddings_select != None:
        enable_guided_reply = False
        # check user input is similar to previous questions
        questions = requests.get(f"{BACKEND_SERVER}/user_rec", json={"student_id": student_id, "embedding_name": embeddings_select, "question_str": user_input})
        # using text embedding to check similarity
        # if similarity > 0.9, return the response
        # else, continue to search the content
        if questions.status_code == 200:
            questions = questions.json()
            if "questions" in questions.keys():

                # using text embedding to check similarity
                vectorstore = InMemoryVectorStore(OllamaEmbeddings(model='nomic-embed-text', base_url=OLLAMA_SERVER))
                temp_documents = []
                for idx,question in enumerate(questions["questions"]):
                    temp_documents.append(Document(id=str(idx), page_content=question))
                vectorstore.add_documents(documents=temp_documents)
                results = vectorstore.similarity_search_with_score(
                    query=user_input, k=1
                )
                retrieved_documents = [doc for doc, score in results if score > 0.75]

                # if similarity > 0.75, enable guided reply
                if len(retrieved_documents) > 0:
                    enable_guided_reply = True
                else:
                    enable_guided_reply = False
                
                # clean up
                del temp_documents
                del results
                del vectorstore
                del retrieved_documents
        else:
            st.error("Failed to get user questions from the server.")

        # save user input to redis
        # name -> student_id, value -> {embedding_name: embedding_name, conversation_times: 1}
        response = requests.post(f"{BACKEND_SERVER}/user_rec", json={"student_id": student_id, "embedding_name": embeddings_select, "question_str": user_input})
        if response.status_code != 200:
            st.error("Failed to save user input to the server.")

        with st.status("Searching for book content..."):
            embeddings_search_result = embeddings_search(user_input, embeddings_select)

        with st.status("Extracting information..."):
            extracted_info = ""
            for embedding in embeddings_search_result["results"]:
                # embedding is dict with keys: "page_content", "metadata"
                # metadata is dict with keys: "page", "source"
                extract_template = EXTRACT_PROMPT
                extract_chain = extract_template | llm | StrOutputParser()
                extract_response = extract_chain.invoke({"user_input": user_input, "content": embedding["page_content"]})
                extracted_info += f"Page {embedding['metadata']['page']}: {extract_response}\n"
            
        with st.status("Digital TA Thinking..."):
            chat_tmp.append(SystemMessage(f"Extracted information from the content: {extracted_info}"))
            if enable_guided_reply:
                chat_tmp.append(SystemMessage("The AI Teaching Assistant found similar questions from the student."))
                chat_tmp.append(SystemMessage("You should provide a response in guided mode. Not directly respond to the user input, help student think and find the answer."))
            chat_tmp.append(HumanMessage(user_input))
            response = chain.invoke({})
            chat_tmp.append(AIMessage(response))
            st.session_state['chat_history'] = chat_tmp
    
    else:
        with st.status("Digital TA Thinking..."):
            chat_tmp.append(HumanMessage(user_input))
            response = chain.invoke({})
            chat_tmp.append(AIMessage(response))
            st.session_state['chat_history'] = chat_tmp

for message in st.session_state['chat_history'].messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.write(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.write(message.content)