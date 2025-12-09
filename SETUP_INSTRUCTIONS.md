# Resume Customizer 3 - LaTeX Version Setup Instructions

## Overview
This version of the resume customizer uses LaTeX templates instead of DOCX files for better formatting control. The system will:
1. Take a job description as input
2. Use Claude AI to customize your LaTeX resume
3. Compile it to a PDF
4. Return the PDF for download or email attachment

## Files Structure

```
resume-customizer-3/
├── app.py                          # Main Flask application (LaTeX-based)
├── latex_templates/                # LaTeX resume templates
│   ├── verification_fpga_rtl_resume.tex  # For verification/FPGA/RTL jobs
│   ├── devops_resume.tex           # For DevOps jobs
│   ├── physical_design_resume.tex  # For Physical Design jobs
│   └── dft_resume.tex              # For DFT jobs
├── templates/
│   ├── index.html                  # Web interface
│   └── result.html                 # Results page
├── requirements.txt                # Python dependencies
└── Procfile                        # For Railway deployment
```

## Required Changes

### 1. Update `requirements.txt`
Remove `python-docx` and keep only:
```
Flask==3.0.0
Werkzeug==3.0.1
gunicorn==21.2.0
anthropic==0.39.0
```

### 2. Update `Procfile` to install LaTeX
Railway needs to install `pdflatex`:
```
web: apt-get update && apt-get install -y texlive-latex-base texlive-latex-extra && gunicorn app:app
```

OR use a buildpack approach - create a file named `apt.txt`:
```
texlive-latex-base
texlive-latex-extra
texlive-fonts-recommended
```

### 3. Create LaTeX Templates

You provided the verification template. You'll need to create similar templates for other roles:
- `devops_resume.tex`
- `physical_design_resume.tex`  
- `dft_resume.tex`

## How It Works

### API Flow:
1. Google Apps Script sends:
   - `requirements`: Job description text
   - `role_type`: One of ['verification', 'devops', 'physical_design', 'dft']

2. Flask app:
   - Loads appropriate LaTeX template
   - Uses Claude AI to customize the "Key Skills" section
   - Compiles LaTeX to PDF
   - Returns PDF filename

3. Google Apps Script:
   - Downloads the PDF
   - Attaches to email

## Google Apps Script Updates

The Apps Script needs to send `role_type` parameter. Update the `customizeResumeViaAPI` function:

```javascript
const options = {
  method: 'post',
  payload: {
    requirements: jobRequirements,
    role_type: roleType  // ADD THIS LINE
  },
  muteHttpExceptions: true
};
```

## Testing Locally

1. Install LaTeX on your Mac:
```bash
brew install --cask mactex-no-gui
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variable:
```bash
export ANTHROPIC_API_KEY="your_key_here"
```

4. Run the app:
```bash
python app.py
```

5. Test API:
```bash
curl -X POST http://localhost:5000/api/health
```

## Deployment to Railway

1. Make sure all LaTeX templates are in `latex_templates/` folder
2. Update requirements.txt (remove python-docx)
3. Add buildpack for LaTeX or update Procfile
4. Deploy to Railway
5. Add ANTHROPIC_API_KEY environment variable in Railway dashboard

## Alternative Simpler Approach

If LaTeX installation on Railway is problematic, you could:
1. Pre-compile PDFs for each role type
2. Store them in Google Drive
3. Apps Script downloads appropriate PDF based on role type
4. No customization needed on server

Would you like me to implement that simpler approach instead?
