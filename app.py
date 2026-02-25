"""
SpecForge MVP - AI Requirement Expansion Tool (Enhanced Version)
Transforms brief requirements into detailed specs with AI enhancement.
"""

from flask import Flask, render_template, request, jsonify
import os
import re
import json

app = Flask(__name__)

# Domain templates - what features are typically needed
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
        "Order confirmation emails"
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
        "Support/helpdesk"
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
        "Payment splitting"
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
        "Author profiles"
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
        "Import/export data"
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
        "Data sync"
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
        "Monitoring/logging"
    ]
}

# Detect domain from input
def detect_domain(text):
    text = text.lower()
    domain_scores = {}
    
    keywords = {
        "e-commerce": ["shop", "store", "buy", "sell", "product", "cart", "order", "payment", "bakery", "inventory"],
        "saas": ["subscription", "team", "plan", "billing", "monthly", "dashboard", "software", "app"],
        "marketplace": ["marketplace", "seller", "buyer", "multiple vendors", "commission", "vendor"],
        "blog": ["blog", "article", "post", "content", "newsletter", "publish", "writer"],
        "crm": ["crm", "customer", "lead", "deal", "pipeline", "contact", "sales", "client"],
        "mobile-app": ["mobile", "ios", "android", "app", "phone", "iphone"],
        "api": ["api", "backend", "endpoint", "integration", "service"]
    }
    
    for domain, words in keywords.items():
        score = sum(1 for word in words if word in text)
        domain_scores[domain] = score
    
    best = max(domain_scores, key=domain_scores.get)
    return best if domain_scores[best] > 0 else "general"

# Negative scope detection
def detect_missing_features(domain, text):
    template = DOMAIN_TEMPLATES.get(domain, [])
    text = text.lower()
    
    missing = []
    for feature in template:
        feature_lower = feature.lower()
        feature_keywords = feature_lower.split()
        if not any(kw in text for kw in feature_keywords[:2]):
            missing.append(feature)
    
    return missing[:7]  # Return top 7

# Detect implied users
def detect_implied_users(text):
    text = text.lower()
    users = []
    
    user_indicators = {
        "admin": ["admin", "administrator", "dashboard", "manage"],
        "customer": ["customer", "user", "client", "buyer", "shopper"],
        "employee": ["employee", "staff", "team", "worker"],
        "guest": ["guest", "visitor", "anonymous", "public"],
        "vendor": ["vendor", "seller", "supplier", "partner"]
    }
    
    for user_type, indicators in user_indicators.items():
        if any(ind in text for ind in indicators):
            users.append(user_type.title())
    
    return users if users else ["User"]

# Calculate RMS
def calculate_rms(requirements, domain):
    score = 40  # Base score
    
    # Length check
    if len(requirements) > 100:
        score += 20
    elif len(requirements) > 50:
        score += 15
    elif len(requirements) > 20:
        score += 10
    
    # Domain coverage
    template = DOMAIN_TEMPLATES.get(domain, [])
    coverage = len([f for f in template if f.lower() in requirements.lower()]) / len(template) if template else 0
    score += int(coverage * 15)
    
    # Check for key sections
    key_terms = {
        "security": ["security", "auth", "password", "encryption"],
        "performance": ["performance", "speed", "load", "cache"],
        "api": ["api", "endpoint", "integration"],
        "mobile": ["mobile", "responsive", "ios", "android"],
        "admin": ["admin", "dashboard", "manage"]
    }
    
    for category, terms in key_terms.items():
        if any(term in requirements.lower() for term in terms):
            score += 5
    
    return min(100, score)

# Generate clarification questions
def generate_questions(domain, text, missing_features):
    questions = []
    text_lower = text.lower()
    
    # Authentication questions
    if "login" in text_lower or "auth" in text_lower or "sign" in text_lower:
        questions.append("What authentication methods do you need? (Password, Social login, SSO, 2FA, Magic links)")
    
    # Payment questions
    if "payment" in text_lower or "buy" in text_lower or "order" in text_lower or "purchase" in text_lower:
        questions.append("Which payment providers should be integrated? (Stripe, PayPal, Razorpay, etc.)")
        questions.append("Do you need support for subscriptions/reurring payments?")
    
    # Mobile questions
    if "mobile" in text_lower or "ios" in text_lower or "android" in text_lower:
        questions.append("Do you need native mobile apps or a responsive web app?")
    
    # Timeline/Budget
    questions.append("What's your expected launch timeline? (Weeks/Months)")
    questions.append("What's your approximate budget range?")
    
    # Domain-specific questions
    if domain == "e-commerce":
        questions.append("How will inventory be managed? (Manual, sync with suppliers, automated)")
        questions.append("Do you need multi-vendor marketplace support?")
        questions.append("What shipping providers will you use?")
    
    if domain == "saas":
        questions.append("What pricing tiers should be available? (Free, Pro, Enterprise)")
        questions.append("Do you need usage-based billing or feature-based?")
        questions.append("Should customers be able to create teams/workspaces?")
    
    if domain == "crm":
        questions.append("What pipeline stages do you need?")
        questions.append("Do you need email integration? (Gmail, Outlook)")
        questions.append("What reporting features are essential?")
    
    # Only return top 5 most important
    return questions[:5]

