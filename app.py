import fitz  # PyMuPDF
import streamlit as st
import google.generativeai as genai
import os
import io
import toml 
with open('.streamlit\secrets.toml', 'r') as f:
        config = toml.load(f)
# Configure Gemini
genai.configure(api_key=config["GEMINI_API_KEY"])

# ---------- Extract text from PDF ----------
def extract_text_from_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

# ---------- AI Suggestion ----------
def optimize_resume(resume_text, job_desc):
    prompt = f"""
    You are an expert resume writer.
    Job description:
    {job_desc}

    Resume text:
    {resume_text}

    Please rewrite and improve the resume to best match the job description while maintaining honesty and factual accuracy.
   
    FORMAT REQUIREMENTS - Follow this EXACT structure:
   
    1. HEADER SECTION:
    - Full Name (centered, larger font)
    - Phone Number | Email Address | LinkedIn Profile | Location
    - Professional headline/title
   
    2. PROFESSIONAL SUMMARY:
    - 3-4 line compelling summary highlighting key qualifications
    - Include relevant years of experience and key skills
   
    3. CORE COMPETENCIES/SKILLS:
    - List 8-12 relevant technical and soft skills
    - Organize in bullet points or comma-separated format
   
    4. PROFESSIONAL EXPERIENCE:
    - List in reverse chronological order
    - Company Name, Job Title, Location, Dates
    - 3-5 bullet points per role using action verbs
    - Quantify achievements with numbers/percentages where possible
    - Highlight accomplishments relevant to the target job
   
    5. EDUCATION:
    - Degree, Institution, Location, Graduation Date
    - Include relevant coursework, honors, or GPA if impressive
   
    6. ADDITIONAL SECTIONS (if applicable):
    - Certifications
    - Projects
    - Awards/Achievements
    - Publications
    - Languages
   
    OPTIMIZATION GUIDELINES:
    - Use keywords from the job description naturally throughout
    - Start bullet points with strong action verbs
    - Focus on achievements, not just job duties
    - Keep it concise but comprehensive (1-2 pages)
    - Use consistent formatting and professional language
    - Tailor the content to match the specific role requirements
   
    Return the complete optimized resume in the specified format.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()

# ---------- Overlay text onto original PDF ----------
def overlay_text_on_pdf(original_pdf_bytes, updated_text):
    # Open original PDF
    doc = fitz.open(stream=original_pdf_bytes, filetype="pdf")

    # Remove old text (optional, comment out if you want to overlay only)
    for page in doc:
        page.clean_contents()  # WARNING: this wipes text but keeps graphics/images

    # Now overlay updated text (simple version: one block per page)
    for i, page in enumerate(doc):
        rect = fitz.Rect(50, 50, 550, 800)  # adjust placement box
        page.insert_textbox(rect, updated_text,
                            fontsize=10,
                            fontname="helv",
                            color=(0, 0, 0),
                            align=0)

    # Save updated PDF into memory
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ---------- Streamlit App ----------
st.title("📄 AI Resume Optimizer (Preserve PDF Design)")

uploaded_resume = st.file_uploader("Upload Resume (PDF only)", type=["pdf"])
job_desc = st.text_area("Paste Job Description", height=200)

if uploaded_resume and job_desc:
    if st.button("🔍 Optimize Resume"):
        resume_text = extract_text_from_pdf(uploaded_resume.read())
        optimized_text = optimize_resume(resume_text, job_desc)

        st.subheader("Preview Optimized Resume Text")
        st.text_area("", optimized_text, height=400)

        # Overlay new text back onto original PDF
        uploaded_resume.seek(0)  # reset pointer
        final_pdf = overlay_text_on_pdf(uploaded_resume.read(), optimized_text)

        st.download_button(
            "📥 Download Optimized Resume (PDF with Original Style)",
            data=final_pdf,
            file_name="optimized_resume.pdf",
            mime="application/pdf"
        )
