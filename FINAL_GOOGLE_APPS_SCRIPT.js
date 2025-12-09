// ============================================================================
// GOOGLE APPS SCRIPT - AI-Powered Resume Customization Integration
// ============================================================================

// Configuration
const CONFIG = {
  keywords: ['DevOps', 'contract', 'hiring', 'job opportunity', 'position', 'role', 'recruitment', 'recruiter', '1099', 'W2', 'immediate', 'urgent'],
  yourName: 'Gokul P K',
  yourPhone: '+1 213 316 8527',
  yourEmail: 'gprasann@usc.edu',

  // Resume customizer API - AI-powered customization
  resumeCustomizerAPI: 'https://web-production-98316.up.railway.app/api/customize-resume',
  downloadAPI: 'https://web-production-98316.up.railway.app/api/download-resume',
  healthCheckAPI: 'https://web-production-98316.up.railway.app/api/health',

  // Role detection keywords
  roleKeywords: {
    devops: ['devops', 'dev ops', 'site reliability', 'sre', 'cloud engineer', 'infrastructure', 'kubernetes', 'docker', 'jenkins', 'ci/cd', 'aws', 'azure', 'gcp', 'terraform', 'ansible'],
    verification: ['verification', 'rtl', 'verify', 'uvm', 'systemverilog', 'testbench', 'simulation', 'functional verification', 'verification engineer', 'fpga', 'asic', 'vlsi'],
    physical_design: ['physical design', 'pd', 'place and route', 'pnr', 'layout', 'floorplan', 'timing closure', 'sta', 'physical designer'],
    dft: ['dft', 'design for test', 'design-for-test', 'bist', 'scan', 'atpg', 'jtag', 'boundary scan', 'dft engineer']
  },

  processedLabel: 'AutoReplied',
  autoSend: true,
  excludeEmails: ['noreply@', 'no-reply@', 'gocoool94leo@gmail.com', 'reddit.com', 'linkedin.com', 'indeed.com', 'glassdoor.com']
};

function processRecruitingEmails() {
  try {
    const scriptProperties = PropertiesService.getScriptProperties();
    let sentRecipients = {};
    try {
      sentRecipients = JSON.parse(scriptProperties.getProperty('sentRecipients') || '{}');
    } catch (e) {
      sentRecipients = {};
    }

    const query = 'newer_than:1d';
    const threads = GmailApp.search(query);
    Logger.log('Found ' + threads.length + ' threads from last 24 hours');

    for (let thread of threads) {
      const messages = thread.getMessages();
      const lastMessage = messages[messages.length - 1];
      const senderEmail = lastMessage.getFrom();
      const subject = lastMessage.getSubject();
      const body = lastMessage.getPlainBody();

      // Check if already processed
      if (thread.getLabels().some(label => label.getName() === CONFIG.processedLabel)) {
        Logger.log('Skipping - already processed: ' + subject);
        continue;
      }

      // Skip excluded emails
      if (CONFIG.excludeEmails.some(excluded => senderEmail.toLowerCase().includes(excluded))) {
        Logger.log('Skipping - excluded email: ' + senderEmail);
        continue;
      }

      // Check if this is a recruiting email
      if (isRecruitingEmail(subject, body, senderEmail)) {
        Logger.log('Processing recruiting email: ' + subject);

        try {
          let recipientEmail, recruiterName;

          // Special handling for Brenda's emails
          if (senderEmail.toLowerCase().includes('brenda@zenspaceit.com')) {
            const recipientInfo = extractRecipientEmail(body, senderEmail);
            recipientEmail = recipientInfo.email;
            recruiterName = recipientInfo.name;
            Logger.log('Email from Brenda - Extracted recipient: ' + recipientEmail);
          } else {
            recipientEmail = senderEmail;
            recruiterName = extractRecruiterName(lastMessage);
            Logger.log('Normal recruiter email - Replying to: ' + recipientEmail);
          }

          // Check if already contacted
          if (sentRecipients[recipientEmail.toLowerCase()]) {
            Logger.log('⚠️ Already sent reply to ' + recipientEmail + ' - skipping');
            thread.addLabel(GmailApp.getUserLabelByName(CONFIG.processedLabel) || GmailApp.createLabel(CONFIG.processedLabel));
            continue;
          }

          const jobTitle = extractJobTitle(subject, body);
          const roleType = detectRoleType(subject, body);

          Logger.log('Detected role type: ' + (roleType || 'none'));
          Logger.log('Recipient: ' + recipientEmail + ' | Recruiter: ' + recruiterName);

          const attachments = [];

          // If role detected, customize resume with AI
          if (roleType) {
            Logger.log('🤖 Customizing resume with AI for: ' + jobTitle);
            const customizedResumeBlob = customizeResumeWithAI(body, roleType);

            if (customizedResumeBlob) {
              attachments.push(customizedResumeBlob);
              Logger.log('✅ AI-customized resume attached');
            } else {
              Logger.log('⚠️ Failed to customize resume');
            }
          } else {
            Logger.log('⚠️ No specific role detected - sending reply without resume');
          }

          // Generate reply
          const replyText = generateReply(recruiterName, jobTitle);

          // Send email
          if (CONFIG.autoSend) {
            if (attachments.length > 0) {
              GmailApp.sendEmail(recipientEmail, 'Re: ' + subject, replyText, { attachments: attachments });
              Logger.log('✅ Sent reply with AI-customized ' + roleType + ' resume to ' + recipientEmail);
            } else {
              GmailApp.sendEmail(recipientEmail, 'Re: ' + subject, replyText);
              Logger.log('✅ Sent reply without resume to ' + recipientEmail);
            }
          } else {
            if (attachments.length > 0) {
              GmailApp.createDraft(recipientEmail, 'Re: ' + subject, replyText, { attachments: attachments });
              Logger.log('✅ Created draft with AI-customized resume');
            } else {
              GmailApp.createDraft(recipientEmail, 'Re: ' + subject, replyText);
              Logger.log('✅ Created draft without resume');
            }
          }

          // Mark as contacted
          sentRecipients[recipientEmail.toLowerCase()] = {
            timestamp: new Date().toISOString(),
            jobTitle: jobTitle,
            roleType: roleType
          };
          scriptProperties.setProperty('sentRecipients', JSON.stringify(sentRecipients));

          // Mark thread as processed
          thread.addLabel(GmailApp.getUserLabelByName(CONFIG.processedLabel) || GmailApp.createLabel(CONFIG.processedLabel));

        } catch (error) {
          Logger.log('❌ Error processing email: ' + error.message);
          Logger.log('Stack: ' + error.stack);
        }
      }
    }
  } catch (error) {
    Logger.log('❌ Error: ' + error.message);
    Logger.log('Stack: ' + error.stack);
  }
}

