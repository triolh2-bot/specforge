# 🔓 HRForge - HR Automation Services

## Email-Based Candidate Management System

Replace full HR functions with AI-powered email automation.

---

## 🎯 Service Tiers

### Tier 1: Email Automation Lite ($149/month)
- Automated candidate responses
- Interview scheduling via email
- Status updates to candidates
- Template-based communication

### Tier 2: Full HR Automation ($399/month)
- Everything in Lite
- Candidate screening automation
- Offer letter generation
- Onboarding email sequences
- HR policy compliance

### Tier 3: Enterprise ($799/month)
- Everything in Full
- Multi-channel recruitment (Email + WhatsApp + SMS)
- Analytics dashboard
- Team collaboration
- Custom integrations

---

## 📧 Email Workflows

### 1. Application Received

```
Trigger: New email to careers@company.com

Actions:
├── Acknowledge receipt (auto-reply)
├── Parse resume/CV
├── Extract candidate info
├── Create candidate profile
├── Score against job requirements
└── Forward to hiring manager
```

**Templates:**
- Acknowledgment email
- Next steps notification
- Rejection email (if not qualified)

---

### 2. Interview Scheduling

```
Trigger: Candidate passes screening

Actions:
├── Send interview invitation
├── Include available time slots
├── Calendar invite attachment
├── Reminder 24h before
├── Collect prerequisites
└── Confirm attendance
```

**Templates:**
- Initial interview invite
- Technical assessment link
- Final round invitation
- Interview reminder

---

### 3. Offer & Onboarding

```
Trigger: Candidate selected

Actions:
├── Send offer letter
├── Collect documents
├── Background check initiation
├── Send onboarding info
├── First day instructions
└── Welcome series (Day 1, 7, 30)
```

**Templates:**
- Offer letter
- Document collection
- Onboarding welcome
- First day checklist

---

### 4. Rejection/Follow-up

```
Trigger: Candidate not selected OR no response

Actions:
├── Send rejection (personalized)
├── Keep in talent pool
├── Future opportunity notification
└── Survey (optional)
```

**Templates:**
- Rejection after interview
- Rejection after final round
- Talent pool notification

---

## 🔧 Technical Implementation

### Email Integration

| Provider | Use |
|----------|-----|
| Gmail API | Primary (recommended) |
| Outlook API | Enterprise clients |
| IMAP/SMTP | Generic fallback |

### Automation Triggers

| Event | Action |
|-------|--------|
| Email received | Parse + classify |
| Resume attached | Extract + score |
| Schedule confirmed | Add to calendar |
| Offer accepted | Start onboarding |
| Offer rejected | Pipeline update |

### AI Processing

| Function | Model |
|----------|-------|
| Resume parsing | GPT-4 / Claude |
| Response generation | GPT-4 |
| Candidate scoring | Custom classifier |
| Sentiment analysis | Claude |

---

## 📊 Features

### Candidate Management

- [x] Resume parsing (PDF, DOCX)
- [x] Candidate database
- [x] Application tracking
- [x] Status pipeline (Applied → Screen → Interview → Offer → Hired)
- [x] Notes & comments
- [x] Activity timeline

### Email Automation

- [x] Auto-reply rules
- [x] Template variables
- [x] Scheduled sends
- [x] Bounce handling
- [x] Unsubscribe management
- [x] Attachment handling

### Scheduling

- [x] Calendar integration
- [x] Time zone handling
- [x] Availability detection
- [x] Reminder automation
- [x] Reschedule handling

### Reporting

- [x] Response time metrics
- [x] Conversion rates
- [x] Source tracking
- [x] Time-to-hire
- [x] Email engagement

---

## 🎯 NEW: WhatsApp Integration (v2.0)

### Supported Actions

| Action | Description |
|--------|-------------|
| Send interview reminders | WhatsApp message 24h before |
| Quick status updates | "Your application is under review" |
| Schedule confirmations | One-click confirm via WhatsApp |
| Offer notifications | Send offer letters via WhatsApp |

### Setup

```bash
# Configure WhatsApp Business API
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_TOKEN=your_access_token
```

### Message Templates

```
Interview Reminder:
"Hi {name}, reminder: Your interview for {position} is tomorrow at {time}. 
Reply C to confirm or R to reschedule."

Application Status:
"Hi {name}, great news! Your application for {position} has moved to the 
next round. We'll be in touch soon with interview details."
```

