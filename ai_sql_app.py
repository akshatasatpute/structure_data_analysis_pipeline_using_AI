import streamlit as st
import pandas as pd
import sqlite3
import os
import google.generativeai as genai
from dotenv import load_dotenv


#oad_dotenv(r"C:\Users\User\Downloads\gemini_ai\api.env")
#PI_KEY = os.getenv("GOOGLE_API_KEY")


#Prefer Streamlit secrets if running on Streamlit Cloud
API_KEY = st.secrets["GOOGLE_API_KEY"]

genai.configure(api_key=API_KEY)

#Get list of gemini models

#results = genai.list_models()
#for m in results:
    #print(m.name)

# --------------------------------------
# Configure Gemini
# --------------------------------------
def get_model(api_key):
    genai.configure(api_key=API_KEY)
    return genai.GenerativeModel("gemini-2.5-flash")


# --------------------------------------
# Simple function: Ask Gemini to create SQL
# --------------------------------------
def ask_gemini_for_sql(model, question, columns, table_name="data"):
    prompt = f"""
    You are a senior data analyst agent that answers questions using a SQLite database
    created from a CSV file. You MUST respond with ONLY a single valid SQLite SQL query
    that can be executed directly, and NOTHING else.

    RULES:
    - Output ONLY the final optimized SQL query.
    - Do NOT include explanations, comments, markdown, backticks, or extra text.
    - The output must begin with the keyword SELECT.
    - Produce exactly one single-statement SELECT query.
    - Use only existing columns.
    

    Table name: {table_name}
    Columns: {columns}

    User question: {question}

    Remember: reply with ONLY the final optimized SQL query, nothing else.
    """
    resp = model.generate_content(prompt)
    sql = resp.text.strip()

    # Remove accidental code fences
    if sql.startswith("```"):
        sql = sql.replace("```", "").replace("sql", "").strip()

    return sql


# --------------------------------------
# Simple function: Ask Gemini to explain results
# --------------------------------------
def explain_results(model, question, rows):
    prompt = f"""
    
    You are a helpful data analyst AI. You get:
    - the original user question,
    - the SQL query that was executed,
    - the tabular result.

    Your job:
    - Explain the answer in clear, concise language.
    - If relevant, highlight trends, outliers, or interesting insights.
    - If there are many rows, summarize instead of listing everything.
    - If no rows are returned, explain that clearly and suggest how to adjust the question.
    
    User question: {question}
    Query output: {rows}
    
    Now give a clear explanation to the user.

    Explain this output in simple English.
    """

    resp = model.generate_content(prompt)
    return resp.text


# --------------------------------------
# Streamlit UI
# --------------------------------------
st.markdown(
    "<span style='color:#228B22; font-weight:bold; font-size:40px;'>Structured Data Analysis Pipeline:</span>",
    unsafe_allow_html=True
    )
#st.title("Structured Data Analysis Pipeline")

api_key = API_KEY

uploaded = st.file_uploader("Upload CSV", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
    st.write("Preview of uploaded data:")

    st.dataframe(df.head(2))

    # Convert CSV → SQLite
    conn = sqlite3.connect(":memory:")
    df.to_sql("data", conn, index=False, if_exists="replace")

    st.success("CSV loaded into SQLite database!")

    question = st.text_input("Ask a question about your data:")

    if question:
        try:
            # Create LLM model
            model = get_model(api_key)

            # 1️ Ask Gemini to create SQL
            columns = ", ".join(df.columns)
            sql_query = ask_gemini_for_sql(model, question, columns)

            st.write(" **Generated SQL Query:**")
            st.code(sql_query)

            # 2️ Run SQL on SQLite
            cursor = conn.execute(sql_query)
            rows = cursor.fetchall()

            if rows:
                result_df = pd.DataFrame(rows, columns=[col[0] for col in cursor.description])
                st.write("📄 **Query Output (Table):**")
                st.dataframe(result_df)
            else:
                st.info("Query returned no rows.")

            # 3️ Ask Gemini to explain
            explanation = explain_results(model, question, rows)
            st.write(" **Explanation:**")
            st.write(explanation)

        except Exception as e:
            st.error(f"Error: {e}")

else:
    st.info("Please upload a CSV file to begin.")
