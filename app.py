"""
SpecForge - AI Requirement Expansion Tool
Two-step flow: analyze → clarify → generate PRD
"""

from flask import Flask, render_template, request, jsonify
import os
from openai import OpenAI

app = Flask(__name__)

DOMAIN_TEMPLATES = {
    "e-commerce": [
        "Product catalog with images",
        "Shopping cart functionality",
        "Checkout and payment processing",
        "Order management system",
        "Inventory management",
        "User accounts and profiles",
        "Product search and filters",
        "Shipping calculation",
        "Admin dashboard",
        "Order confirmation emails",
    ],
    "saas": [
        "User authentication (signup/login)",
        "Subscription billing",
        "Team/workspace management",
        "Role-based permissions",
        "Dashboard with analytics",
        "Settings/configuration",
        "API access",
        "Usage tracking",
        "Notification system",
        "Support/helpdesk",
    ],
    "marketplace": [
        "User profiles (buyers/sellers)",
        "Product listings",
        "Search and filtering",
        "Messaging between users",
        "Order processing",
        "Commission/billing system",
        "Rating and reviews",
        "Dispute resolution",
        "Admin moderation",
        "Payment splitting",
    ],
    "blog": [
        "Article publishing",
        "Categories and tags",
        "Comment system",
        "User accounts",
        "Newsletter signup",
        "Social sharing",
        "SEO optimization",
        "Search functionality",
        "Media library",
        "Author profiles",
    ],
    "crm": [
        "Contact management",
        "Lead tracking",
        "Deal pipeline",
        "Task management",
        "Email integration",
        "Reporting/analytics",
        "Activity timeline",
        "Team collaboration",
        "Workflow automation",
        "Import/export data",
    ],
    "mobile-app": [
        "User authentication",
        "Push notifications",
        "Offline mode",
        "Camera/gallery access",
        "Location services",
        "Social sharing",
        "In-app purchases",
        "Analytics tracking",
        "App settings",
        "Data sync",
    ],
    "api": [
        "RESTful endpoints",
        "Authentication (JWT/OAuth)",
        "Rate limiting",
        "Input validation",
        "Error handling",
        "API documentation",
        "Webhooks",
        "Caching layer",
        "Versioning",
        "Monitoring/logging",
    ],
    "social": [
        "User profiles",
        "Follow/friend system",
        "News feed / timeline",
        "Direct messaging",
        "End-to-end encryption",
        "Media sharing (photos/videos)",
        "Notifications",
        "Search for users",
        "Privacy settings",
        "Content moderation",
    ],
}

