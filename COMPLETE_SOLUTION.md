# COMPLETE SOLUTION: Resume Customizer with LaTeX

## The Problem
- Original app used DOCX which doesn't preserve formatting well
- You want to use LaTeX templates for perfect formatting
- Railway deployment can't easily compile LaTeX
- Need to send PDF attachments via Google Apps Script

## The Solution: Pre-compiled PDFs

### Step 1: Install LaTeX on Your Mac (one-time)
```bash
brew install --cask mactex-no-gui
# Wait 10-15 minutes for install
```

### Step 2: Compile Your LaTeX Templates to PDF

```bash
cd /Users/gokul/resume-customizer-3/latex_templates

# Compile verification resume
pdflatex verification_fpga_rtl_resume.tex
pdflatex verification_fpga_rtl_resume.tex  # Run twice for references

# Compile devops resume  
pdflatex devops_resume.tex
pdflatex devops_resume.tex

# You'll create these later for other roles:
# pdflatex physical_design_resume.tex
# pdflatex dft_resume.tex
```

### Step 3: Create Static Folder and Move PDFs

```bash
cd /Users/gokul/resume-customizer-3
mkdir -p static/resumes

# Move PDFs
mv latex_templates/*.pdf static/resumes/

# Rename for clarity
cd static/resumes
mv verification_fpga_rtl_resume.pdf Gokul_PK_Verification_Resume.pdf
mv devops_resume.pdf Gokul_PK_DevOps_Resume.pdf
```

### Step 4: Update Google Apps Script

The Apps Script should store base resume FILENAMES instead of Google Drive files:

```javascript
const CONFIG = {
  // ... other config ...
  
  // Base resume file names - these match the PDF filenames in static/resumes/
  baseResumes: {
    devops: 'Gokul_PK_DevOps_Resume.pdf',
    verification: 'Gokul_PK_Verification_Resume.pdf',
    physical_design: 'Gokul_PK_Physical_Design_Resume.pdf',
    dft: 'Gokul_PK_DFT_Resume.pdf'
  },
  
  // API endpoints
  resumeDownloadAPI: 'https://web-production-98316.up.railway.app/static/resumes',
};
```

### Step 5: Update Apps Script `customizeResumeViaAPI` Function

```javascript
function customizeResumeViaAPI(jobRequirements, roleType) {
  try {
    const resumeFileName = CONFIG.baseResumes[roleType];
    
    if (!resumeFileName) {
      Logger.log('ERROR: No resume configured for role type: ' + roleType);
      return null;
    }
    
    Logger.log('Downloading pre-compiled ' + roleType + ' resume: ' + resumeFileName);
    
    // Download the PDF directly from static folder
    const downloadUrl = CONFIG.resumeDownloadAPI + '/' + encodeURIComponent(resumeFileName);
    Logger.log('Downloading from: ' + downloadUrl);
    
    const downloadOptions = {
      method: 'get',
      muteHttpExceptions: true
    };
    
    const downloadResponse = UrlFetchApp.fetch(downloadUrl, downloadOptions);
    const downloadResponseCode = downloadResponse.getResponseCode();
    
    Logger.log('Download Response Code: ' + downloadResponseCode);
    
    if (downloadResponseCode === 200) {
      const resumeBlob = downloadResponse.getBlob();
      resumeBlob.setName(resumeFileName);
      Logger.log('✅ Downloaded resume: ' + resumeFileName);
      return resumeBlob;
    } else {
      Logger.log('Failed to download resume. Status: ' + downloadResponseCode);
      return null;
    }
    
  } catch (error) {
    Logger.log('Error downloading resume: ' + error.message);
    return null;
  }
}
```

### Step 6: Deploy to Railway

1. Commit and push:
```bash
cd /Users/gokul/resume-customizer-3
git add .
git commit -m "Add pre-compiled PDF resumes"
git push
```

2. Railway will automatically deploy
3. PDFs will be accessible at: `https://web-production-98316.up.railway.app/static/resumes/Gokul_PK_DevOps_Resume.pdf`

## Benefits of This Approach

✅ **Perfect Formatting** - LaTeX-compiled PDFs look professional  
✅ **Fast** - No server-side compilation needed  
✅ **Simple Deployment** - Just static files  
✅ **Reliable** - No complex dependencies  
✅ **Easy Updates** - Just recompile LaTeX and replace PDF  

## How to Update a Resume

1. Edit the `.tex` file in `latex_templates/`
2. Compile: `pdflatex devops_resume.tex`
3. Move to static: `mv devops_resume.pdf ../static/resumes/Gokul_PK_DevOps_Resume.pdf`
4. Commit and push to Railway

## Current Status

You have:
- ✅ `verification_fpga_rtl_resume.tex` - Created
- ✅ `devops_resume.tex` - Created  
- ❌ `physical_design_resume.tex` - Need to create
- ❌ `dft_resume.tex` - Need to create

## Next Steps

1. Install MacTeX: `brew install --cask mactex-no-gui`
2. Compile existing templates to PDF
3. Create `static/resumes/` folder
4. Move PDFs there
5. Update Google Apps Script  
6. Test locally
7. Deploy to Railway

Would you like me to help with any specific step?
