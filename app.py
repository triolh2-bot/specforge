"""
SpecForge MVP - AI Requirement Expansion Tool (Enhanced Version)
Transforms brief requirements into detailed specs with AI enhancement.
Now with MiniMax OAuth and API integration support.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import os
import re
import json
import hashlib
import time
import secrets
from functools import wraps

app = Flask(__name__)

# Secret key for sessions
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ============================================================
# MINIMAX OAUTH CONFIGURATION
# ============================================================

MINIMAX_CLIENT_ID = os.environ.get('MINIMAX_CLIENT_ID', '')
MINIMAX_CLIENT_SECRET = os.environ.get('MINIMAX_CLIENT_SECRET', '')
MINIMAX_REDIRECT_URI = os.environ.get('MINIMAX_REDIRECT_URI', 'http://localhost:5000/auth/minimax/callback')
MINIMAX_AUTH_URL = 'https://platform.minimaxi.com/oauth/authorize'
MINIMAX_TOKEN_URL = 'https://platform.minimaxi.com/oauth/token'
MINIMAX_API_BASE = 'https://api.minimaxi.com/v1'

# MiniMax API configuration
MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')

# ============================================================
# OAUTH HELPERS
# ============================================================

def generate_oauth_state():
    """Generate random state for OAuth security"""
    return secrets.token_urlsafe(32)

def get_minimax_auth_url():
    """Generate MiniMax OAuth authorization URL"""
    state = generate_oauth_state()
    session['oauth_state'] = state
    
    params = {
        'client_id': MINIMAX_CLIENT_ID,
        'redirect_uri': MINIMAX_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'api:read api:write user:read',
        'state': state
    }
    
    import urllib.parse
    return f"{MINIMAX_AUTH_URL}?{urllib.parse.urlencode(params)}"

def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    import requests
    
    data = {
        'client_id': MINIMAX_CLIENT_ID,
        'client_secret': MINIMAX_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': MINIMAX_REDIRECT_URI
    }
    
    try:
        response = requests.post(MINIMAX_TOKEN_URL, data=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Token exchange error: {e}")
        return None

def call_minimax_api(endpoint, method='GET', data=None, use_api_key=False):
    """Make API calls to MiniMax"""
    import requests
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Use API key if available
    if use_api_key and MINIMAX_API_KEY:
        headers['Authorization'] = f'Bearer {MINIMAX_API_KEY}'
    elif session.get('access_token'):
        headers['Authorization'] = f"Bearer {session.get('access_token')}"
    else:
        return None
    
    url = f"{MINIMAX_API_BASE}/{endpoint}"
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=30)
        else:
            response = requests.post(url, headers=headers, json=data, timeout=30)
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API call error: {e}")
        return None

# ============================================================
# OAUTH ROUTES
# ============================================================

@app.route('/auth/minimax')
def minimax_login():
    """Initiate MiniMax OAuth flow"""
    if not MINIMAX_CLIENT_ID:
        return jsonify({
            "success": False,
            "error": "MiniMax OAuth not configured. Set MINIMAX_CLIENT_ID environment variable."
        }), 400
    
    auth_url = get_minimax_auth_url()
    return redirect(auth_url)

@app.route('/auth/minimax/callback')
def minimax_callback():
    """Handle OAuth callback"""
    error = request.args.get('error')
    if error:
        return jsonify({"success": False, "error": error}), 400
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify state
    if state != session.get('oauth_state'):
        return jsonify({"success": False, "error": "Invalid state parameter"}), 400
    
    # Exchange code for token
    token_data = exchange_code_for_token(code)
    
    if not token_data or 'access_token' not in token_data:
        return jsonify({"success": False, "error": "Failed to obtain access token"}), 400
    
    # Store tokens in session
    session['access_token'] = token_data['access_token']
    session['refresh_token'] = token_data.get('refresh_token')
    session['token_expires_at'] = time.time() + token_data.get('expires_in', 3600)
    session['minimax_authenticated'] = True
    
    return redirect(url_for('index'))

@app.route('/auth/status')
def auth_status():
    """Check authentication status"""
    is_authenticated = session.get('minimax_authenticated', False)
    token_expires = session.get('token_expires_at', 0)
    
    return jsonify({
        "authenticated": is_authenticated,
        "provider": "minimax" if is_authenticated else None,
        "token_expires_in": max(0, int(token_expires - time.time())) if is_authenticated else 0
    })

@app.route('/auth/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('index'))

# ============================================================
# MINIMAX API ROUTES
# ============================================================

@app.route('/api/minimax/chat', methods=['POST'])
def minimax_chat():
    """Chat with MiniMax API"""
    if not MINIMAX_API_KEY and not session.get('access_token'):
        return jsonify({
            "success": False,
            "error": "Not authenticated. Use MiniMax OAuth or set MINIMAX_API_KEY"
        }), 401
    
    data = request.json
    message = data.get('message', '')
    model = data.get('model', 'abab6.5s-chat')
    
    if not message:
        return jsonify({"success": False, "error": "Message is required"}), 400
    
    # Call MiniMax API
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": message}
        ]
    }
    
    response = call_minimax_api('chat/completions', method='POST', data=payload, use_api_key=bool(MINIMAX_API_KEY))
    
    if response:
        return jsonify({
            "success": True,
            "response": response
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to get response from MiniMax"
        }), 500

@app.route('/api/minimax/enhance', methods=['POST'])
def enhance_with_minimax():
    """Enhance requirements using MiniMax AI"""
    if not MINIMAX_API_KEY and not session.get('access_token'):
        return jsonify({
            "success": False,
            "error": "MiniMax not configured. Set MINIMAX_API_KEY or authenticate via OAuth"
        }), 401
    
    data = request.json
    requirements = data.get('requirements', '')
    
    if not requirements:
        return jsonify({"success": False, "error": "Requirements are required"}), 400
    
    # Build enhancement prompt
    prompt = f"""Analyze these requirements and provide enhancement suggestions:

