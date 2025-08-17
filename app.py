import streamlit as st
import google.generativeai as genai
import io
import os
from PyPDF2 import PdfReader
from docx import Document
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# Configure Gemini API key (from environment variable or secrets.toml)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ----------- Helper Functions ------------
def extract_text_from_pdf(uploaded_file):
    pdf = PdfReader(uploaded_file)
    text = ""
    for page in pdf.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(uploaded_file):
    doc = Document(uploaded_file)
    return "\n".join([para.text for para in doc.paragraphs])

def generate_corrected_resume(resume_text, job_desc):
    prompt = f"""
    You are an expert resume writer.
    Here is a job description:
    {job_desc}

    Here is the candidate's resume:
    {resume_text}

    Rewrite and improve the resume so it best matches the job description 
    while keeping honesty and factual accuracy. Return the full corrected resume.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text

def save_resume_to_pdf(resume_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = [Paragraph(line, styles["Normal"]) for line in resume_text.split("\n") if line.strip()]
    doc.build(story)
    buffer.seek(0)  # rewind to start
    return buffer

# ----------- Streamlit UI ------------
st.title("AI Resume Optimizer (Gemini API)")

uploaded_resume = st.file_uploader("Upload your Resume (PDF or DOCX)", type=["pdf", "docx"])
job_desc = st.text_area("Paste the Job Description")

if uploaded_resume and job_desc:
    if st.button("Generate Optimized Resume"):
        with st.spinner("Optimizing your resume..."):

            # Extract resume text
            if uploaded_resume.type == "application/pdf":
                resume_text = extract_text_from_pdf(uploaded_resume)
            elif uploaded_resume.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                resume_text = extract_text_from_docx(uploaded_resume)
            else:
                st.error("Unsupported file format")
                st.stop()

            # Generate corrected resume
            corrected_resume = generate_corrected_resume(resume_text, job_desc)

            # Save to PDF (in memory)
            pdf_buffer = save_resume_to_pdf(corrected_resume)

            # Show download button
            st.success("Resume optimized successfully!")
            st.download_button(
                label="📥 Download Optimized Resume",
                data=pdf_buffer,
                file_name="optimized_resume.pdf",
                mime="application/pdf"
            )
