from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os
import re
from io import BytesIO

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['OUTPUT_FOLDER'] = '/tmp/outputs'

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_skills_from_description(job_description):
    """
    Extract skills, tools, and technologies from job description
    """
    if not job_description or job_description.strip() == '':
        return {}

    jd_lower = job_description.lower()

    # Common technical skill patterns
    skill_patterns = {
        'Programming Languages': r'\b(python|java|javascript|typescript|c\+\+|c#|ruby|go|rust|scala|kotlin|swift|r|matlab|perl|tcl|bash|shell|verilog|systemverilog|vhdl)\b',
        'Web Technologies': r'\b(react|angular|vue|node\.?js|express|django|flask|spring|\.net|asp\.net|html|css|jquery|bootstrap|tailwind)\b',
        'Databases': r'\b(sql|mysql|postgresql|mongodb|oracle|redis|cassandra|dynamodb|sqlite|mariadb|elasticsearch)\b',
        'Cloud & DevOps': r'\b(aws|azure|gcp|docker|kubernetes|jenkins|terraform|ansible|ci/cd|git|github|gitlab|bitbucket)\b',
        'Data & ML': r'\b(machine learning|deep learning|tensorflow|pytorch|scikit-learn|pandas|numpy|spark|hadoop|kafka|airflow)\b',
        'Testing & QA': r'\b(junit|pytest|selenium|cypress|jest|mocha|atpg|dft|bist|mbist|lbist|scan|jtag)\b',
        'Methodologies': r'\b(agile|scrum|kanban|devops|tdd|bdd|ci/cd|waterfall)\b',
        'Hardware/Semiconductor Tools': r'\b(tessent|testmax|fastscan|tetramax|dftmax|spyglass|primetime|design compiler|genus|icc|innovus|encounter|calibre|hercules|virtuoso|spectre|hspice|cadence|synopsys|mentor|siemens|xilinx|altera|quartus|vivado)\b',
    }

    extracted_skills = {}

    # Extract skills by pattern
    for category, pattern in skill_patterns.items():
        matches = re.findall(pattern, jd_lower, re.IGNORECASE)
        if matches:
            # Deduplicate and capitalize properly
            unique_skills = list(set(matches))
            extracted_skills[category] = unique_skills

    # Extract requirements/qualifications sections
    requirements = []
    req_patterns = [
        r'(?:requirements?|qualifications?|skills?)[:\s]+([^\n]+(?:\n[^\n]+){0,20})',
        r'(?:must have|required)[:\s]+([^\n]+(?:\n[^\n]+){0,10})',
        r'(?:experience with|proficiency in)[:\s]+([^\n]+(?:\n[^\n]+){0,10})'
    ]

    for pattern in req_patterns:
        matches = re.findall(pattern, job_description, re.IGNORECASE | re.MULTILINE)
        requirements.extend(matches)

    # Extract bullet points (common in job descriptions)
    bullet_points = re.findall(r'[•\-\*]\s*([^\n]+)', job_description)

    # Combine all extracted text
    all_requirements_text = ' '.join(requirements + bullet_points)

    # Extract any mentioned tools/technologies (capitalized words or known acronyms)
    tech_words = re.findall(r'\b[A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*)*\b', all_requirements_text)

    # Comprehensive filter for non-technical words
    non_technical_words = {
        # Articles, prepositions, conjunctions
        'The', 'A', 'An', 'In', 'On', 'At', 'To', 'For', 'Of', 'With', 'By', 'From', 'And', 'Or', 'But', 'Not',
        'This', 'That', 'These', 'Those', 'Will', 'Should', 'Must', 'Can', 'May', 'Has', 'Have', 'Had',
        'Is', 'Are', 'Was', 'Were', 'Be', 'Been', 'Being', 'Do', 'Does', 'Did', 'Done',

        # Time-related words
        'Years', 'Year', 'Months', 'Month', 'Weeks', 'Week', 'Days', 'Day', 'Duration', 'Time',
        'Hours', 'Hour', 'Experience', 'Experienced',

        # Location-related words
        'Location', 'Remote', 'Onsite', 'Hybrid', 'Office', 'City', 'State', 'Country',
        'Santa', 'Clara', 'San', 'Francisco', 'Jose', 'Diego', 'Angeles', 'York', 'Seattle',
        'Austin', 'Boston', 'Denver', 'Portland', 'Chicago', 'Atlanta', 'Dallas', 'Houston',

        # Job-related generic words
        'Job', 'Position', 'Role', 'Candidate', 'Candidates', 'Team', 'Member', 'Members',
        'Company', 'Work', 'Working', 'Works', 'Worked', 'Responsibilities', 'Responsibility',
        'Requirements', 'Requirement', 'Qualifications', 'Qualification', 'Skills', 'Skill',

        # Descriptive words
        'Strong', 'Excellent', 'Good', 'Great', 'Best', 'Better', 'Deep', 'Solid', 'Proven',
        'Ability', 'Abilities', 'Knowledge', 'Understanding', 'Preferred', 'Required', 'Desired',
        'Plus', 'Bonus', 'Nice', 'Including', 'Such', 'Other', 'Various', 'Multiple', 'Several',

        # Action/Status words
        'Conduct', 'Provide', 'Perform', 'Develop', 'Create', 'Build', 'Design', 'Implement',
        'Maintain', 'Support', 'Manage', 'Lead', 'Coordinate', 'Collaborate', 'Communicate',
        'Availability', 'Available', 'Immediately', 'Successful', 'Completion',

        # Degree/Education words
        'Degree', 'Bachelor', 'Masters', 'PhD', 'BS', 'MS', 'BA', 'MA', 'Engineering', 'Science',
        'Computer', 'Electrical', 'Mechanical', 'Software', 'Hardware',

        # Generic terms
        'Thanks', 'Please', 'Note', 'Include', 'Summary', 'Overview', 'Description', 'Details',
        'Information', 'Contact', 'Apply', 'Application', 'Resume', 'Cover', 'Letter'
    }

    # Additional pattern-based filters for non-technical content
    def is_technical_term(word):
        # Filter out words that are clearly non-technical
        if word in non_technical_words:
            return False
        if len(word) < 3:  # Too short
            return False
        if word.lower() in ['inc', 'llc', 'ltd', 'corp', 'corporation']:  # Company suffixes
            return False
        if re.match(r'^[A-Z][a-z]+$', word) and word not in ['Git', 'Rust', 'Go', 'Java', 'Ruby', 'Swift', 'Perl']:
            # Single capitalized word (likely a name/location), unless it's a known language
            return False
        return True

    tech_words = [word for word in tech_words if is_technical_term(word)]

    # Additional known technical terms/tools to look for (case-insensitive)
    known_tech_patterns = r'\b(verilog|systemverilog|vhdl|atpg|dft|bist|mbist|lbist|jtag|scan|testmax|tessent|fastscan|spyglass|lint|cdc|rdc|sta|synthesis|primetime|design compiler|genus|conformal|formality|calibre|icv|hercules|dracula|assura|mentor|cadence|synopsys|siemens|xilinx|altera|fpga|asic|soc|rtl|gls|netlist|sdf|spef|sdcl|upf|cpf)\b'

    additional_tech = re.findall(known_tech_patterns, jd_lower, re.IGNORECASE)
    if additional_tech:
        # Capitalize properly
        tech_words.extend([t.upper() if len(t) <= 4 else t.title() for t in set(additional_tech)])

    if tech_words:
        extracted_skills['Tools & Technologies'] = list(set(tech_words))[:15]  # Limit to top 15

    return extracted_skills


