from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.system import SystemMessage
from langchain_openai import ChatOpenAI
import io
import streamlit as st
import base64
import httpx
import requests
import os
import pandas as pd
import matplotlib.figure as figure
import matplotlib.pyplot as plt

DESCRIBE_PROMPT = [
        {"role": "system", "content": "You are an AI Data Analysis Assistant. Help users analyze data, identify patterns, and provide actionable insights."},
        {"role": "user", "content": [
            {"type": "text", "text": "Describe the images as an alternative text"},
            {"type": "image_url", "image_url": {
                "url": "data:image/png;base64,{base64_image}"}
            }
        ]}
    ]

ANALYSIS_PROMPT = ChatPromptTemplate.from_template(
    """
    You are an AI assistant. Write a Python function named `analyze_data` that takes a pandas DataFrame `data` as input 
    and returns a matplotlib figure `fig`. The function should only use pandas and matplotlib for operations. 
    The user's request is: {user_input}, Data Preview: {data_preview}
    """
)

class AnalysisOutput(BaseModel):
    code: str = Field(description="The Python code to define a function that analyzes the data.")
    explanation: str = Field(description="A short explanation of the function's purpose.")

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

API_URL = os.getenv("API_URL", "http://localhost:8080")
OPEN_API_KEY = os.getenv("OPENAI_API_KEY", "sk_test_1234567890")

if OPEN_API_KEY == "sk_test_1234567890":
    st.warning("Please set your OpenAI API key in the environment variable OPENAI_API_KEY.")

chat_tmp = init_chat_history()
llm = ChatOpenAI(model="gpt-4o-2024-11-20", temperature=0, api_key=OPEN_API_KEY)
structured_llm = llm.with_structured_output(AnalysisOutput)
dialogue_llm = chat_tmp | llm | StrOutputParser()
user_input = st.chat_input("Describe the analysis you want to perform on the data.")

if user_input:
    with st.status("Fetching data...") as status:
        try:
            response = requests.get(f"{API_URL}/data")
            response.raise_for_status()
            raw_data = response.json()
            data = pd.read_json(raw_data, orient='table')
            st.write("Data Preview:")
            st.dataframe(data.head())

            # Generate function code
            status.update(label="Generating analysis function...")
            analysis_prompt = ANALYSIS_PROMPT.format(user_input=user_input, data_preview=data.head())
            parsed_response = structured_llm.invoke(analysis_prompt)

            st.code(parsed_response.code, language="python")
            st.write(f"**Explanation:** {parsed_response.explanation}")

            # Execute the generated function
            exec_locals = {}
            try:
                exec(parsed_response.code, {"pd": pd, "plt": plt}, exec_locals)
                if "analyze_data" in exec_locals:
                    analyze_data = exec_locals["analyze_data"]
                    fig = analyze_data(data)
                    st.pyplot(fig)
                    st.session_state['temp_fig'] = fig
                else:
                    st.error("Generated code did not define the expected `analyze_data` function.")
            except Exception as e:
                st.error(f"Error executing the generated function: {e}")
        except requests.RequestException as e:
            st.error(f"Failed to fetch data: {e}")

        # add the user input and response to the chat history
        chat_tmp.append(HumanMessage(user_input))
        if "temp_fig" in st.session_state:
            # convert the plot to base64
            image_data_a = io.BytesIO()
            st.session_state['temp_fig'].savefig(image_data_a, format='jpeg')
            image_data = base64.b64encode(image_data_a.getvalue()).decode('utf-8')
            chat_tmp.append(HumanMessage("Here is the analysis figure:"))
            chat_tmp.append(HumanMessage(content=[{"type": "image_url","image_url": {"url": f"data:image/jpeg;base64,{image_data}"}, "caption": "Analysis Result"}]))


            status.update(label="Assistant is responding...")

            # invoke the assistant
            DESCRIBE_PROMPT[1]["content"][0]["text"] = user_input
            DESCRIBE_PROMPT[1]["content"][1]["image_url"]["url"] = f"data:image/jpeg;base64,{image_data}"
            ai_message = llm.invoke(DESCRIBE_PROMPT)
            chat_tmp.append(AIMessage(ai_message.content))
            st.session_state['chat_history'] = chat_tmp
            # clear the temp fig
            del st.session_state['temp_fig']
        

for message in st.session_state['chat_history'].messages:
    if isinstance(message, HumanMessage):
        # if is plot
        if type(message.content) == list and message.content[0]["type"] == "image_url":
            with st.chat_message("assistant"):
                st.image(message.content[0]["image_url"]["url"], caption=message.content[0]["caption"])
        elif message.content == "Here is the analysis figure:":
            continue
        else:
            with st.chat_message("user"):
                st.write(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.write(message.content)
    