# Generate stakeholder conflicts
def detect_conflicts(text):
    conflicts = []
    text_lower = text.lower()
    
    # Timeline conflicts
    if any(word in text_lower for word in ["fast", "quick", "soon", "asap"]) and any(word in text_lower for word in ["complex", "advanced", "ml", "ai", "custom"]):
        conflicts.append("You want quick delivery but complex features - consider prioritizing MVP features")
    
    # Budget vs scope
    if any(word in text_lower for word in ["cheap", "budget", "low cost", "free"]) and any(word in text_lower for word in ["professional", "enterprise", "custom"]):
        conflicts.append("Budget expectations may not match enterprise feature requirements")
    
    # Security vs simplicity
    if "simple" in text_lower and ("secure" in text_lower or "security" in text_lower):
        conflicts.append("Security features add complexity - balance simplicity with security needs")
    
    return conflicts

# Generate PRD
def generate_prd(client_input, use_ai=False):
    domain = detect_domain(client_input)
    missing_features = detect_missing_features(domain, client_input)
    questions = generate_questions(domain, client_input, missing_features)
    implied_users = detect_implied_users(client_input)
    conflicts = detect_conflicts(client_input)
    rms = calculate_rms(client_input, domain)
    
    # AI enhancement (placeholder - can integrate with OpenAI/Anthropic)
    ai_enhanced = None
    if use_ai:
        # TODO: Add OpenAI API call for advanced enhancement
        ai_enhanced = {
            "status": "AI enhancement requires API key",
            "suggestion": "Configure OPENAI_API_KEY for advanced analysis"
        }
    
    return {
        "success": True,
        "domain": domain,
        "implied_users": implied_users,
        "missing_features": missing_features,
        "clarification_questions": questions,
        "conflicts": conflicts,
        "rms": rms,
        "prd": {
            "title": "Project Specification Document",
            "version": "1.0",
            "overview": {
                "summary": client_input[:300],
                "project_type": domain,
                "target_users": implied_users
            },
            "scope": {
                "in_scope": [
                    f"Core {domain} functionality",
                    "User authentication and management",
                    "Admin dashboard",
                    "Basic analytics/reporting"
                ],
                "out_of_scope": [
                    "Advanced AI/ML features",
                    "Custom integrations",
                    "Mobile native apps (MVP phase)"
                ]
            },
            "functional_requirements": generate_functional_reqs(domain, client_input),
            "non_functional": {
                "performance": "Page load under 3 seconds",
                "security": "HTTPS, secure authentication, data encryption",
                "scalability": "Support 1000+ concurrent users initially",
                "reliability": "99.9% uptime target"
            },
            "technical_constraints": {
                "timeline": "To be determined",
                "budget": "To be determined",
                "team_size": "1-3 developers recommended"
            },
            "risks": [
                "Scope creep from unclear requirements",
                "Third-party API integration challenges",
                "Timeline delays from dependencies"
            ],
            "next_steps": [
                "Answer clarification questions",
                "Finalize scope with stakeholders",
                "Create technical specification"
            ]
        },
        "ai_enhanced": ai_enhanced
    }

def generate_functional_reqs(domain, text):
    base_reqs = [
        "User registration and authentication",
        "User profile management",
        f"{domain.title()} core functionality",
        "Admin dashboard with analytics",
        "Data management (CRUD operations)",
        "Basic reporting"
    ]
    
    text_lower = text.lower()
    
    if any(w in text_lower for w in ["payment", "buy", "order", "purchase"]):
        base_reqs.extend([
            "Shopping cart functionality",
            "Payment integration",
            "Order history"
        ])
    
    if any(w in text_lower for w in ["search", "find", "filter"]):
        base_reqs.append("Advanced search and filtering")
    
    if any(w in text_lower for w in ["notify", "email", "message"]):
        base_reqs.append("Notification system")
    
    return base_reqs[:10]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    client_input = data.get('requirements', '')
    use_ai = data.get('ai_enhance', False)
    
    if not client_input or len(client_input.strip()) < 10:
        return jsonify({
            "success": False,
            "error": "Please enter at least 10 characters describing your requirements"
        }), 400
    
    result = generate_prd(client_input, use_ai)
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "features": [
            "Domain detection",
            "Negative scope detection",
            "RMS calculation",
            "Clarification questions",
            "Conflict detection",
            "PRD generation"
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🔓 SpecForge running on http://localhost:{port}")
    app.run(debug=True, port=port, host='0.0.0.0')