---

## 📱 NEW: SMS Notifications (v2.0)

### Use Cases

- Urgent interview changes
- Final offer notifications
- Emergency broadcasts

### Providers

| Provider | Setup |
|----------|-------|
| Twilio | Set TWILIO_SID, TWILIO_AUTH_TOKEN |
| Vonage | Set VONAGE_API_KEY |

---

## 🤖 AI-Powered Features (v2.0)

### Candidate Matching

```python
# Score candidate against job requirements
def match_candidate(resume_text, job_requirements):
    # Use embedding similarity
    resume_embedding = get_embedding(resume_text)
    job_embedding = get_embedding(job_requirements)
    similarity = cosine_similarity(resume_embedding, job_embedding)
    return similarity * 100  # Percentage match
```

### Automatic Qualification

- Score resume against job description
- Flag missing required skills
- Highlight experience matches
- Generate screening questions

### Response Generation

- Personalized follow-up emails
- Interview confirmation templates
- Rejection letters (keep in talent pool)

---

## 📈 Analytics Dashboard (v2.0)

### Key Metrics

| Metric | Description |
|--------|-------------|
| Time to Hire | Days from apply to offer |
| Conversion Rate | % of candidates at each stage |
| Source Effectiveness | Where best candidates come from |
| Response Time | Avg time to respond to applicants |
| Offer Acceptance Rate | % of offers accepted |

### Charts

- Funnel visualization (Applied → Screen → Interview → Offer → Hired)
- Source breakdown pie chart
- Weekly/monthly trends
- Team performance comparison

---

## 🔗 Integration with SpecForge

### Upsell Path

```
Client: "I need HR software for my startup"
       ↓
SpecForge: Generates requirements
       ↓
Question: "How do you handle recruitment?"
       ↓
Upsell: "Want AI-powered candidate email automation?"
       ↓
HRForge Quote
```

### Package Deal

| Combined Package | Price | Savings |
|------------------|-------|---------|
| SpecForge + HRForge Lite | $299/mo | $50/mo |
| SpecForge + HRForge Full | $599/mo | $100/mo |
| All 3 (SpecForge + HRForge + RedForge) | $999/mo | $200/mo |

---

## 🎨 Template Examples

### Acknowledgment Email

```subject
Application Received - {{Position}} at {{Company}}

---

Hi {{CandidateName}},

Thank you for applying to the {{Position}} role at {{Company}}.

We've received your application and our team is reviewing it. You'll hear back from us within 5 business days.

Best regards,
{{HR Team}}
```

### Interview Invitation

```subject
Interview Invitation - {{Position}} - {{CandidateName}}

---

Hi {{CandidateName}},

Great news! We'd like to invite you for an interview for the {{Position}} role.

Please choose a time that works for you:
- {{TimeSlot1}}
- {{TimeSlot2}}
- {{TimeSlot3}}

Click to confirm: {{CalendarLink}}

Best regards,
{{HR Team}}
```

### WhatsApp Quick Update

```
Hi {{first_name}}! 👋 Just a quick update - your application for 
{{position}} is being reviewed. We'll be in touch soon! #{{company}}
```

---

## 💰 Pricing

| Service | Price |
|---------|-------|
| Lite | $149/month |
| Full | $399/month |
| Enterprise | $799/month |

**One-time setup:** $499 (Lite), $999 (Full), $1,999 (Enterprise)

**Add-ons:**
- WhatsApp notifications: +$50/month
- SMS notifications: +$30/month
- Custom integrations: $499 one-time

---

## 🚀 Quick Start

1. **Connect Email** - Gmail/Outlook API
2. **Import Templates** - Or use ours
3. **Set Triggers** - Define automation rules
4. **Configure WhatsApp** - Optional
5. **Test** - Run through candidate flow
6. **Go Live** - Start processing applications

### Environment Variables

```bash
# Required
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret

# Optional - WhatsApp
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_TOKEN=your_token

# Optional - SMS
TWILIO_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
```

---

## 🔐 Security

- All credentials encrypted at rest
- OAuth2 for email providers
- Webhook signature verification
- GDPR compliant data handling
- Candidate data deletion on request

---

**🔓 HRForge - Replace HR with AI**

*Version 2.0 - Now with WhatsApp & SMS support*
