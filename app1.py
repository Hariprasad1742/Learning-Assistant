import streamlit as st
import fitz  # PyMuPDF
import requests
import markdown2
from fpdf import FPDF
from bs4 import BeautifulSoup

# Groq API Setup
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Initialize session state variables
if "notes" not in st.session_state:
    st.session_state.notes = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "quiz_text" not in st.session_state:
    st.session_state.quiz_text = ""

# Helper: Extract text from multiple PDFs and combine
def extract_text_from_pdfs(files):
    combined_text = ""
    for pdf_file in files:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        for page in doc:
            combined_text += page.get_text()
    return combined_text

# Helper: Clean HTML to plain text
def html_to_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n")

# Helper: Groq chat completion with context memory
def groq_chat_completion(messages):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-70b-8192",
        "messages": messages,
        "temperature": 0.7
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    try:
        res_json = response.json()
        if "choices" in res_json:
            # Convert any HTML in response to plain text
            raw_content = res_json["choices"][0]["message"]["content"]
            return html_to_text(raw_content)
        else:
            st.error(f"Groq API Error: {res_json}")
            return "❌ Failed to get response from Groq."
    except Exception as e:
        st.error(f"Exception: {e}")
        st.text(response.text)
        return "❌ Something went wrong."

# Generate summary
def generate_summary(text):
    prompt = f"Summarize this Microsoft study material:\n\n{text[:3000]}"
    return groq_chat_completion([{"role": "user", "content": prompt}])

# Generate quiz in flashcard style
def generate_flashcard_quiz(text):
    prompt = f"Create 3 flashcard-style questions with answers from this text:\n\n{text[:3000]}"
    return groq_chat_completion([{"role": "user", "content": prompt}])

# Append user question + context memory, get answer
def ask_with_context(question):
    # Build conversation history for context (limit last 6)
    history = st.session_state.chat_history[-6:]
    messages = [{"role": "system", "content": "You are a helpful assistant for Microsoft study materials."}]
    messages.extend(history)
    messages.append({"role": "user", "content": f"Material:\n{st.session_state.pdf_text[:3000]}\n\nQuestion: {question}"})
    answer = groq_chat_completion(messages)
    st.session_state.chat_history.append({"role": "user", "content": question})
    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    return answer

# Export quiz as PDF
def export_quiz_to_pdf(quiz_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in quiz_text.split('\n'):
        pdf.multi_cell(0, 10, line)
    pdf_file = "quiz.pdf"
    pdf.output(pdf_file)
    return pdf_file

# Streamlit UI starts here
st.set_page_config(page_title="AI MS Learning Assistant", layout="wide")
st.title("Duratech Learning Assistant")

uploaded_files = st.file_uploader("Upload one or more MS subject PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Load PDF(s)"):
        st.session_state.pdf_text = extract_text_from_pdfs(uploaded_files)
        st.success("PDF(s) loaded successfully!")

    if st.session_state.pdf_text:
        tabs = st.tabs(["Summary", "Notes", "Quiz & Flashcards", "Ask Questions"])

        with tabs[0]:
            if st.button("Generate Summary"):
                summary_text = generate_summary(st.session_state.pdf_text)
                st.text_area("Summary (plain text)", summary_text, height=300)

        with tabs[1]:
            st.text_area("Your Notes (autosaved)", value=st.session_state.notes, height=300, key="notes")
            st.download_button("Download Notes as TXT", st.session_state.notes, file_name="microsoft_notes.txt")

        with tabs[2]:
            if st.button("Generate Flashcard Quiz"):
                quiz_text = generate_flashcard_quiz(st.session_state.pdf_text)
                st.session_state.quiz_text = quiz_text
                st.text_area("Flashcard Quiz", quiz_text, height=300)

            if st.session_state.quiz_text:
                if st.button("Export Quiz as PDF"):
                    pdf_path = export_quiz_to_pdf(st.session_state.quiz_text)
                    with open(pdf_path, "rb") as f:
                        st.download_button("Download Quiz PDF", f, file_name="quiz.pdf")

        with tabs[3]:
            question = st.text_input("Ask a question based on uploaded PDFs:")
            if st.button("Get Answer"):
                if question.strip():
                    answer = ask_with_context(question)
                    st.text_area("Answer", answer, height=200)
                else:
                    st.warning("Please enter a question.")
else:
    st.info("Please upload PDF(s) to get started.")
