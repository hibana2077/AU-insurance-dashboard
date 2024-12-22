import pandas as pd

# Define the URL of the xlsx file
xlsx_url = "https://www.apra.gov.au/sites/default/files/2024-08/%5B20240820%5D%20Quarterly%20general%20insurance%20institution-level%20statistics%20database%20%28historical%20data%29%20from%20September%202017%20to%20June%202023.xlsx"

# Download and read the xlsx file
file_path = "./data.xlsx"
df_table_1a = pd.read_excel(xlsx_url, sheet_name="Table 1a")

df_cleaned = df_table_1a.iloc[2:]
df_cleaned.columns = df_table_1a.iloc[2]
df_cleaned = df_cleaned.iloc[1:]

# print(df_cleaned.columns)
# print(df_cleaned)
print(df_cleaned.to_json())