DOMAIN_QUESTIONS = {
    "e-commerce": [
        {
            "id": "products",
            "question": "How many products are you planning to sell?",
            "options": [
                "Less than 50",
                "50-500 products",
                "500-5000 products",
                "More than 5000",
            ],
        },
        {
            "id": "payment",
            "question": "Which payment methods do you need?",
            "options": [
                "Cards only (Stripe)",
                "PayPal",
                "Razorpay (India)",
                "Multiple gateways",
            ],
        },
        {
            "id": "shipping",
            "question": "How will shipping work?",
            "options": [
                "Fixed flat rate",
                "Weight-based calculation",
                "Free shipping always",
                "Third-party (FedEx/UPS)",
            ],
        },
        {
            "id": "vendors",
            "question": "Is this single vendor or multi-vendor?",
            "options": [
                "Single vendor (my store)",
                "Multi-vendor marketplace",
                "Dropshipping model",
                "Not sure yet",
            ],
        },
        {
            "id": "timeline",
            "question": "What is your expected launch timeline?",
            "options": ["1-2 months", "3-4 months", "6+ months", "No fixed deadline"],
        },
    ],
    "saas": [
        {
            "id": "billing",
            "question": "What pricing model do you want?",
            "options": [
                "Monthly subscription",
                "Annual subscription",
                "Usage-based (pay per use)",
                "Freemium + paid tiers",
            ],
        },
        {
            "id": "users",
            "question": "How will users be organized?",
            "options": [
                "Individual users only",
                "Teams with workspaces",
                "Organizations with roles",
                "Single user tool",
            ],
        },
        {
            "id": "platform",
            "question": "What platform does this run on?",
            "options": ["Web app only", "Web + mobile", "Desktop app", "API only"],
        },
        {
            "id": "auth",
            "question": "How should users sign in?",
            "options": [
                "Email + password",
                "Google/social login",
                "SSO (enterprise)",
                "Magic link (email)",
            ],
        },
        {
            "id": "timeline",
            "question": "What is your expected launch timeline?",
            "options": ["1-2 months", "3-4 months", "6+ months", "No fixed deadline"],
        },
    ],
    "social": [
        {
            "id": "chat_type",
            "question": "What type of messaging do you need?",
            "options": [
                "1-on-1 only",
                "Group chats only",
                "Both 1-on-1 and groups",
                "Public channels like Slack",
            ],
        },
        {
            "id": "platform",
            "question": "Which platforms should this support?",
            "options": [
                "Mobile only (iOS + Android)",
                "Web only",
                "Both mobile and web",
                "All platforms including desktop",
            ],
        },
        {
            "id": "encryption",
            "question": "What encryption approach do you need?",
            "options": [
                "Signal protocol (like WhatsApp)",
                "Custom encryption",
                "Standard HTTPS only",
                "Not sure, need recommendation",
            ],
        },
        {
            "id": "media",
            "question": "What media can users share?",
            "options": [
                "Text only",
                "Images only",
                "Images and videos",
                "All files (images, video, docs, audio)",
            ],
        },
        {
            "id": "discovery",
            "question": "How do users find each other?",
            "options": [
                "Username search",
                "Phone number / contacts sync",
                "QR code scan",
                "Invite link only",
            ],
        },
    ],
    "marketplace": [
        {
            "id": "category",
            "question": "What type of marketplace is this?",
            "options": [
                "Physical products",
                "Digital products",
                "Services",
                "Mixed (products + services)",
            ],
        },
        {
            "id": "commission",
            "question": "How will you earn money?",
            "options": [
                "Commission per sale (%)",
                "Monthly seller subscription",
                "Listing fees",
                "Mixed model",
            ],
        },
        {
            "id": "payment",
            "question": "How should payments work?",
            "options": [
                "Direct to seller",
                "Held in escrow, released on delivery",
                "Stripe Connect",
                "Manual bank transfer",
            ],
        },
        {
            "id": "trust",
            "question": "How will you build buyer/seller trust?",
            "options": [
                "Ratings and reviews",
                "Verified seller badges",
                "Buyer protection program",
                "All of the above",
            ],
        },
        {
            "id": "timeline",
            "question": "What is your expected launch timeline?",
            "options": ["1-2 months", "3-4 months", "6+ months", "No fixed deadline"],
        },
    ],
    "blog": [
        {
            "id": "authors",
            "question": "Who will publish content?",
            "options": [
                "Just me (solo blog)",
                "Multiple authors",
                "Guest contributors",
                "Community-driven",
            ],
        },
        {
            "id": "monetization",
            "question": "How will you monetize?",
            "options": [
                "Ads (Google AdSense)",
                "Paid newsletter",
                "Affiliate links",
                "No monetization",
            ],
        },
        {
            "id": "comments",
            "question": "Do you need a comment system?",
            "options": [
                "Yes, full comment system",
                "Yes, but moderated only",
                "No comments",
                "Use Disqus or similar",
            ],
        },
        {
            "id": "seo",
            "question": "How important is SEO?",
            "options": [
                "Very important (main traffic source)",
                "Somewhat important",
                "Not a priority",
                "Not sure",
            ],
        },
        {
            "id": "timeline",
            "question": "What is your expected launch timeline?",
            "options": ["1-2 months", "3-4 months", "6+ months", "No fixed deadline"],
        },
    ],
    "crm": [
        {
            "id": "team_size",
            "question": "How many people will use this CRM?",
            "options": ["Just me", "2-10 people", "11-50 people", "50+ people"],
        },
        {
            "id": "pipeline",
            "question": "What is your sales process like?",
            "options": [
                "Simple (lead → close)",
                "Multi-stage pipeline",
                "Complex with approvals",
                "Not sure yet",
            ],
        },
        {
            "id": "integrations",
            "question": "What integrations do you need?",
            "options": [
                "Email (Gmail/Outlook)",
                "Calendar sync",
                "Slack notifications",
                "All of the above",
            ],
        },
        {
            "id": "reporting",
            "question": "What reports do you need?",
            "options": [
                "Basic (revenue, leads)",
                "Advanced analytics",
                "Custom dashboards",
                "Export to Excel only",
            ],
        },
        {
            "id": "timeline",
            "question": "What is your expected launch timeline?",
            "options": ["1-2 months", "3-4 months", "6+ months", "No fixed deadline"],
        },
    ],
    "mobile-app": [
        {
            "id": "platform",
            "question": "Which platforms do you need?",
            "options": [
                "iOS only",
                "Android only",
                "Both iOS and Android",
                "Cross-platform + web",
            ],
        },
        {
            "id": "offline",
            "question": "Does the app need to work offline?",
            "options": [
                "Yes, full offline mode",
                "Partial offline (read only)",
                "No, always online",
                "Not sure",
            ],
        },
        {
            "id": "notifications",
            "question": "What notifications does the app need?",
            "options": [
                "Push notifications",
                "In-app only",
                "Email + push",
                "No notifications",
            ],
        },
        {
            "id": "monetization",
            "question": "How will the app make money?",
            "options": [
                "Free with ads",
                "One-time purchase",
                "Subscription",
                "Freemium model",
            ],
        },
        {
            "id": "timeline",
            "question": "What is your expected launch timeline?",
            "options": ["1-2 months", "3-4 months", "6+ months", "No fixed deadline"],
        },
    ],
    "api": [
        {
            "id": "auth",
            "question": "What authentication method?",
            "options": ["API keys", "OAuth 2.0", "JWT tokens", "Multiple methods"],
        },
        {
            "id": "consumers",
            "question": "Who will consume this API?",
            "options": [
                "Internal apps only",
                "Third-party developers",
                "Mobile apps",
                "All of the above",
            ],
        },
        {
            "id": "scale",
            "question": "Expected API call volume?",
            "options": [
                "Low (< 1000/day)",
                "Medium (1k-100k/day)",
                "High (100k+/day)",
                "Not sure yet",
            ],
        },
        {
            "id": "docs",
            "question": "Do you need API documentation?",
            "options": [
                "Yes, Swagger/OpenAPI",
                "Yes, custom docs site",
                "Basic README only",
                "No docs needed",
            ],
        },
        {
            "id": "timeline",
            "question": "What is your expected launch timeline?",
            "options": ["1-2 months", "3-4 months", "6+ months", "No fixed deadline"],
        },
    ],
    "general": [
        {
            "id": "type",
            "question": "What type of product is this?",
            "options": [
                "Web application",
                "Mobile app",
                "Desktop software",
                "API / backend service",
            ],
        },
        {
            "id": "users",
            "question": "Who are the main users?",
            "options": [
                "Consumers (B2C)",
                "Businesses (B2B)",
                "Internal team only",
                "Developers",
            ],
        },
        {
            "id": "auth",
            "question": "Do users need to log in?",
            "options": [
                "Yes, with accounts",
                "Optional login",
                "No login needed",
                "Not sure",
            ],
        },
        {
            "id": "budget",
            "question": "What is your approximate budget?",
            "options": [
                "Under $5,000",
                "$5k - $20k",
                "$20k - $100k",
                "No fixed budget",
            ],
        },
        {
            "id": "timeline",
            "question": "What is your expected launch timeline?",
            "options": ["1-2 months", "3-4 months", "6+ months", "No fixed deadline"],
        },
    ],
}