def analyze_gaps(current_resume_path, job_description):
    """
    Analyze gaps between current resume and job requirements
    """
    # Extract skills from job description
    job_tools = extract_skills_from_description(job_description)

    if not job_tools:
        # Fallback to generic professional skills if no job description provided
        job_tools = {
            'Core Skills': ['Communication', 'Problem Solving', 'Team Collaboration', 'Time Management']
        }

    # Read current resume
    doc = Document(current_resume_path)
    resume_text = '\n'.join([para.text for para in doc.paragraphs]).lower()

    # Find missing tools
    missing_tools = {}
    for category, tools in job_tools.items():
        missing = []
        for tool in tools:
            # Check if tool or its key component is in resume
            tool_keywords = str(tool).lower().replace('(', '').replace(')', '').split()
            if not any(keyword in resume_text for keyword in tool_keywords if len(keyword) > 2):
                missing.append(tool)
        if missing:
            missing_tools[category] = missing

    return missing_tools, job_tools

def enhance_resume(input_path, output_path, job_description):
    """
    Enhance resume by adding missing tools and reorganizing skills section
    """
    # Analyze gaps
    missing_tools, all_job_tools = analyze_gaps(input_path, job_description)

    # Load document
    doc = Document(input_path)

    # Find the Key Skills section
    skills_section_index = None
    for i, para in enumerate(doc.paragraphs):
        if 'Key Skills' in para.text or 'Skills' in para.text or 'SKILLS' in para.text.upper():
            skills_section_index = i
            break

    if skills_section_index is None:
        print("Warning: Could not find 'Key Skills' section. Skills will be added at the end.")
        skills_section_index = len(doc.paragraphs) - 1

    # Read existing skills from resume
    existing_skills = {}
    if skills_section_index is not None:
        for i in range(skills_section_index + 1, len(doc.paragraphs)):
            para_text = doc.paragraphs[i].text.strip()
            if not para_text:
                continue
            # Check if it's a new section header (capitalized, no colon in first part)
            if para_text and para_text[0].isupper() and ':' not in para_text[:20] and len(para_text) > 20:
                break
            # Try to parse skill category lines
            if ':' in para_text:
                parts = para_text.split(':', 1)
                if len(parts) == 2:
                    category = parts[0].strip()
                    skills = [s.strip() for s in parts[1].split(',')]
                    existing_skills[category] = skills

    # Merge job requirements with existing skills
    enhanced_skills = {}

    # First, preserve existing skills
    for category, skills in existing_skills.items():
        enhanced_skills[category] = skills

    # Then add missing skills from job description
    for category, tools in all_job_tools.items():
        if category in enhanced_skills:
            # Merge with existing
            for tool in tools:
                tool_str = str(tool).title() if isinstance(tool, str) else str(tool)
                # Check if skill is already there
                if not any(tool_str.lower() in existing.lower() for existing in enhanced_skills[category]):
                    enhanced_skills[category].append(tool_str)
        else:
            # Add new category
            enhanced_skills[category] = [str(tool).title() if isinstance(tool, str) else str(tool) for tool in tools]

    # Find where to insert enhanced skills
    # Remove old skills section content
    paragraphs_to_remove = []
    if skills_section_index is not None:
        for i in range(skills_section_index + 1, len(doc.paragraphs)):
            if doc.paragraphs[i].text.strip() and not doc.paragraphs[i].text.strip().startswith(tuple('ABCDEFGHIJKLMNOPQRSTUVWXYZ')):
                paragraphs_to_remove.append(i)
            elif doc.paragraphs[i].text.strip() and doc.paragraphs[i].text.strip()[0].isupper() and ':' not in doc.paragraphs[i].text[:20]:
                break

    # Create new document with enhanced skills
    new_doc = Document()

    # Copy all paragraphs up to skills section
    for i in range(skills_section_index + 1):
        new_para = new_doc.add_paragraph()
        new_para.text = doc.paragraphs[i].text
        new_para.style = doc.paragraphs[i].style
        # Copy formatting
        if doc.paragraphs[i].runs:
            new_para.runs[0].bold = doc.paragraphs[i].runs[0].bold
            new_para.runs[0].font.size = doc.paragraphs[i].runs[0].font.size

    # Add enhanced skills
    for category, skills in enhanced_skills.items():
        skill_para = new_doc.add_paragraph()
        skill_para.add_run(f"{category}: ").bold = True
        skill_para.add_run(', '.join(skills))
        skill_para.style = 'Normal'

    # Copy remaining content (skip old skills)
    copy_remaining = False
    for i in range(skills_section_index + 1, len(doc.paragraphs)):
        if copy_remaining or (doc.paragraphs[i].text.strip() and
                              doc.paragraphs[i].text.strip()[0].isupper() and
                              ':' not in doc.paragraphs[i].text[:30] and
                              i not in paragraphs_to_remove):
            copy_remaining = True
            if i not in paragraphs_to_remove:
                new_para = new_doc.add_paragraph()
                new_para.text = doc.paragraphs[i].text
                new_para.style = doc.paragraphs[i].style

    # Save enhanced resume
    new_doc.save(output_path)

    return new_doc, missing_tools

