# Resume Customizer 3

AI-Powered Resume Customization Tool

## Features

- **Universal Job Description Analysis**: Works with any job description from any industry
- **Smart Skill Extraction**: Automatically identifies required skills, technologies, and tools from job descriptions
- **Intelligent Resume Enhancement**: Adds missing skills while preserving your existing ones
- **Gap Analysis Reports**: Generates detailed reports showing what skills were added and why
- **Dynamic Categorization**: Organizes skills into relevant categories based on the job description
- **Universal Application**: Works for tech, engineering, business, healthcare, and any other field

## Technology Stack

- Python 3.11
- Flask 3.0
- python-docx for Word document processing
- Deployed on Railway

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open browser to `http://localhost:5000`

## Deployment

This application is configured for deployment on Railway with automatic deployments from GitHub.

## How It Works

1. **Paste the Job Description**: Copy the complete job posting into the text area
2. **Upload Your Resume**: Upload your current resume in .docx format
3. **AI Analysis**: The tool extracts skills, technologies, and requirements from the job description using advanced pattern matching
4. **Smart Enhancement**: Missing skills are intelligently added to your resume while preserving existing ones
5. **Download Results**: Get your customized resume and a detailed gap analysis report

## Example Use Cases

- **Software Engineers**: Extracts programming languages, frameworks, cloud technologies, databases
- **Data Scientists**: Identifies ML libraries, data tools, statistical methods
- **Product Managers**: Recognizes methodologies, tools, collaboration frameworks
- **Engineers**: Detects technical tools, software, industry-specific technologies
- **Any Role**: Universal skill extraction works across all industries
