from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import os
import re
import subprocess
import shutil
from pathlib import Path
from anthropic import Anthropic

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['OUTPUT_FOLDER'] = '/tmp/outputs'
app.config['LATEX_TEMPLATES_FOLDER'] = os.path.join(os.path.dirname(__file__), 'latex_templates')

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['LATEX_TEMPLATES_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'tex', 'docx'}

# Base LaTeX templates for different roles (stored as filenames)
LATEX_TEMPLATES = {
    'verification': 'verification_fpga_rtl_resume.tex',
    'devops': 'devops_resume.tex',
    'physical_design': 'physical_design_resume.tex',
    'dft': 'dft_resume.tex'
}

# Initialize Claude API client
claude_client = None
api_key = os.environ.get('ANTHROPIC_API_KEY')
if api_key:
    try:
        claude_client = Anthropic(api_key=api_key)
        print('✅ Claude API initialized successfully')
    except Exception as e:
        print(f'⚠️ Claude API initialization failed: {e}')
else:
    print('⚠️ ANTHROPIC_API_KEY not set - will use regex-only extraction')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_skills_with_claude(job_description):
    """
    Use Claude API to intelligently extract technical skills from job description
    """
    if not claude_client:
        print('⚠️ Claude API not available, falling back to regex extraction')
        return None

    try:
        prompt = f"""You are an expert technical recruiter. Extract ALL technical skills, tools, technologies, and keywords from this job description.

Job Description:
{job_description}

Extract and categorize the technical requirements into these categories:
- Programming Languages (e.g., Python, Java, .NET, C#, etc.)
- Cloud Platforms (e.g., AWS, Azure, GCP)
- DevOps & CI/CD Tools (e.g., Jenkins, GitLab CI/CD, GitHub Actions, Pipeline tools)
- Infrastructure as Code (e.g., Terraform, Ansible, CloudFormation)
- Containers & Orchestration (e.g., Docker, Kubernetes)
- Databases (e.g., PostgreSQL, MongoDB, DynamoDB)
- Monitoring & Observability (e.g., Prometheus, Grafana, DataDog)
- Security Tools (e.g., Security Integration, Secrets Management)
- AI/ML Technologies (e.g., AI/ML, Machine Learning, TensorFlow)
- Operating Systems (e.g., Linux, Windows Administration)
- Build & Deployment (e.g., Build Automation, Deployment Automation, Maven, Gradle)
- Other Technical Skills

IMPORTANT:
- Extract EXACT phrases from the job description (e.g., if it says ".NET Build", extract ".NET Build" not just ".NET")
- Include compound terms (e.g., "GitLab CI/CD", "Pipeline Mastery", "Security Integration")
- Focus on TECHNICAL keywords only, ignore soft skills
- Include years of experience requirements with the skill (e.g., "4+ yrs Terraform")

Return ONLY a JSON object in this format:
{{
  "Programming Languages": ["skill1", "skill2"],
  "Cloud Platforms": ["skill1"],
  "DevOps & CI/CD Tools": ["skill1", "skill2"],
  ...
}}"""

        response = claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        content = response.content[0].text.strip()

        # Extract JSON from response
        import json
        # Try to find JSON in response
        json_start = content.find('{')
        json_end = content.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            extracted_skills = json.loads(json_str)
            print(f'✅ Claude API extracted {sum(len(v) for v in extracted_skills.values())} skills')
            return extracted_skills
        else:
            print('⚠️ Could not parse JSON from Claude response')
            return None

    except Exception as e:
        print(f'⚠️ Claude API error: {e}')
        return None

def extract_skills_from_description(job_description):
    """
    Extract skills, tools, and technologies from job description
    Uses Claude API for intelligent extraction, falls back to regex
    """
    if not job_description or job_description.strip() == '':
        return {}

    # Try Claude API first for intelligent extraction
    if claude_client:
        claude_skills = extract_skills_with_claude(job_description)
        if claude_skills:
            return claude_skills

    # Fall back to regex-based extraction
    print('ℹ️ Using regex-based skill extraction')
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
        'California', 'Texas', 'Washington', 'Oregon', 'Colorado', 'Massachusetts',

        # Job-related generic words
        'Job', 'Position', 'Role', 'Candidate', 'Candidates', 'Team', 'Member', 'Members',
        'Company', 'Work', 'Working', 'Works', 'Worked', 'Responsibilities', 'Responsibility',
        'Requirements', 'Requirement', 'Qualifications', 'Qualification', 'Skills', 'Skill',
        'Description', 'Descriptions',

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
        'Information', 'Contact', 'Apply', 'Application', 'Resume', 'Cover', 'Letter',

        # Acronyms that are not technical
        'GLS', 'USA', 'US'
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

    # Modify the existing skills section in-place to preserve all formatting
    if skills_section_index is not None:
        # Find existing skill lines and update them
        skill_lines_indices = []
        for i in range(skills_section_index + 1, len(doc.paragraphs)):
            para_text = doc.paragraphs[i].text.strip()
            if not para_text:
                continue
            # Check if we've reached the next major section
            if para_text and para_text[0].isupper() and ':' not in para_text[:20] and len(para_text) > 20:
                break
            # This is a skill line
            if ':' in para_text:
                skill_lines_indices.append(i)

        # Update existing skill lines and track how many we've used
        skills_list = list(enhanced_skills.items())

        for idx, line_idx in enumerate(skill_lines_indices):
            if idx < len(skills_list):
                category, skills = skills_list[idx]
                para = doc.paragraphs[line_idx]

                # Clear existing content
                para.clear()

                # Add new content with formatting
                run1 = para.add_run(f"{category}: ")
                run1.bold = True
                run2 = para.add_run(', '.join(skills))

        # If we have more skills than existing lines, add new paragraphs
        if len(skills_list) > len(skill_lines_indices):
            # Find where to insert (after last skill line or after header)
            insert_after_idx = skill_lines_indices[-1] if skill_lines_indices else skills_section_index

            for idx in range(len(skill_lines_indices), len(skills_list)):
                category, skills = skills_list[idx]

                # Insert paragraph at the right position
                new_para = doc.add_paragraph()
                run1 = new_para.add_run(f"{category}: ")
                run1.bold = True
                run2 = new_para.add_run(', '.join(skills))

                # Move it to the correct position
                para_element = new_para._element
                para_element.getparent().remove(para_element)
                doc.paragraphs[insert_after_idx]._element.addnext(para_element)
                insert_after_idx += 1

    # Save enhanced resume (preserves all original formatting, layout, fonts, spacing)
    doc.save(output_path)

    return doc, missing_tools

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

# ============================================================================
# API ENDPOINTS FOR GOOGLE APPS SCRIPT INTEGRATION
# ============================================================================

@app.route('/api/customize-resume', methods=['POST'])
def api_customize_resume():
    """
    API endpoint for Google Apps Script to customize resume
    Expected: multipart/form-data with 'resume' file and 'requirements' text
    Returns: JSON with success status and filename
    """
    try:
        # Check if resume file is provided
        if 'resume' not in request.files:
            return {'success': False, 'message': 'No resume file provided'}, 400

        file = request.files['resume']
        job_requirements = request.form.get('requirements', '').strip()

        if file.filename == '':
            return {'success': False, 'message': 'No file selected'}, 400

        if not job_requirements:
            return {'success': False, 'message': 'No job requirements provided'}, 400

        if not allowed_file(file.filename):
            return {'success': False, 'message': 'Invalid file type. Only .docx files are allowed'}, 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        # Generate output filename
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_Customized.docx"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        # Enhance the resume
        enhanced_doc, missing_tools = enhance_resume(input_path, output_path, job_requirements)

        # Clean up input file
        os.remove(input_path)

        # Return success with file path
        return {
            'success': True,
            'message': 'Resume customized successfully',
            'filePath': output_filename,
            'filename': output_filename
        }, 200

    except Exception as e:
        # Clean up if there's an error
        if 'input_path' in locals() and os.path.exists(input_path):
            os.remove(input_path)
        
        return {'success': False, 'message': f'Error: {str(e)}'}, 500


@app.route('/api/download-resume/<filename>', methods=['GET'])
def api_download_resume(filename):
    """
    API endpoint to download a customized resume
    Returns the file directly
    """
    try:
        # Sanitize filename for security
        safe_filename = secure_filename(filename)
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], safe_filename)
        
        if os.path.exists(output_path):
            return send_file(
                output_path,
                as_attachment=True,
                download_name=safe_filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        else:
            return {'success': False, 'message': 'File not found'}, 404
            
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}, 500


@app.route('/api/health', methods=['GET'])
def api_health():
    """
    Health check endpoint
    """
    return {
        'status': 'healthy',
        'service': 'resume-customizer-3',
        'claude_api': 'enabled' if claude_client else 'disabled'
    }, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