def create_gap_analysis_report(input_path, job_description):
    """
    Create a detailed gap analysis report
    """
    missing_tools, all_job_tools = analyze_gaps(input_path, job_description)

    report = []
    report.append("="*70)
    report.append("GAP ANALYSIS: YOUR RESUME vs. JOB REQUIREMENTS")
    report.append("="*70)
    report.append("")

    report.append("-"*70)
    report.append("SKILLS IDENTIFIED FROM JOB DESCRIPTION:")
    report.append("-"*70)
    report.append("")

    for category, tools in all_job_tools.items():
        report.append(f"\n{category}:")
        for tool in tools[:10]:  # Limit to first 10 per category
            report.append(f"  • {tool}")

    report.append("")
    report.append("-"*70)
    report.append("SKILLS/TOOLS MISSING FROM YOUR RESUME:")
    report.append("-"*70)
    report.append("")

    if missing_tools:
        for category, tools in missing_tools.items():
            report.append(f"\n{category}:")
            for tool in tools:
                report.append(f"  • {tool}")
    else:
        report.append("Great! Your resume already contains most of the required skills.")

    report.append("")
    report.append("="*70)
    report.append("RECOMMENDATIONS:")
    report.append("="*70)
    report.append("")

    recommendations = [
        "Review the enhanced resume and verify the added skills match your experience",
        "Add specific project examples demonstrating these skills",
        "Customize the professional summary to highlight key technologies",
        "Quantify your achievements where possible (e.g., improved performance by X%)",
        "Ensure your experience section demonstrates the listed skills in action",
        "Proofread for consistency in terminology and formatting"
    ]

    for i, rec in enumerate(recommendations, 1):
        report.append(f"{i}. {rec}")

    report.append("")
    report.append("="*70)

    return '\n'.join(report)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/enhance', methods=['POST'])
def enhance():
    if 'resume' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('index'))

    file = request.files['resume']
    job_description = request.form.get('job_description', '').strip()

    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))

    if not job_description:
        flash('Please provide a job description')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        # Generate output filename
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_Customized.docx"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        try:
            # Enhance the resume
            enhanced_doc, missing_tools = enhance_resume(input_path, output_path, job_description)

            # Create gap analysis report
            gap_report = create_gap_analysis_report(input_path, job_description)

            # Clean up input file
            os.remove(input_path)

            return render_template('result.html',
                                   output_filename=output_filename,
                                   missing_tools=missing_tools,
                                   gap_report=gap_report)
        except Exception as e:
            flash(f'Error processing resume: {str(e)}')
            if os.path.exists(input_path):
                os.remove(input_path)
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a .docx file')
        return redirect(url_for('index'))

@app.route('/download/<filename>')
def download(filename):
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(output_path):
        return send_file(output_path, as_attachment=True)
    else:
        flash('File not found')
        return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
