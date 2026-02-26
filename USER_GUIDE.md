# 🔓 SpecForge - User Guide

## AI-Powered Requirement Expansion Tool

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Features](#features)
4. [MiniMax Integration](#minimax-integration)
5. [Understanding Results](#understanding-results)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)

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

## MiniMax Integration

SpecForge supports AI enhancement using MiniMax.

### Two Authentication Methods

#### Method 1: OAuth (Recommended)

```bash
# Set environment variables
export MINIMAX_CLIENT_ID=your_client_id
export MINIMAX_CLIENT_SECRET=your_client_secret
export MINIMAX_REDIRECT_URI=http://localhost:5000/auth/minimax/callback
```

**Flow:**
1. User clicks "Connect MiniMax" 
2. Redirects to MiniMax authorization
3. Callback stores access token
4. AI enhancement available

#### Method 2: API Key

```bash
# Set API key directly
export MINIMAX_API_KEY=your_api_key
```

### Using AI Enhancement

1. Check "AI Enhance with MiniMax" checkbox
2. Click "Analyze Requirements"
3. MiniMax will enhance with:
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
    "provider": "minimax"
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
  "ai_provider": "minimax"
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

### MiniMax Chat

```bash
POST /api/minimax/chat
Content-Type: application/json

{
  "message": "Help me design a login system",
  "model": "abab6.5s-chat"
}
```

---

### MiniMax Enhancement

```bash
POST /api/minimax/enhance
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
    "minimax": {
      "oauth_configured": true,
      "api_key_configured": false
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
  "provider": "minimax",
  "token_expires_in": 3600
}
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | No | Server port (default: 5000) |
| `SECRET_KEY` | No | Session secret key |
| `MINIMAX_CLIENT_ID` | No* | OAuth client ID |
| `MINIMAX_CLIENT_SECRET` | No* | OAuth client secret |
| `MINIMAX_REDIRECT_URI` | No | OAuth callback URL |
| `MINIMAX_API_KEY` | No* | Direct API key access |

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
1. Click "Connect MiniMax" (or set API key)
2. Check "AI Enhance with MiniMax"
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
| MiniMax OAuth fails | Check CLIENT_ID and REDIRECT_URI |
| AI enhancement not working | Verify API key or OAuth flow |
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

*Version 2.0 - Now with MiniMax AI Integration*
