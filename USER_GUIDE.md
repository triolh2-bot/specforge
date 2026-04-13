# 🔓 SpecForge - User Guide

## AI-Powered Requirement Expansion Tool

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Features](#features)
4. [Generate Brief](#generate-brief)
5. [OpenRouter Setup](#openrouter-setup)
6. [Understanding Results](#understanding-results)
7. [API Reference](#api-reference)
8. [Configuration](#configuration)

---

## Overview

SpecForge transforms brief client requirements into comprehensive PRD documents using AI enhancement. It detects:
- Domain type (e-commerce, SaaS, CRM, etc.)
- Missing features (Negative Scope Detection™)
- Clarification questions needed
- Stakeholder conflicts
- Requirement Maturity Score (RMS)

---

## Getting Started

### Quick Start

```bash
# Clone and setup
git clone https://github.com/your-org/specforge.git
cd specforge-mvp
pip install -r requirements.txt

# Run the app
python app.py

# Access at http://localhost:5000
```

### Environment Variables

```bash
export PORT=5000
export SECRET_KEY=your-secret-key
```

---

## Features

### 1. Domain Detection

SpecForge automatically identifies the project type:

| Domain | Keywords Detected |
|--------|-------------------|
| E-commerce | shop, store, buy, cart, inventory |
| SaaS | subscription, team, billing, dashboard |
| Marketplace | seller, buyer, vendor, commission |
| Blog | article, post, publish, newsletter |
| CRM | customer, lead, deal, pipeline |
| Mobile App | mobile, iOS, Android, app |
| API | endpoint, backend, integration |

---

### 2. Negative Scope Detection™

The core feature - identifies features NOT mentioned but likely needed:

**Example:**
```
Input: "I want an e-commerce store for my bakery"
Missing detected:
- Inventory management
- Shipping calculation
- Order confirmation emails
- Admin dashboard
- Product search & filters
```

---

### 3. Requirement Maturity Score (RMS)

Scored 0-100 based on:

| Factor | Weight |
|--------|--------|
| Requirements length | +20 max |
| Domain coverage | +15 max |
| Security mentions | +5 |
| Performance mentions | +5 |
| API requirements | +5 |
| Mobile requirements | +5 |
| Admin features | +5 |

---

### 4. Clarification Questions

自动生成需澄清的问题:

- Authentication methods needed
- Payment providers
- Mobile app requirements
- Timeline expectations
- Budget range

---

### 5. Conflict Detection

Detects stakeholder conflicts:

| Conflict | Example |
|----------|---------|
| Timeline vs Complexity | "Fast" + "Advanced ML features" |
| Budget vs Scope | "Cheap" + "Enterprise features" |
| Security vs Simplicity | "Simple" + "Secure" |

---

## Generate Brief

The "Generate Brief" modal helps you draft a full requirements brief from a few structured inputs.

### How it works

1. Click **Generate Brief** in the Analyze view.
2. Fill in Project Name and Core Idea (required).
3. Choose OpenRouter as the AI provider.
4. Click **Generate** and wait for the brief to populate the requirements box.

The generated brief can then be analyzed like any other requirements input.

## OpenRouter Setup

SpecForge supports AI enhancement using OpenRouter.

### Environment Variables

```bash
export OPENROUTER_API_KEY=your_api_key
export OPENROUTER_MODEL=openai/gpt-4o-mini
export OPENROUTER_SITE_URL=http://localhost:5000
```

### Using AI Enhancement

1. Check "AI Enhance" in the Analyze form.
2. Choose the OpenRouter provider.
3. Click "Analyze Requirements".
4. OpenRouter will enhance the output with:
   - Missing technical components
   - Security considerations
   - Scalability recommendations
   - UX improvements
   - Risk assessment

---

## Understanding Results

### Output Structure

```json
{
  "success": true,
  "domain": "e-commerce",
  "implied_users": ["Customer", "Admin"],
  "missing_features": [
    "Shopping cart functionality",
    "Payment integration",
    ...
  ],
  "clarification_questions": [
    "Which payment providers?",
    ...
  ],
  "conflicts": [],
  "rms": 65,
  "prd": {
    "title": "Project Specification Document",
    "version": "1.0",
    "overview": {...},
    "scope": {...},
    "functional_requirements": [...],
    "non_functional": {...},
    "risks": [...],
    "next_steps": [...]
  },
  "ai_enhanced": {
    "status": "ready",
    "provider": "openrouter"
  }
}
```

### PRD Sections

| Section | Description |
|---------|-------------|
| Overview | Summary, project type, target users |
| Scope | In-scope and out-of-scope items |
| Functional Requirements | Core features needed |
| Non-Functional | Performance, security, scalability |
| Risks | Potential issues |
| Next Steps | Action items |

---

## API Reference

### Analyze Requirements

```bash
POST /analyze
Content-Type: application/json

{
  "requirements": "I want an e-commerce store...",
  "ai_enhance": true,
  "ai_provider": "openrouter"
}
```

**Response:**
```json
{
  "success": true,
  "domain": "e-commerce",
  "rms": 65,
  "prd": {...}
}
```

---

### Generate Brief

```bash
POST /api/generate-brief
Content-Type: application/json

{
  "project_name": "TaskFlow",
  "project_type": "Web Application",
  "core_idea": "Task management for distributed teams",
  "target_audience": "SMBs",
  "key_features": "team boards, notifications, reports",
  "ai_provider": "openrouter"
}
```

---

### AI Chat

```bash
POST /api/ai/chat
Content-Type: application/json

{
  "message": "Help me design a login system",
  "model": "openai/gpt-4o-mini"
}
```

---

### AI Enhancement

```bash
POST /api/ai/enhance
Content-Type: application/json

{
  "requirements": "User wants a blog..."
}
```

---

### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "features": [...],
  "ai_providers": {
    "openrouter": {
      "api_key_configured": true,
      "model_configured": true
    }
  }
}
```

---

### Authentication Status

```bash
GET /auth/status
```

**Response:**
```json
{
  "authenticated": true,
  "provider": null,
  "token_expires_in": 0
}
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | No | Server port (default: 5000) |
| `SECRET_KEY` | No | Session secret key |
| `OPENROUTER_API_KEY` | No* | OpenRouter API key |
| `OPENROUTER_MODEL` | No | OpenRouter model name |
| `OPENROUTER_SITE_URL` | No | Domain sent as HTTP-Referer |

*Required for AI features

### Custom Domain Templates

Edit `app.py` to add custom domain templates:

```python
DOMAIN_TEMPLATES = {
    "your-domain": [
        "Feature 1",
        "Feature 2",
        ...
    ]
}
```

---

## Example Workflows

### 1. Basic Requirement Analysis

```
1. Enter brief: "I need a booking system for a hotel"
2. Click "Analyze Requirements"
3. View RMS score and missing features
4. Answer clarification questions
5. Download PRD
```

### 2. AI-Enhanced Analysis

```
1. Set OPENROUTER_API_KEY in your environment
2. Check "AI Enhance"
3. Enter requirements
4. Click "Analyze Requirements"
5. View both PRD + AI enhancement suggestions
```

### 3. Integration with HRForge

```
1. SpecForge detects HR/recruitment need
2. Prompt: "Need candidate management?"
3. Upsell to HRForge service
4. Generate combined quote
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Please enter at least 10 characters" | Add more detail to requirements |
| OpenRouter requests fail | Check OPENROUTER_API_KEY, model, and rate limits |
| AI enhancement not working | Verify OpenRouter credentials and provider status |
| Domain detection wrong | Add more domain-specific keywords |

### Debug Mode

```python
# In app.py, temporarily add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Support

- **Docs:** docs.specforge.io
- **GitHub:** github.com/your-org/specforge
- **Email:** support@specforge.io

---

**🔓 SpecForge - Turn "build me an app" into buildable software**

*Version 2.0 - OpenRouter-powered AI enhancement*
