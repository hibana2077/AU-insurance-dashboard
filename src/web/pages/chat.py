from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.system import SystemMessage
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.documents import Document
import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px

OLLAMA_SERVER = os.getenv("OLLAMA_SERVER", "http://localhost:11434")
BACKEND_SERVER = os.getenv("BACKEND_SERVER", "http://localhost:8081")
API_URL = os.getenv("API_URL", "http://localhost:8080")
OPEN_API_KEY = os.getenv("OPENAI_API_KEY", "sk_test_1234567890")
EXTRACT_PROMPT = ChatPromptTemplate.from_template(
    "You are an AI Data Analysis Assistant. Extract relevant insights, trends, and potential issues from the data provided. User input: {user_input}, content: {content}"
)

def init_chat_history() -> ChatPromptTemplate:
    if 'chat_history' not in st.session_state:
        template = ChatPromptTemplate.from_messages([
            ('system', "You are an AI Data Analysis Assistant. Help users analyze data, identify patterns, and provide actionable insights."),
        ])
        st.session_state['chat_history'] = template
    else:
        template = st.session_state['chat_history']
    return template

header_col, embeddings_select_col = st.columns([0.7, 0.3])

with header_col:
    st.header("Data Analysis Chat")

st.divider()

chat_tmp = init_chat_history()
llm = ChatOpenAI(model="o1", api_key=OPEN_API_KEY)
user_input = st.chat_input("Ask the AI Data Analysis Assistant a question.")
chain = chat_tmp | llm | StrOutputParser()

if user_input:
    with st.status("Fetching data..."):
        try:
            response = requests.get(f"{API_URL}/data")
            response.raise_for_status()
            raw_data = response.json()
            data = pd.DataFrame.from_records(raw_data)
            st.write("Data Preview:")
            st.dataframe(data.head())

            # Generate analysis code using LLM
            with st.status("Generating analysis code..."):
                chat_tmp.append(HumanMessage(user_input))
                analysis_request = f"Write Python code to analyze the following data: {data.head(3).to_dict()} based on the user's request: '{user_input}'. Include a visualization using Plotly."
                chat_tmp.append(SystemMessage(analysis_request))
                analysis_code = chain.invoke({"user_input": analysis_request})

                st.code(analysis_code, language="python")

                # Execute the generated code (use with caution!)
                exec_locals = {}
                try:
                    exec(analysis_code, {"data": data, "px": px}, exec_locals)
                    if "fig" in exec_locals:
                        st.plotly_chart(exec_locals["fig"])
                    else:
                        st.error("Generated code did not produce a figure.")
                except Exception as e:
                    st.error(f"Error executing generated code: {e}")

                chat_tmp.append(AIMessage("Generated and executed the analysis code."))
                st.session_state['chat_history'] = chat_tmp
        except requests.RequestException as e:
            st.error(f"Failed to fetch data: {e}")

for message in st.session_state['chat_history'].messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.write(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.write(message.content)
