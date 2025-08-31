import streamlit as st
import google.generativeai as genai
import io
import os
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from docx import Document
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import inch
import re

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

def extract_jd_from_url(url):
    """Extract job description from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
       
        soup = BeautifulSoup(response.content, 'html.parser')
       
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
       
        # Get text
        text = soup.get_text()
       
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
       
        return text
    except Exception as e:
        st.error(f"Error extracting job description from URL: {str(e)}")
        return None

def check_resume_completeness(resume_text):
    """Check if resume has essential information"""
    missing_info = []
   
    # Check for name (usually at the beginning or in header)
    name_pattern = r'^[A-Z][a-zA-Z\s]{2,30}$'
    lines = resume_text.split('\n')
    has_name = False
    for line in lines[:5]:  # Check first 5 lines
        if re.match(name_pattern, line.strip()):
            has_name = True
            break
   
    if not has_name:
        missing_info.append("Full Name")
   
    # Check for phone number
    phone_pattern = r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    if not re.search(phone_pattern, resume_text):
        missing_info.append("Phone Number")
   
    # Check for email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if not re.search(email_pattern, resume_text):
        missing_info.append("Email Address")
   
    # Check for address/location
    location_keywords = ['address', 'city', 'state', 'location', 'street', 'avenue', 'road']
    has_location = any(keyword in resume_text.lower() for keyword in location_keywords)
    if not has_location:
        missing_info.append("Address/Location")
   
    # Check for experience section
    experience_keywords = ['experience', 'work history', 'employment', 'professional experience']
    has_experience = any(keyword in resume_text.lower() for keyword in experience_keywords)
    if not has_experience:
        missing_info.append("Work Experience section")
   
    # Check for education section
    education_keywords = ['education', 'degree', 'university', 'college', 'school']
    has_education = any(keyword in resume_text.lower() for keyword in education_keywords)
    if not has_education:
        missing_info.append("Education section")
   
    # Check for skills section
    skills_keywords = ['skills', 'technical skills', 'competencies', 'proficiencies']
    has_skills = any(keyword in resume_text.lower() for keyword in skills_keywords)
    if not has_skills:
        missing_info.append("Skills section")
   
    return missing_info

def generate_corrected_resume(resume_text, job_desc):
    """Generate optimized resume with proper formatting"""
    prompt = f"""
    You are an expert resume writer and career consultant.
   
    Here is a job description:
    {job_desc}
   
    Here is the candidate's resume:
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
    return response.text

def save_resume_to_pdf(resume_text):
    """Save resume to PDF with proper formatting"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, topMargin=0.5*inch, bottomMargin=0.5*inch,
                           leftMargin=0.75*inch, rightMargin=0.75*inch)
   
    # Get styles
    styles = getSampleStyleSheet()
   
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor='black'
    )
   
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6,
        spaceBefore=12,
        textColor='black'
    )
   
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        alignment=TA_LEFT
    )
   
    story = []
    lines = resume_text.split('\n')
   
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
           
        # Detect if it's a heading (all caps or contains common section headers)
        section_headers = ['professional summary', 'experience', 'education', 'skills',
                          'core competencies', 'certifications', 'projects', 'awards']
       
        if any(header in line.lower() for header in section_headers) or line.isupper():
            story.append(Paragraph(line, heading_style))
        elif len(story) == 0:  # First line is likely the name
            story.append(Paragraph(line, title_style))
        else:
            story.append(Paragraph(line, normal_style))
   
    doc.build(story)
    buffer.seek(0)
    return buffer

# ----------- Streamlit UI ------------

st.set_page_config(page_title="AI Resume Optimizer", page_icon="📄", layout="wide")

st.title("🚀 AI Resume Optimizer (Gemini API)")
st.markdown("### Optimize your resume to match job descriptions and improve your chances!")

# Create two columns for layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📄 Upload Resume")
    uploaded_resume = st.file_uploader("Upload your Resume (PDF or DOCX)", type=["pdf", "docx"])
   
    if uploaded_resume:
        st.success("Resume uploaded successfully!")

with col2:
    st.subheader("📋 Job Description")
   
    # Job description input method selection
    jd_input_method = st.radio(
        "Choose how to provide job description:",
        ("Paste Job Description", "Job Description URL")
    )
   
    job_desc = ""
   
    if jd_input_method == "Paste Job Description":
        job_desc = st.text_area("Paste the Job Description", height=200)
    else:
        jd_url = st.text_input("Enter Job Description URL")
        if jd_url:
            if st.button("Extract Job Description"):
                with st.spinner("Extracting job description from URL..."):
                    job_desc = extract_jd_from_url(jd_url)
                    if job_desc:
                        st.success("Job description extracted successfully!")
                        # Store in session state to persist
                        st.session_state.extracted_jd = job_desc
       
        # Use extracted JD if available
        if 'extracted_jd' in st.session_state:
            job_desc = st.session_state.extracted_jd
            st.text_area("Extracted Job Description (you can edit if needed):",
                        value=job_desc, height=200, key="extracted_jd_display")

# Main processing section
if uploaded_resume and job_desc:
    st.markdown("---")
   
    if st.button("🔄 Generate Optimized Resume", type="primary", use_container_width=True):
        with st.spinner("Analyzing and optimizing your resume..."):
            # Extract resume text
            try:
                if uploaded_resume.type == "application/pdf":
                    resume_text = extract_text_from_pdf(uploaded_resume)
                elif uploaded_resume.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    resume_text = extract_text_from_docx(uploaded_resume)
                else:
                    st.error("Unsupported file format")
                    st.stop()
               
                # Check resume completeness
                missing_info = check_resume_completeness(resume_text)
               
                if missing_info:
                    st.warning("⚠️ **Missing Information Detected:**")
                    st.markdown("Your resume appears to be missing the following important information:")
                    for info in missing_info:
                        st.markdown(f"• {info}")
                    st.markdown("Please ensure your resume includes all essential information for better optimization.")
                    st.markdown("---")
               
                # Generate corrected resume
                corrected_resume = generate_corrected_resume(resume_text, job_desc)
               
                # Display the optimized resume
                st.success("✅ Resume optimized successfully!")
               
                # Create tabs for different views
                tab1, tab2 = st.tabs(["📖 Preview", "📥 Download"])
               
                with tab1:
                    st.subheader("Optimized Resume Preview")
                    st.text_area("", value=corrected_resume, height=600, disabled=True)
               
                with tab2:
                    # Save to PDF (in memory)
                    pdf_buffer = save_resume_to_pdf(corrected_resume)
                   
                    st.subheader("Download Your Optimized Resume")
                    st.download_button(
                        label="📥 Download Optimized Resume (PDF)",
                        data=pdf_buffer,
                        file_name="optimized_resume.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                   
                    # Option to download as text file too
                    st.download_button(
                        label="📝 Download as Text File",
                        data=corrected_resume,
                        file_name="optimized_resume.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
               
            except Exception as e:
                st.error(f"An error occurred while processing your resume: {str(e)}")
                st.error("Please check your file format and try again.")

else:
    st.info("👆 Please upload your resume and provide a job description to get started!")

# Add footer with tips
st.markdown("---")
st.markdown("### 💡 Tips for Best Results:")
st.markdown("""
- Ensure your resume includes all essential information (name, contact details, experience, education, skills)
- Use a clear, well-formatted resume as input
- Provide a detailed and accurate job description
- Review the optimized resume before using it for applications
- Customize further based on specific company requirements
""")

st.markdown("---")
st.markdown("*Built with Streamlit and Google Gemini AI*")
