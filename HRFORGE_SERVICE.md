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

- [ ] Resume parsing (PDF, DOCX)
- [ ] Candidate database
- [ ] Application tracking
- [ ] Status pipeline (Applied → Screen → Interview → Offer → Hired)
- [ ] Notes & comments
- [ ] Activity timeline

### Email Automation

- [ ] Auto-reply rules
- [ ] Template variables
- [ ] Scheduled sends
- [ ] Bounce handling
- [ ] Unsubscribe management
- [ ] Attachment handling

### Scheduling

- [ ] Calendar integration
- [ ] Time zone handling
- [ ] Availability detection
- [ ] Reminder automation
- [ ] Reschedule handling

### Reporting

- [ ] Response time metrics
- [ ] Conversion rates
- [ ] Source tracking
- [ ] Time-to-hire
- [ ] Email engagement

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

---

## 💰 Pricing

| Service | Price |
|---------|-------|
| Lite | $149/month |
| Full | $399/month |
| Enterprise | $799/month |

**One-time setup:** $499 (Lite), $999 (Full), $1,999 (Enterprise)

---

## 🔄 Integration with SpecForge

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

---

## 🚀 Quick Start

1. **Connect Email** - Gmail/Outlook API
2. **Import Templates** - Or use ours
3. **Set Triggers** - Define automation rules
4. **Test** - Run through candidate flow
5. **Go Live** - Start processing applications

---

**🔓 HRForge - Replace HR with AI**
