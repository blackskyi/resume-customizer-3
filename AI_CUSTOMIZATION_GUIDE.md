# Resume Customizer 3 - AI-Powered Customization

## ✅ FINAL SOLUTION: Claude AI Customizes Resume for Each Job

### How It Works:

1. **Google Apps Script** detects recruiting email and extracts:
   - Job description
   - Role type (devops, verification, etc.)

2. **Sends to Flask API** with:
   - `requirements`: Full job description text
   - `role_type`: Detected role (devops, verification, physical_design, dft)

3. **Flask App**:
   - Loads base resume content for that role type
   - Uses **Claude AI** to analyze job description
   - **Customizes resume** by:
     - Reordering skills to highlight relevant ones
     - Adding missing keywords from job description
     - Reordering experience bullets to show relevant achievements first
     - Making it ATS-friendly
   - Generates DOCX file
   - Returns filename

4. **Google Apps Script**:
   - Downloads customized DOCX
   - Attaches to email reply

### Key Features:

✅ **AI-Powered** - Claude analyzes each job and customizes accordingly  
✅ **Role-Specific** - Different base resume for DevOps vs Verification  
✅ **ATS-Friendly** - Optimized keywords and formatting  
✅ **Fast** - Customization happens in seconds  
✅ **Professional** - Maintains quality and tone  

### Setup:

1. **Deploy to Railway** with `ANTHROPIC_API_KEY` environment variable
2. **Update Google Apps Script** with corrected code (see below)
3. **Test** with sample job descriptions

### Google Apps Script Updates:

The `customizeResumeViaAPI` function now needs to send `role_type`:

```javascript
const options = {
  method: 'post',
  payload: {
    requirements: jobRequirements,
    role_type: roleType  // IMPORTANT: Must send role type
  },
  muteHttpExceptions: true
};
```

### Example Customization:

**Job Description mentions:**
- Terraform, AWS, Kubernetes, Jenkins, Python

**Claude AI will:**
- Move those skills to the TOP of Technical Skills section
- Reorder experience bullets mentioning those technologies first
- Add any missing but relevant keywords
- Keep all original content, just optimize order

### Base Resumes Included:

1. **devops** - Full DevOps/SRE resume with cloud infrastructure focus
2. **verification** - VLSI/RTL/FPGA verification resume  
3. **physical_design** - (you'll need to add content)
4. **dft** - (you'll need to add content)

### Next Steps:

1. ✅ app.py updated with AI customization
2. ✅ requirements.txt updated
3. ⏳ Deploy to Railway
4. ⏳ Update Google Apps Script
5. ⏳ Test with real job emails

### Testing Locally:

```bash
export ANTHROPIC_API_KEY="your_key"
python app.py

# Test API:
curl -X POST http://localhost:5000/api/customize-resume \
  -F "requirements=Looking for DevOps engineer with Kubernetes and AWS experience" \
  -F "role_type=devops"
```

This solution gives you **intelligent, per-job customization** without needing LaTeX compilation on the server!
