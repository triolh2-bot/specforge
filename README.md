# 🔓 SpecForge - AI Requirement Expansion Platform

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

Transform 2-5 line client briefs into professional, buildable software specifications with AI-powered analysis.

## ✨ Features

### 🎯 Core Innovation: Negative Scope Detection™
The only tool that finds what's **NOT** in the requirements but SHOULD be:

- ✅ Detects implicit assumptions
- ✅ Identifies missing adjacent systems  
- ✅ Flags regulatory requirements
- ✅ Lists commonly overlooked features

### 📊 Requirement Maturity Score (RMS)
A 0-100 score measuring:
- Completeness (all required sections present)
- Feasibility (technically achievable)
- Consistency (no self-contradictory requirements)
- Precision (specific vs vague language)

### ⚔️ Stakeholder Conflict Detection
Flags contradictory requirements:
- "Quick delivery" vs "Complex features"
- "Budget conscious" vs "Enterprise features"
- "Simple" vs "Highly secure"

### ❓ Auto-Question Engine
Generates specific, contextual questions instead of generic "tell me more":
- "Which payment providers? (Stripe, PayPal)"
- "What authentication methods? (2FA, SSO, Magic links)"
- "Native app or responsive web?"

### 🌐 Multi-Domain Support
Automatically detects and adapts for:
- E-commerce / Online Stores
- SaaS Applications
- Marketplaces
- CRM Systems
- Blogs / Content Sites
- Mobile Apps
- APIs / Backend Services

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/triolh2-bot/specforge.git
cd specforge

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Then open: **http://localhost:5000**

### Containerized Startup

```bash
cp .env.example .env
docker compose up --build
```

The compose stack starts `postgres`, `web`, and `worker`. Deployment details live in `docs/deployment.md`.

### Docker

```bash
docker compose up --build
```

The web UI runs on `http://localhost:5000` and the worker runs in a separate container.

## 💻 Usage

### 1. Enter Requirements
Paste a 2-5 line client brief:

```
I want an e-commerce site for my bakery. Instagram-style feed. 
People can order and pay. Need admin panel.
```

### 2. Click Analyze
SpecForge processes and extracts:
- Project domain
- Implied users
- Missing features
- Clarification questions
- Conflict warnings
- RMS score

### 3. Review Results
- **Missing Features** - What's not mentioned but needed
- **Questions** - What to ask the client
- **Conflicts** - Potential scope issues
- **PRD** - Complete specification document

### 4. Export
Generate professional PRD documents for:
- PDF export
- Markdown
- Confluence
- Notion

## 📱 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main UI |
| `/analyze` | POST | Analyze requirements |
| `/health/live` | GET | Liveness check |
| `/health/ready` | GET | Readiness check |
| `/health` | GET | Compatibility health summary |
| `/metrics` | GET | Metrics snapshot |

### API Example

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": "I want an e-commerce site for my bakery",
    "ai_enhance": false
  }'
```

## 🏗️ Tech Stack

- **Backend**: Python + Flask
- **Frontend**: HTML + Tailwind CSS (self-hosted)
- **AI**: OpenRouter (OpenAI-compatible)
- **Database**: SQLite (dev) or PostgreSQL (recommended for prod)

## 📦 Project Structure

```
specforge/
├── app.py              # Main Flask application
├── requirements.txt    # Dependencies
├── templates/          # HTML templates
│   └── index.html
└── README.md          # This file
```

## 🔧 Configuration

### Environment Variables

```bash
export PORT=5000
export OPENROUTER_API_KEY=your_key_here
export OPENROUTER_MODEL=openai/gpt-4o-mini
export OPENROUTER_SITE_URL=https://your-domain.example
```

For the full list of supported env vars, see `.env.example`.

## Security

Security baseline material lives in:
- `SECURITY.md`
- `docs/security-baseline.md`
- `docs/deployment.md`
- `docs/operations-monitoring.md`
- `docs/ci-cd.md`
- `.github/workflows/ci.yml`
- `.github/workflows/security.yml`
- `.github/workflows/release.yml`
- `scripts/security_check.sh`

Local security checks can be run with:

```bash
pip install -r requirements-security.txt
./scripts/security_check.sh
```

## 🎯 Use Cases

### For Freelancers
- Charge $100-500 for requirement analysis
- Deliver professional PRD documents
- Reduce scope creep

### For Agencies
- Streamline discovery process
- Improve client communication
- Faster project kickoffs

### For Product Teams
- Document MVP requirements
- Align stakeholders
- Identify gaps early

## 📈 Roadmap

- [ ] AI enhancement with OpenAI
- [ ] More domain templates
- [ ] PDF export
- [ ] Confluence integration
- [ ] Notion integration
- [ ] Team collaboration
- [ ] API access
- [x] 🔓 Red Team Automation Service (NEW)
- [x] Security Testing Upsells (NEW)

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines first.

1. Fork the repo
2. Create your feature branch
3. Submit a pull request

## 📝 License

MIT License - feel free to use for personal and commercial projects.

## 👏 Acknowledgments

- Inspired by Nat Eliason's AI agent business
- Built with OpenClaw

---

**Built with ❤️ by fewic**

*Turn "build me an app" into buildable software.* 🔓