// Detect role type based on keywords
function detectRoleType(subject, body) {
  const textToSearch = (subject + ' ' + body).toLowerCase();

  // Check each role type (more specific first)
  if (CONFIG.roleKeywords.dft.some(keyword => textToSearch.includes(keyword.toLowerCase()))) {
    return 'dft';
  }
  if (CONFIG.roleKeywords.physical_design.some(keyword => textToSearch.includes(keyword.toLowerCase()))) {
    return 'physical_design';
  }
  if (CONFIG.roleKeywords.verification.some(keyword => textToSearch.includes(keyword.toLowerCase()))) {
    return 'verification';
  }
  if (CONFIG.roleKeywords.devops.some(keyword => textToSearch.includes(keyword.toLowerCase()))) {
    return 'devops';
  }

  return null; // No role detected
}

// AI-powered resume customization via Flask API
function customizeResumeWithAI(jobRequirements, roleType) {
  try {
    Logger.log('🤖 Sending job description to AI customizer...');
    Logger.log('Role type: ' + roleType);
    Logger.log('API URL: ' + CONFIG.resumeCustomizerAPI);

    // Call the AI customization API
    const options = {
      method: 'post',
      payload: {
        requirements: jobRequirements,
        role_type: roleType  // Send role type for base resume selection
      },
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(CONFIG.resumeCustomizerAPI, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();

    Logger.log('API Response Code: ' + responseCode);
    Logger.log('API Response: ' + responseText.substring(0, 200));

    if (responseCode !== 200) {
      Logger.log('❌ API Error: ' + responseText);
      return null;
    }

    const result = JSON.parse(responseText);

    if (result.success && result.filename) {
      Logger.log('✅ Resume customized successfully');
      Logger.log('Filename: ' + result.filename);

      // Download the customized resume
      const downloadUrl = CONFIG.downloadAPI + '/' + encodeURIComponent(result.filename);
      Logger.log('Downloading from: ' + downloadUrl);

      const downloadResponse = UrlFetchApp.fetch(downloadUrl, {
        method: 'get',
        muteHttpExceptions: true
      });

      if (downloadResponse.getResponseCode() === 200) {
        const customizedBlob = downloadResponse.getBlob();
        customizedBlob.setName(result.filename);
        Logger.log('✅ Downloaded AI-customized resume: ' + result.filename);
        return customizedBlob;
      } else {
        Logger.log('❌ Failed to download: ' + downloadResponse.getResponseCode());
        return null;
      }

    } else {
      Logger.log('❌ API returned error: ' + (result.message || 'Unknown error'));
      return null;
    }

  } catch (error) {
    Logger.log('❌ Error in AI customization: ' + error.message);
    Logger.log('Stack: ' + error.stack);
    return null;
  }
}

function isRecruitingEmail(subject, body, senderEmail) {
  const textToSearch = (subject + ' ' + body + ' ' + senderEmail).toLowerCase();
  return CONFIG.keywords.some(keyword => textToSearch.includes(keyword.toLowerCase()));
}

function extractRecipientEmail(body, fallbackEmail) {
  try {
    const emailPattern = /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g;
    const emails = body.match(emailPattern);

    if (emails && emails.length > 0) {
      const validEmails = emails.filter(email => !CONFIG.excludeEmails.some(excluded => email.toLowerCase().includes(excluded)));

      if (validEmails.length > 0) {
        const recipientEmail = validEmails[0];
        return {
          email: recipientEmail,
          name: recipientEmail.split('@')[0]
        };
      }
    }

    return {
      email: fallbackEmail,
      name: fallbackEmail.split('@')[0]
    };

  } catch (error) {
    return {
      email: fallbackEmail,
      name: fallbackEmail.split('@')[0]
    };
  }
}

function extractRecruiterName(message) {
  try {
    const fromHeader = message.getFrom();
    const nameMatch = fromHeader.match(/^([^<]+)</);
    if (nameMatch) return nameMatch[1].trim();
    const body = message.getPlainBody();
    const namePatterns = [/My name is ([A-Za-z\s]+)[.,;]/, /I'm ([A-Za-z\s]+),/, /This is ([A-Za-z\s]+)/];
    for (let pattern of namePatterns) {
      const match = body.match(pattern);
      if (match) return match[1].trim();
    }
    return 'there';
  } catch (error) {
    return 'there';
  }
}

function extractJobTitle(subject, body) {
  try {
    const patterns = [/Job Title[:\s]+([^\n\r]+)/i, /Position[:\s]+([^\n\r]+)/i, /Role[:\s]+([^\n\r]+)/i];
    const textToSearch = subject + ' ' + body;
    for (let pattern of patterns) {
      const match = textToSearch.match(pattern);
      if (match) return match[1].trim().split('\n')[0];
    }
    if (subject.includes('Engineer') || subject.includes('Developer') || subject.includes('DevOps')) {
      return subject.replace(/Re:\s+/i, '').trim();
    }
    return 'the opportunity';
  } catch (error) {
    return 'the opportunity';
  }
}

function generateReply(recruiterName, jobTitle) {
  return 'Hi,\n\nThank you for reaching out and considering my profile.\nPlease find my customized resume attached.\n\nContact Information:\n* Phone: ' + CONFIG.yourPhone + '\n* Email: ' + CONFIG.yourEmail + '\n* LinkedIn: https://www.linkedin.com/in/gokul-pk-4b16b9345/\n* Expected Pay Rate: $60/hour\n* Availability: Immediately available to start\n\nI am available for interviews at your convenience and can be reached during standard business hours.\n\nBest regards,\n' + CONFIG.yourName;
}

function setupTrigger() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'processRecruitingEmails') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  ScriptApp.newTrigger('processRecruitingEmails').timeBased().everyMinutes(10).create();
  Logger.log('✅ Trigger set to run every 10 minutes');
}

function removeTrigger() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'processRecruitingEmails') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  Logger.log('✅ Trigger removed');
}