Requirements: {requirements}

Provide:
1. Missing technical components
2. Security considerations  
3. Scalability recommendations
4. User experience improvements
5. Potential risks

Be concise and actionable."""
    
    payload = {
        "model": "abab6.5s-chat",
        "messages": [
            {"role": "system", "content": "You are a senior software architect helping to refine project requirements."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    response = call_minimax_api('chat/completions', method='POST', data=payload, use_api_key=bool(MINIMAX_API_KEY))
    
    if response and 'choices' in response:
        return jsonify({
            "success": True,
            "enhancement": response['choices'][0]['message']['content'],
            "model": response.get('model', 'minimax')
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to get enhancement from MiniMax"
        }), 500

# ============================================================
# DECORATORS
# ============================================================

def minimax_required(f):
    """Decorator requiring MiniMax authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('minimax_authenticated') and not MINIMAX_API_KEY:
            return jsonify({
                "success": False,
                "error": "MiniMax authentication required"
            }), 401
        return f(*args, **kwargs)
    return decorated_function

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
def generate_prd(client_input, use_ai=False, ai_provider='minimax'):
    domain = detect_domain(client_input)
    missing_features = detect_missing_features(domain, client_input)
    questions = generate_questions(domain, client_input, missing_features)
    implied_users = detect_implied_users(client_input)
    conflicts = detect_conflicts(client_input)
    rms = calculate_rms(client_input, domain)
    
    # AI enhancement
    ai_enhanced = None
    if use_ai and (MINIMAX_API_KEY or session.get('minimax_authenticated')):
        # Trigger MiniMax enhancement via API
        ai_enhanced = {
            "status": "ready",
            "provider": ai_provider,
            "endpoint": "/api/minimax/enhance"
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
                    "Admin dashboard with analytics",
                    "Basic reporting"
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
        "ai_enhanced": ai_enhanced,
        "ai_providers": {
            "minimax": {
                "oauth_enabled": bool(MINIMAX_CLIENT_ID),
                "api_key_enabled": bool(MINIMAX_API_KEY),
                "models": ["abab6.5s-chat", "abab6-chat"]
            }
        }
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
    ai_provider = data.get('ai_provider', 'minimax')
    
    if not client_input or len(client_input.strip()) < 10:
        return jsonify({
            "success": False,
            "error": "Please enter at least 10 characters describing your requirements"
        }), 400
    
    result = generate_prd(client_input, use_ai, ai_provider)
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "version": "2.0.0",
        "features": [
            "Domain detection",
            "Negative scope detection",
            "RMS calculation",
            "Clarification questions",
            "Conflict detection",
            "PRD generation",
            "MiniMax OAuth authentication",
            "MiniMax API integration"
        ],
        "ai_providers": {
            "minimax": {
                "oauth_configured": bool(MINIMAX_CLIENT_ID),
                "api_key_configured": bool(MINIMAX_API_KEY)
            }
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🔓 SpecForge running on http://localhost:{port}")
    print(f"   MiniMax OAuth: {'✓' if MINIMAX_CLIENT_ID else '✗'}")
    print(f"   MiniMax API Key: {'✓' if MINIMAX_API_KEY else '✗'}")
    app.run(debug=True, port=port, host='0.0.0.0')