def detect_domain(text):
    text = text.lower()
    domain_scores = {}
    keywords = {
        "e-commerce": [
            "shop",
            "store",
            "buy",
            "sell",
            "product",
            "cart",
            "order",
            "payment",
            "bakery",
            "inventory",
        ],
        "saas": [
            "subscription",
            "team",
            "plan",
            "billing",
            "monthly",
            "dashboard",
            "software",
        ],
        "marketplace": [
            "marketplace",
            "seller",
            "buyer",
            "multiple vendors",
            "commission",
            "vendor",
        ],
        "blog": [
            "blog",
            "article",
            "post",
            "content",
            "newsletter",
            "publish",
            "writer",
        ],
        "crm": [
            "crm",
            "customer",
            "lead",
            "deal",
            "pipeline",
            "contact",
            "sales",
            "client",
        ],
        "mobile-app": ["mobile", "ios", "android", "phone", "iphone"],
        "api": ["api", "backend", "endpoint", "integration", "service"],
        "social": [
            "chat",
            "message",
            "social",
            "connect",
            "instagram",
            "follow",
            "friend",
            "feed",
            "share",
            "community",
            "network",
            "dm",
            "encryption",
            "messaging",
        ],
    }
    for domain, words in keywords.items():
        score = sum(1 for word in words if word in text)
        domain_scores[domain] = score
    best = max(domain_scores, key=domain_scores.get)
    return best if domain_scores[best] > 0 else "general"


def detect_missing_features(domain, text):
    template = DOMAIN_TEMPLATES.get(domain, [])
    text = text.lower()
    missing = []
    for feature in template:
        feature_keywords = feature.lower().split()
        if not any(kw in text for kw in feature_keywords[:2]):
            missing.append(feature)
    return missing[:7]


