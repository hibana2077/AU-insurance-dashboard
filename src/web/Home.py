import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
from plotly import express as px

API_URL = os.getenv("API_URL", "http://localhost:8081")

# Load data
# file_path = 'revise.csv'
# data = pd.read_csv(file_path)
data = requests.get(f"{API_URL}/data").json()
data = pd.read_json(data, orient='table')

# Page Title
st.title("數據分析 Dashboard")
st.write("以下為保險公司財務數據分析。所有金額單位均為百萬。")

# Data Summary
st.header("數據摘要")
st.write("**數據概況：**")
st.write(data.describe())

# Filtered Data View
st.sidebar.header("資料篩選")
companies = st.sidebar.multiselect("選擇公司名稱", data['Company Name'].unique())
segments = st.sidebar.multiselect("選擇業務類型 (Segment)", data['Segment'].unique())
sub_segments = st.sidebar.multiselect("選擇子業務類型 (Sub-segment)", data['Sub-segment'].unique())

filtered_data = data.copy()
if companies:
    filtered_data = filtered_data[filtered_data['Company Name'].isin(companies)]
if segments:
    filtered_data = filtered_data[filtered_data['Segment'].isin(segments)]
if sub_segments:
    filtered_data = filtered_data[filtered_data['Sub-segment'].isin(sub_segments)]

st.header("篩選後的資料")
st.write(filtered_data)

# Visualizations
st.header("數據視覺化")

# Gross Written Premium Distribution
st.subheader("毛保費分佈")
# format the data: 3,870 -> 3870
filtered_data['Gross written premium'] = filtered_data['Gross written premium']
filtered_data['Gross written premium'].dropna().astype(float)
fig = px.histogram(filtered_data, x='Gross written premium', nbins=20, title="毛保費分佈 (百萬)")
st.plotly_chart(fig)

# Net Profit/Loss by Company
st.subheader("各公司稅後淨利/虧損")
profit_data = filtered_data[['Company Name', 'Net profit/loss after tax']].dropna()
profit_data['Net profit/loss after tax'] = profit_data['Net profit/loss after tax'].astype(float)

# fig, ax = plt.subplots()
# ax.set_title("稅後淨利/虧損 (百萬)")
# ax.set_ylabel("稅後淨利/虧損")
# ax.set_xlabel("公司名稱")
# st.pyplot(fig)
profit_data.set_index('Company Name')['Net profit/loss after tax']

fig = px.bar(profit_data, x=profit_data['Company Name'], y=profit_data['Net profit/loss after tax'], title="稅後淨利/虧損 (百萬)")
st.plotly_chart(fig)


# time chart
st.subheader("時間序列圖")# Reporting date
filtered_data['Reporting date'] = pd.to_datetime(filtered_data['Reporting date'], dayfirst=True)
time_chart_data = filtered_data[['Reporting date', 'Gross written premium']].set_index('Reporting date')
time_chart_data = time_chart_data.resample('QE').sum()

fig = px.line(time_chart_data, x=time_chart_data.index, y='Gross written premium', title="毛保費時間序列圖 (百萬)")
st.plotly_chart(fig)

# Segment-wise Gross Written Premium
st.subheader("業務類型毛保費貢獻")
fig = px.bar(filtered_data, 
             x='Segment', 
             y='Gross written premium', 
             color='Sub-segment', 
             barmode='group',
             title="主業務與子業務毛保費貢獻")
st.plotly_chart(fig)

# Profit/Loss by Sub-segment
st.subheader("子業務稅後淨利/虧損")
profit_sub_segment = filtered_data.groupby('Sub-segment')['Net profit/loss after tax'].sum().reset_index()
fig = px.bar(profit_sub_segment, 
             x='Sub-segment', 
             y='Net profit/loss after tax', 
             title="各子業務稅後淨利/虧損")
st.plotly_chart(fig)

# Time Series Chart by Sub-segment
st.subheader("各子業務毛保費時間序列圖")
time_chart_data = filtered_data.groupby(['Reporting date', 'Sub-segment'])['Gross written premium'].sum().reset_index()
fig = px.line(time_chart_data, 
              x='Reporting date', 
              y='Gross written premium', 
              color='Sub-segment', 
              title="各子業務毛保費時間序列圖")
st.plotly_chart(fig)

# Segment-wise Profit/Loss Heatmap
st.subheader("主業務與子業務的損益熱力圖")
pivot_table = pd.pivot_table(filtered_data, 
                             values='Net profit/loss after tax', 
                             index='Segment', 
                             columns='Sub-segment', 
                             aggfunc='sum', 
                             fill_value=0)
fig = px.imshow(pivot_table, 
                text_auto=True, 
                title="主業務與子業務的損益熱力圖")
st.plotly_chart(fig)