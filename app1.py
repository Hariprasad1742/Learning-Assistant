import streamlit as st
import fitz  # PyMuPDF
import requests
from fpdf import FPDF
from bs4 import BeautifulSoup

# Groq API Setup
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

st.set_page_config(page_title="Duratech AI MS Learning Assistant", layout="wide")
st.title("📘 Duratech Learning Assistant")
st.caption("Upload MS study material PDFs to get summaries, quizzes, flashcards, and ask questions")

# Session states
for key in ["notes", "chat_history", "pdf_text", "quiz_text", "flashcard_text", "summary_text"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "chat_history" else []

# Helper: Extract text from uploaded PDFs
def extract_text_from_pdfs(files):
    combined_text = ""
    for pdf_file in files:
        with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
            for page in doc:
                combined_text += page.get_text()
    return combined_text

# Helper: Clean HTML to text
def html_to_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n")

# Groq API Completion
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
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        res_json = response.json()
        if "choices" in res_json:
            return html_to_text(res_json["choices"][0]["message"]["content"])
        else:
            st.error(f"Groq API error: {res_json}")
            return "❌ No response from Groq."
    except Exception as e:
        st.error(f"Exception occurred: {e}")
        return "❌ Error connecting to Groq."

# Summary
def generate_summary(text):
    prompt = f"Summarize this Microsoft study material:\n\n{text[:3000]}"
    return groq_chat_completion([{"role": "user", "content": prompt}])

# Quiz
def generate_quiz(text):
    prompt = f"Create 3 multiple-choice quiz questions with answers from this Microsoft subject content:\n\n{text[:3000]}"
    return groq_chat_completion([{"role": "user", "content": prompt}])

# Flashcards
def generate_flashcards(text):
    prompt = f"Create 3 flashcards (Q&A style) from this Microsoft subject material:\n\n{text[:3000]}"
    return groq_chat_completion([{"role": "user", "content": prompt}])

# Ask Questions
def ask_with_context(question):
    history = st.session_state.chat_history[-6:]
    messages = [{"role": "system", "content": "You are a helpful assistant for Microsoft study materials."}]
    messages.extend(history)
    messages.append({
        "role": "user",
        "content": f"Material:\n{st.session_state.pdf_text[:3000]}\n\nQuestion: {question}"
    })
    answer = groq_chat_completion(messages)
    st.session_state.chat_history.append({"role": "user", "content": question})
    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    return answer

# Export to PDF
def export_text_to_pdf(text, filename="output.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.multi_cell(0, 10, line)
    pdf.output(filename)
    return filename

# Upload UI
uploaded_files = st.file_uploader("Upload one or more Microsoft subject PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("📥 Load PDFs"):
        st.session_state.pdf_text = extract_text_from_pdfs(uploaded_files)
        st.success("PDFs loaded successfully!")

    if st.session_state.pdf_text:
        tabs = st.tabs(["📄 Summary", "📝 Notes", "🧠 Quiz & Flashcards", "❓ Ask Questions"])

        with tabs[0]:
            if st.button("🧾 Generate Summary"):
                st.session_state.summary_text = generate_summary(st.session_state.pdf_text)
            st.text_area("Summary", st.session_state.summary_text, height=300)

        with tabs[1]:
            st.session_state.notes = st.text_area("Write your notes below", value=st.session_state.notes, height=300)
            st.download_button("💾 Download Notes", st.session_state.notes, file_name="microsoft_notes.txt")

        with tabs[2]:
            col1, col2 = st.columns(2)

            with col1:
                if st.button("📝 Generate Quiz"):
                    st.session_state.quiz_text = generate_quiz(st.session_state.pdf_text)
                st.text_area("Quiz", st.session_state.quiz_text, height=250)

                if st.session_state.quiz_text:
                    if st.button("⬇️ Export Quiz as PDF"):
                        quiz_pdf_path = export_text_to_pdf(st.session_state.quiz_text, "quiz.pdf")
                        with open(quiz_pdf_path, "rb") as f:
                            st.download_button("Download Quiz PDF", f, file_name="quiz.pdf")

            with col2:
                if st.button("📇 Generate Flashcards"):
                    st.session_state.flashcard_text = generate_flashcards(st.session_state.pdf_text)
                st.text_area("Flashcards", st.session_state.flashcard_text, height=250)

                if st.session_state.flashcard_text:
                    if st.button("⬇️ Export Flashcards as PDF"):
                        flashcard_pdf_path = export_text_to_pdf(st.session_state.flashcard_text, "flashcards.pdf")
                        with open(flashcard_pdf_path, "rb") as f:
                            st.download_button("Download Flashcards PDF", f, file_name="flashcards.pdf")

        with tabs[3]:
            col1, col2 = st.columns([4, 1])
            with col1:
                question = st.text_input("What is your question?")
            with col2:
                get_answer = st.button("🔍 Get Answer")

            if get_answer and question.strip():
                answer = ask_with_context(question)
                st.text_area("Answer", value=answer, height=200)
            elif get_answer:
                st.warning("Please enter a valid question.")
else:
    st.info("Please upload at least one PDF to get started.")