def calculate_rms(requirements, domain):
    score = 40
    if len(requirements) > 100:
        score += 20
    elif len(requirements) > 50:
        score += 15
    elif len(requirements) > 20:
        score += 10
    template = DOMAIN_TEMPLATES.get(domain, [])
    coverage = (
        len([f for f in template if f.lower() in requirements.lower()]) / len(template)
        if template
        else 0
    )
    score += int(coverage * 15)
    key_terms = {
        "security": ["security", "auth", "password", "encryption"],
        "performance": ["performance", "speed", "load", "cache"],
        "api": ["api", "endpoint", "integration"],
        "mobile": ["mobile", "responsive", "ios", "android"],
        "admin": ["admin", "dashboard", "manage"],
    }
    for category, terms in key_terms.items():
        if any(term in requirements.lower() for term in terms):
            score += 5
    return min(100, score)


def get_ai_client():
    groq_key = os.environ.get("GROQ_API_KEY")
    minimax_key = os.environ.get("MINIMAX_API_KEY")
    if groq_key:
        return (
            OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key),
            "llama-3.3-70b-versatile",
            "Groq",
        )
    elif minimax_key:
        return (
            OpenAI(base_url="https://api.minimax.io/v1", api_key=minimax_key),
            "MiniMax-M2.5",
            "MiniMax",
        )
    return None, None, None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    client_input = data.get("requirements", "")
    if not client_input or len(client_input.strip()) < 10:
        return (
            jsonify({"success": False, "error": "Please enter at least 10 characters"}),
            400,
        )

    domain = detect_domain(client_input)
    missing_features = detect_missing_features(domain, client_input)
    rms = calculate_rms(client_input, domain)
    questions = DOMAIN_QUESTIONS.get(domain, DOMAIN_QUESTIONS["general"])

    return jsonify(
        {
            "success": True,
            "domain": domain,
            "missing_features": missing_features,
            "rms": rms,
            "questions": questions,
        }
    )


@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    requirements = data.get("requirements", "")
    domain = data.get("domain", "general")
    answers = data.get("answers", {})
    missing_features = data.get("missing_features", [])
    rms = data.get("rms", 0)

    if not requirements:
        return jsonify({"success": False, "error": "Requirements are required"}), 400

    answers_text = "\n".join([f"- {qid}: {answer}" for qid, answer in answers.items()])

    prompt = f"""You are a senior software architect creating a professional PRD document.

CLIENT BRIEF:
{requirements}

DOMAIN: {domain}

CLIENT ANSWERS TO CLARIFICATION QUESTIONS:
{answers_text}

MISSING FEATURES DETECTED:
{chr(10).join(['- ' + f for f in missing_features])}

Based on the brief AND the client's answers above, generate a complete PRD with these sections:

## Project Overview
Write 2-3 paragraphs summarizing the project based on the brief and answers.

## Target Users
List the main user types and their goals.

## Core Features
List the must-have features based on the brief and answers. Be specific.

## Missing Features to Consider
Based on the detected gaps, list features the client hasn't mentioned but will likely need.

## Recommended Tech Stack
Specific technologies for this exact project based on the answers given.

## Development Phases
Break into MVP phase and future phases.

## Risk Factors
3 specific risks for this project.

## Estimated Timeline
Based on the scope described and answers given.

## Next Steps
3 concrete next steps to start this project.

Be specific and tailor everything to the client's actual answers. Do not give generic advice.
Respond in clean markdown format."""

    client, model, provider = get_ai_client()

    if not client:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "No AI API key configured. Add GROQ_API_KEY or MINIMAX_API_KEY to .env",
                }
            ),
            500,
        )

    try:
        completion = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}]
        )
        prd_text = completion.choices[0].message.content
        return jsonify(
            {
                "success": True,
                "prd": prd_text,
                "model": provider,
                "domain": domain,
                "rms": rms,
                "missing_features": missing_features,
                "answers": answers,
            }
        )
    except Exception as e:
        print(f"AI error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/auth/status", methods=["GET"])
def auth_status():
    return jsonify(
        {
            "authenticated": bool(
                os.environ.get("GROQ_API_KEY") or os.environ.get("MINIMAX_API_KEY")
            ),
            "provider": (
                "Groq"
                if os.environ.get("GROQ_API_KEY")
                else ("MiniMax" if os.environ.get("MINIMAX_API_KEY") else None)
            ),
        }
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "healthy",
            "version": "3.0.0",
            "ai_configured": bool(
                os.environ.get("GROQ_API_KEY") or os.environ.get("MINIMAX_API_KEY")
            ),
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    _, _, provider = get_ai_client()
    print(f"SpecForge v3.0 running on http://localhost:{port}")
    print(f"  AI Provider: {provider or 'NOT CONFIGURED'}")
    app.run(debug=False, port=port, host="127.0.0.1")
