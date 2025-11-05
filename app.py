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

def analyze_gaps(current_resume_path, job_description):
    """
    Analyze gaps between current resume and job requirements
    """
    # Tools mentioned in job description
    job_tools = {
        'DFT Tools': [
            'Siemens Tessent SSN (Streaming Scan Network)',
            'Siemens Tessent ATPG',
            'Tessent Scan Compression',
            'Tessent FastScan',
            'Tessent Shell'
        ],
        'Design & Verification': [
            'Verilog',
            'SystemVerilog',
            'Logic Synthesis',
            'Static Timing Analysis (STA)',
            'RTL Simulation',
            'Gate-level Simulation',
            'SDF (Standard Delay Format)'
        ],
        'Scripting': [
            'Perl',
            'Tcl',
            'Python',
            'Shell scripting (Bash)'
        ],
        'ATPG Types': [
            'Stuck-At Fault ATPG',
            'At-Speed ATPG',
            'Path-Delay ATPG',
            'Transition Fault ATPG'
        ],
        'Environment': [
            'Linux/Unix',
            'Cross-functional team collaboration',
            'Global team coordination'
        ]
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
            tool_keywords = tool.lower().replace('(', '').replace(')', '').split()
            if not any(keyword in resume_text for keyword in tool_keywords if len(keyword) > 3):
                missing.append(tool)
        if missing:
            missing_tools[category] = missing

    return missing_tools, job_tools

def enhance_resume(input_path, output_path):
    """
    Enhance resume by adding missing tools and reorganizing skills section
    """
    # Analyze gaps
    missing_tools, all_job_tools = analyze_gaps(input_path, None)

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

    # Enhanced skills structure based on job requirements
    enhanced_skills = {
        'DFT Methodologies': [
            'DFT implementation',
            'Hierarchical DFT flow',
            'Scan chain design',
            'Test compression (EDT, OPMISR)',
            'Fault simulation',
            'IP and SoC-level DFT',
            'Pattern retargeting',
            'Scan timing analysis'
        ],
        'Test Methodologies': [
            'ATPG (Stuck-At, At-Speed, Path-Delay, Transition Fault)',
            'MBIST (Memory BIST)',
            'Logic BIST',
            'Scan insertion',
            'Test point insertion',
            'Boundary Scan (JTAG)'
        ],
        'DFT Tools & Platforms': [
            'Siemens Tessent (ATPG, FastScan, Shell)',
            'Siemens Tessent SSN (Streaming Scan Network)',
            'Siemens Tessent Scan Compression',
            'Synopsys Tetramax',
            'Synopsys DFTMAX',
            'ATE platforms (pattern generation & validation)'
        ],
        'Design & Verification': [
            'Verilog/SystemVerilog RTL design',
            'Logic Synthesis',
            'Static Timing Analysis (STA) in test mode',
            'RTL/Gate-level/SDF simulation',
            'Design quality checks (lint, CDC)',
            'SoC integration & chip-level flows'
        ],
        'Programming & Scripting': [
            'Python (automation, test flows)',
            'Tcl (tool scripting)',
            'Perl (pattern manipulation)',
            'Bash/Shell scripting',
            'Linux/Unix environment'
        ],
        'Additional Technical Skills': [
            'Complex chip-level DFT flow development',
            'Pattern retargeting and simulation',
            'Cross-functional team collaboration',
            'Global team coordination',
            'Silicon bring-up support',
            'Test engineering collaboration'
        ]
    }

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

def create_gap_analysis_report(input_path):
    """
    Create a detailed gap analysis report
    """
    missing_tools, all_job_tools = analyze_gaps(input_path, None)

    report = []
    report.append("="*70)
    report.append("GAP ANALYSIS: YOUR RESUME vs. JOB REQUIREMENTS")
    report.append("="*70)
    report.append("")

    report.append("-"*70)
    report.append("CRITICAL TOOLS TO HIGHLIGHT (Top Priority):")
    report.append("-"*70)
    report.append("")

    critical_tools = [
        "Siemens Tessent ATPG",
        "Siemens Tessent SSN (Streaming Scan Network)",
        "Pattern retargeting flows",
        "Chip-level DFT flow development"
    ]

    for tool in critical_tools:
        report.append(f"  ☑ {tool}")

    report.append("")
    report.append("-"*70)
    report.append("TOOLS/SKILLS GAPS IDENTIFIED:")
    report.append("-"*70)
    report.append("")

    for category, tools in missing_tools.items():
        report.append(f"\n{category}:")
        for tool in tools:
            report.append(f"  • {tool}")

    report.append("")
    report.append("="*70)
    report.append("RECOMMENDATIONS:")
    report.append("="*70)
    report.append("")

    recommendations = [
        "Emphasize your Tessent experience prominently in summary",
        "Add specific examples of SSN (Streaming Scan Network) work",
        "Highlight pattern retargeting experience",
        "Mention chip-level flow development projects",
        "Include examples of cross-functional team collaboration",
        "Add specific ATPG types experience (At-Speed, Path-Delay)",
        "Mention any global team coordination experience",
        "Highlight Linux scripting expertise (Perl, Tcl, Python)"
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

    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        # Generate output filename
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_Enhanced.docx"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        try:
            # Enhance the resume
            enhanced_doc, missing_tools = enhance_resume(input_path, output_path)

            # Create gap analysis report
            gap_report = create_gap_analysis_report(input_path)

            # Clean up input file
            os.remove(input_path)

            return render_template('result.html',
                                   output_filename=output_filename,
                                   missing_tools=missing_tools,
                                   gap_report=gap_report)
        except Exception as e:
            flash(f'Error processing resume: {str(e)}')
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