function viewSentRecipients() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const sentRecipients = JSON.parse(scriptProperties.getProperty('sentRecipients') || '{}');
  Logger.log('Recipients already contacted:');
  Logger.log(JSON.stringify(sentRecipients, null, 2));
  return sentRecipients;
}

function clearSentRecipients() {
  const scriptProperties = PropertiesService.getScriptProperties();
  scriptProperties.deleteProperty('sentRecipients');
  Logger.log('✅ Cleared all recipient tracking data');
}

function testAPIHealth() {
  try {
    Logger.log('Testing API health...');
    const response = UrlFetchApp.fetch(CONFIG.healthCheckAPI, {
      method: 'get',
      muteHttpExceptions: true
    });
    
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    Logger.log('Health Check Response Code: ' + responseCode);
    Logger.log('Health Check Response: ' + responseText);
    
    if (responseCode === 200) {
      const result = JSON.parse(responseText);
      Logger.log('✅ API is healthy!');
      Logger.log('Service: ' + result.service);
      Logger.log('Claude API: ' + result.claude_api);
      return true;
    } else {
      Logger.log('❌ API health check failed');
      return false;
    }
  } catch (error) {
    Logger.log('❌ Error: ' + error.message);
    return false;
  }
}

function testResumeCustomization() {
  try {
    Logger.log('Testing AI resume customization...');
    
    const sampleJobDescription = `
We are looking for a Senior DevOps Engineer with the following skills:
- 5+ years experience with AWS, Azure, or GCP
- Strong knowledge of Docker and Kubernetes
- Experience with CI/CD tools like Jenkins, GitLab CI/CD
- Infrastructure as Code: Terraform, Ansible
- Scripting: Python, Bash
- Monitoring: Prometheus, Grafana
    `;
    
    const roleType = 'devops';
    const customizedBlob = customizeResumeWithAI(sampleJobDescription, roleType);
    
    if (customizedBlob) {
      Logger.log('✅ Test successful!');
      Logger.log('Blob name: ' + customizedBlob.getName());
      Logger.log('Blob size: ' + customizedBlob.getBytes().length + ' bytes');
      return true;
    } else {
      Logger.log('❌ Test failed');
      return false;
    }
  } catch (error) {
    Logger.log('❌ Error: ' + error.message);
    return false;
  }
}

function testProcess() {
  Logger.log('Testing email processing...');
  processRecruitingEmails();
}
