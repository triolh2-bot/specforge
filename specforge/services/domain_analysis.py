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
        "saas": ["subscription", "team", "plan", "billing", "monthly", "dashboard", "software", "app"],
        "marketplace": ["marketplace", "seller", "buyer", "multiple vendors", "commission", "vendor"],
        "blog": ["blog", "article", "post", "content", "newsletter", "publish", "writer"],
        "crm": ["crm", "customer", "lead", "deal", "pipeline", "contact", "sales", "client"],
        "mobile-app": ["mobile", "ios", "android", "app", "phone", "iphone"],
        "api": ["api", "backend", "endpoint", "integration", "service"],
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
        feature_lower = feature.lower()
        feature_keywords = feature_lower.split()
        if not any(keyword in text for keyword in feature_keywords[:2]):
            missing.append(feature)

    return missing[:7]


def detect_implied_users(text):
    text = text.lower()
    users = []

    user_indicators = {
        "admin": ["admin", "administrator", "dashboard", "manage"],
        "customer": ["customer", "user", "client", "buyer", "shopper"],
        "employee": ["employee", "staff", "team", "worker"],
        "guest": ["guest", "visitor", "anonymous", "public"],
        "vendor": ["vendor", "seller", "supplier", "partner"],
    }

    for user_type, indicators in user_indicators.items():
        if any(indicator in text for indicator in indicators):
            users.append(user_type.title())

    return users if users else ["User"]


def calculate_rms(requirements, domain):
    score = 40

    if len(requirements) > 100:
        score += 20
    elif len(requirements) > 50:
        score += 15
    elif len(requirements) > 20:
        score += 10

    template = DOMAIN_TEMPLATES.get(domain, [])
    coverage = len([feature for feature in template if feature.lower() in requirements.lower()]) / len(template) if template else 0
    score += int(coverage * 15)

    key_terms = {
        "security": ["security", "auth", "password", "encryption"],
        "performance": ["performance", "speed", "load", "cache"],
        "api": ["api", "endpoint", "integration"],
        "mobile": ["mobile", "responsive", "ios", "android"],
        "admin": ["admin", "dashboard", "manage"],
    }

    for terms in key_terms.values():
        if any(term in requirements.lower() for term in terms):
            score += 5

    return min(100, score)


def generate_questions(domain, text, missing_features):
    del missing_features

    questions = []
    text_lower = text.lower()

    if "login" in text_lower or "auth" in text_lower or "sign" in text_lower:
        questions.append("What authentication methods do you need? (Password, Social login, SSO, 2FA, Magic links)")

    if "payment" in text_lower or "buy" in text_lower or "order" in text_lower or "purchase" in text_lower:
        questions.append("Which payment providers should be integrated? (Stripe, PayPal, Razorpay, etc.)")
        questions.append("Do you need support for subscriptions/recurring payments?")

    if "mobile" in text_lower or "ios" in text_lower or "android" in text_lower:
        questions.append("Do you need native mobile apps or a responsive web app?")

    questions.append("What's your expected launch timeline? (Weeks/Months)")
    questions.append("What's your approximate budget range?")

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

    return questions[:5]


def detect_conflicts(text):
    conflicts = []
    text_lower = text.lower()

    if any(word in text_lower for word in ["fast", "quick", "soon", "asap"]) and any(
        word in text_lower for word in ["complex", "advanced", "ml", "ai", "custom"]
    ):
        conflicts.append("You want quick delivery but complex features - consider prioritizing MVP features")

    if any(word in text_lower for word in ["cheap", "budget", "low cost", "free"]) and any(
        word in text_lower for word in ["professional", "enterprise", "custom"]
    ):
        conflicts.append("Budget expectations may not match enterprise feature requirements")

    if "simple" in text_lower and ("secure" in text_lower or "security" in text_lower):
        conflicts.append("Security features add complexity - balance simplicity with security needs")

    return conflicts


def generate_functional_reqs(domain, text):
    base_reqs = [
        "User registration and authentication",
        "User profile management",
        f"{domain.title()} core functionality",
        "Admin dashboard with analytics",
        "Data management (CRUD operations)",
        "Basic reporting",
    ]

    text_lower = text.lower()

    if any(word in text_lower for word in ["payment", "buy", "order", "purchase"]):
        base_reqs.extend(["Shopping cart functionality", "Payment integration", "Order history"])

    if any(word in text_lower for word in ["search", "find", "filter"]):
        base_reqs.append("Advanced search and filtering")

    if any(word in text_lower for word in ["notify", "email", "message"]):
        base_reqs.append("Notification system")

    return base_reqs[:10]
