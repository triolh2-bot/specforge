"""Domain intelligence engine — weighted scoring, phrase matching, scope inference.

Replaces simple substring heuristics with a configurable ruleset that supports:

* Weighted keyword and phrase scoring per domain
* Multi-signal confidence (primary + secondary domain detection)
* Feature-gap analysis with weighted importance
* Implied-user detection with role inference
* Scope inference (MVP / phase-growth / enterprise)
* Richer conflict and question generation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DomainRule:
    """A single weighted signal for domain detection."""

    keywords: list[str]          # All must be present (AND) or any (OR)
    match_mode: str = "any"      # "any" or "all"
    weight: float = 1.0
    label: str = ""             # Human-readable description


@dataclass(frozen=True)
class DomainProfile:
    """Complete domain configuration."""

    name: str
    display_name: str
    description: str
    detection_rules: list[DomainRule]
    feature_template: list[str]            # Expected features for gap analysis
    feature_weights: dict[str, float]       # feature_name -> importance weight
    role_indicators: dict[str, list[str]]  # role -> indicator keywords
    domain_questions: list[str]            # Questions specific to this domain
    conflict_patterns: list[tuple[str, str]]  # (trigger_a, trigger_b) -> conflict msg


# ---------------------------------------------------------------------------
# Built-in domain profiles
# ---------------------------------------------------------------------------

def _build_profiles() -> dict[str, DomainProfile]:
    """Construct the built-in domain profiles."""
    return {
        "e-commerce": DomainProfile(
            name="e-commerce",
            display_name="E-Commerce",
            description="Online store with product catalog, cart, checkout, and order management.",
            detection_rules=[
                DomainRule(keywords=["shop", "store", "bakery", "boutique"], weight=3.0, label="retail venue"),
                DomainRule(keywords=["cart", "checkout", "payment"], weight=4.0, match_mode="any", label="commerce flow"),
                DomainRule(keywords=["product", "catalog", "inventory"], weight=2.0, match_mode="any", label="catalog"),
                DomainRule(keywords=["order", "shipping", "delivery", "fulfillment"], weight=2.0, match_mode="any", label="fulfillment"),
                DomainRule(keywords=["stripe", "paypal", "razorpay", "payment gateway"], weight=3.0, match_mode="any", label="payment provider"),
                DomainRule(keywords=["ecommerce", "e-commerce", "online store", "web store"], weight=5.0, match_mode="any", label="explicit domain"),
            ],
            feature_template=[
                "Product catalog with images and variants",
                "Shopping cart with persistent sessions",
                "Checkout and payment processing",
                "Order management and tracking",
                "Inventory management with low-stock alerts",
                "User accounts and order history",
                "Product search and faceted filters",
                "Shipping rate calculation and label generation",
                "Admin dashboard with sales analytics",
                "Order confirmation and shipping notifications",
                "Discount codes and promotional campaigns",
                "Return / refund workflow",
            ],
            feature_weights={
                "catalog": 3.0, "cart": 3.0, "checkout": 4.0,
                "payment": 4.0, "inventory": 2.5, "shipping": 2.0,
                "refund": 1.5, "discount": 1.5,
            },
            role_indicators={
                "shopper": ["customer", "buyer", "shopper", "checkout"],
                "merchant": ["admin", "merchant", "store owner", "seller"],
                "warehouse": ["warehouse", "fulfillment", "shipping", "inventory"],
                "support": ["support", "refund", "return", "help"],
            },
            domain_questions=[
                "How will inventory be managed? (Manual, sync with suppliers, automated)",
                "Do you need multi-vendor marketplace support?",
                "What shipping providers will you integrate?",
                "Should customers have guest checkout or mandatory accounts?",
                "Do you need subscription / recurring billing for products?",
                "What is the expected product catalog size?",
            ],
            conflict_patterns=[
                ("fast", "complex"),
                ("cheap", "enterprise"),
            ],
        ),

        "saas": DomainProfile(
            name="saas",
            display_name="SaaS (Software as a Service)",
            description="Multi-tenant subscription software with team management and analytics.",
            detection_rules=[
                DomainRule(keywords=["subscription", "billing", "plan", "tier", "monthly"], weight=3.0, match_mode="any", label="billing model"),
                DomainRule(keywords=["team", "workspace", "organization", "tenant"], weight=2.0, match_mode="any", label="multi-tenant"),
                DomainRule(keywords=["dashboard", "analytics", "metrics", "reporting"], weight=1.5, match_mode="any", label="analytics"),
                DomainRule(keywords=["api", "integration", "webhook"], weight=1.5, match_mode="any", label="extensibility"),
                DomainRule(keywords=["saas", "software as a service", "cloud app", "hosted platform"], weight=5.0, match_mode="any", label="explicit domain"),
            ],
            feature_template=[
                "User authentication (signup/login/password reset)",
                "Subscription billing and plan management",
                "Team/workspace management",
                "Role-based access control",
                "Dashboard with usage analytics",
                "Settings and configuration panel",
                "Public API with rate limiting",
                "Usage tracking and quota enforcement",
                "Notification system (email, in-app)",
                "Support/helpdesk integration",
                "Onboarding wizard and tooltips",
                "Audit log for compliance",
            ],
            feature_weights={
                "subscription": 4.0, "team": 2.5, "rbac": 2.5,
                "analytics": 2.0, "api": 2.0, "audit": 1.5,
                "onboarding": 1.5,
            },
            role_indicators={
                "admin": ["admin", "owner", "manage", "settings"],
                "member": ["user", "member", "team member", "employee"],
                "viewer": ["viewer", "read-only", "guest", "observer"],
                "billing": ["billing", "finance", "payer", "accountant"],
            },
            domain_questions=[
                "What pricing tiers should be available? (Free, Pro, Enterprise)",
                "Do you need usage-based billing or feature-based?",
                "Should customers be able to create teams/workspaces?",
                "Is SSO / SAML required for enterprise customers?",
                "What is the target monthly recurring revenue (MRR)?",
                "Do you need a free trial or freemium model?",
            ],
            conflict_patterns=[
                ("fast", "complex"),
                ("cheap", "enterprise"),
                ("simple", "secure"),
            ],
        ),

        "marketplace": DomainProfile(
            name="marketplace",
            display_name="Marketplace",
            description="Two-sided platform connecting buyers and sellers with escrow and ratings.",
            detection_rules=[
                DomainRule(keywords=["marketplace", "platform", "two-sided"], weight=4.0, match_mode="any", label="platform type"),
                DomainRule(keywords=["seller", "buyer", "vendor", "provider"], weight=2.5, match_mode="any", label="participants"),
                DomainRule(keywords=["commission", "escrow", "payout", "payment split"], weight=3.0, match_mode="any", label="payment model"),
                DomainRule(keywords=["rating", "review", "reputation", "trust"], weight=1.5, match_mode="any", label="trust signals"),
                DomainRule(keywords=["listing", "gig", "service provider"], weight=1.5, match_mode="any", label="content type"),
            ],
            feature_template=[
                "Dual user profiles (buyers and sellers)",
                "Product/service listings with media",
                "Advanced search and filtering",
                "Messaging between users",
                "Order processing and escrow",
                "Commission and payout system",
                "Rating and review system",
                "Dispute resolution workflow",
                "Admin moderation and content policy",
                "Payment splitting (Stripe Connect, etc.)",
                "Seller onboarding and verification",
                "Geolocation and map-based search",
            ],
            feature_weights={
                "escrow": 3.5, "commission": 3.0, "messaging": 2.0,
                "rating": 2.0, "dispute": 2.5, "verification": 2.0,
            },
            role_indicators={
                "buyer": ["buyer", "customer", "consumer"],
                "seller": ["seller", "vendor", "provider", "merchant"],
                "moderator": ["moderator", "admin", "content policy"],
                "support": ["support", "dispute", "help", "resolution"],
            },
            domain_questions=[
                "How will you handle disputes between buyers and sellers?",
                "What commission rate structure do you need?",
                "Should sellers be verified before listing?",
                "Do you need geolocation-based matching?",
                "What content moderation policies are required?",
                "Will you handle payments end-to-end or connect external processors?",
            ],
            conflict_patterns=[
                ("fast", "complex"),
                ("simple", "secure"),
            ],
        ),

        "blog": DomainProfile(
            name="blog",
            display_name="Blog / Content Platform",
            description="Content publishing platform with articles, categories, and reader engagement.",
            detection_rules=[
                DomainRule(keywords=["blog", "article", "post", "content"], weight=2.5, match_mode="any", label="content type"),
                DomainRule(keywords=["publish", "editor", "writer", "author"], weight=2.0, match_mode="any", label="authoring"),
                DomainRule(keywords=["comment", "subscribe", "newsletter"], weight=1.5, match_mode="any", label="engagement"),
                DomainRule(keywords=["seo", "rss", "feed", "sitemap"], weight=1.5, match_mode="any", label="discovery"),
            ],
            feature_template=[
                "Article publishing with rich-text editor",
                "Categories, tags, and content organization",
                "Comment system with moderation",
                "User accounts and author profiles",
                "Newsletter signup and email digest",
                "Social sharing and Open Graph metadata",
                "SEO optimization (sitemaps, structured data)",
                "Full-text search",
                "Media library with image optimization",
                "Draft, schedule, and version control",
            ],
            feature_weights={
                "editor": 3.0, "comment": 2.0, "seo": 2.5,
                "newsletter": 1.5, "search": 1.5, "version": 2.0,
            },
            role_indicators={
                "author": ["author", "writer", "blogger", "contributor"],
                "editor": ["editor", "reviewer", "moderator"],
                "reader": ["reader", "subscriber", "follower"],
                "admin": ["admin", "manage", "settings"],
            },
            domain_questions=[
                "Will content be single-author or multi-contributor?",
                "Do you need a paywall or membership model?",
                "What is the expected posting frequency and volume?",
                "Should readers be able to bookmark or save articles?",
                "Do you need multilingual or localization support?",
            ],
            conflict_patterns=[
                ("simple", "secure"),
            ],
        ),

        "crm": DomainProfile(
            name="crm",
            display_name="CRM (Customer Relationship Management)",
            description="Sales pipeline and customer management with lead tracking and automation.",
            detection_rules=[
                DomainRule(keywords=["crm", "customer relationship"], weight=5.0, match_mode="any", label="explicit domain"),
                DomainRule(keywords=["lead", "deal", "opportunity", "prospect"], weight=3.0, match_mode="any", label="sales pipeline"),
                DomainRule(keywords=["pipeline", "stage", "funnel"], weight=2.5, match_mode="any", label="pipeline"),
                DomainRule(keywords=["contact", "account", "client"], weight=1.5, match_mode="any", label="contact management"),
                DomainRule(keywords=["email integration", "calendar", "activity"], weight=1.5, match_mode="any", label="activity tracking"),
                DomainRule(keywords=["sales", "forecast", "quota", "territory"], weight=2.0, match_mode="any", label="sales ops"),
            ],
            feature_template=[
                "Contact and account management",
                "Lead capture and scoring",
                "Deal pipeline with customizable stages",
                "Task and activity management",
                "Email integration (Gmail, Outlook)",
                "Reporting and sales analytics",
                "Activity timeline and notes",
                "Team collaboration and assignment",
                "Workflow automation and triggers",
                "Import/export and data migration tools",
                "Mobile access and offline mode",
                "Integration with marketing tools",
            ],
            feature_weights={
                "pipeline": 3.5, "lead": 3.0, "email": 2.0,
                "reporting": 2.5, "automation": 2.0, "integration": 1.5,
            },
            role_indicators={
                "sales_rep": ["sales rep", "account executive", "ae", "rep"],
                "manager": ["manager", "director", "vp", "forecast"],
                "admin": ["admin", "system admin", "configure"],
                "marketing": ["marketing", "campaign", "lead source"],
            },
            domain_questions=[
                "What pipeline stages do you need? (e.g., Prospecting → Qualified → Proposal → Closed)",
                "Do you need email integration? (Gmail, Outlook)",
                "What reporting features are essential? (Funnel, forecast, activity)",
                "Should leads be auto-scored based on engagement?",
                "Do you need integration with marketing platforms?",
                "How many sales reps will use the system?",
            ],
            conflict_patterns=[
                ("simple", "secure"),
                ("cheap", "enterprise"),
            ],
        ),

        "mobile-app": DomainProfile(
            name="mobile-app",
            display_name="Mobile Application",
            description="Native or cross-platform mobile app with device capabilities.",
            detection_rules=[
                DomainRule(keywords=["mobile app", "ios", "android", "iphone", "app store"], weight=3.0, match_mode="any", label="platform"),
                DomainRule(keywords=["push notification", "notification"], weight=2.0, match_mode="any", label="engagement"),
                DomainRule(keywords=["camera", "gallery", "photo", "scan"], weight=1.5, match_mode="any", label="device feature"),
                DomainRule(keywords=["location", "gps", "map", "geolocation"], weight=1.5, match_mode="any", label="location"),
                DomainRule(keywords=["offline", "sync", "cache"], weight=1.5, match_mode="any", label="offline"),
                DomainRule(keywords=["flutter", "react native", "swift", "kotlin"], weight=3.0, match_mode="any", label="framework"),
            ],
            feature_template=[
                "User authentication with biometric support",
                "Push notifications (FCM / APNs)",
                "Offline mode with local data sync",
                "Camera/gallery access for media capture",
                "Location services and maps",
                "Social sharing and deep linking",
                "In-app purchases and subscriptions",
                "Analytics and crash reporting",
                "App settings and preferences",
                "Real-time data synchronization",
                "Accessibility (VoiceOver, TalkBack)",
            ],
            feature_weights={
                "push": 2.0, "offline": 2.5, "camera": 1.5,
                "location": 1.5, "iap": 2.0, "sync": 2.0,
            },
            role_indicators={
                "user": ["user", "customer", "member"],
                "admin": ["admin", "dashboard", "manage"],
            },
            domain_questions=[
                "Do you need native iOS, Android, or cross-platform (Flutter/React Native)?",
                "Should the app work offline? What data needs local caching?",
                "Do you need push notifications or in-app messaging?",
                "Will you integrate with device features (camera, GPS, NFC)?",
                "What is the target app store launch timeline?",
            ],
            conflict_patterns=[
                ("fast", "complex"),
                ("simple", "secure"),
            ],
        ),

        "api": DomainProfile(
            name="api",
            display_name="API / Backend Service",
            description="RESTful or GraphQL API with authentication, rate limiting, and documentation.",
            detection_rules=[
                DomainRule(keywords=["api", "rest", "graphql", "grpc"], weight=3.0, match_mode="any", label="protocol"),
                DomainRule(keywords=["endpoint", "route", "handler"], weight=1.5, match_mode="any", label="routing"),
                DomainRule(keywords=["jwt", "oauth", "token", "api key"], weight=2.0, match_mode="any", label="auth"),
                DomainRule(keywords=["swagger", "openapi", "documentation"], weight=1.5, match_mode="any", label="docs"),
                DomainRule(keywords=["webhook", "callback", "event-driven"], weight=1.5, match_mode="any", label="async"),
                DomainRule(keywords=["microservice", "backend", "service"], weight=1.5, match_mode="any", label="architecture"),
            ],
            feature_template=[
                "RESTful / GraphQL endpoints with versioning",
                "Authentication (JWT, OAuth, API keys)",
                "Rate limiting and throttling",
                "Request validation and error handling",
                "API documentation (OpenAPI / Swagger)",
                "Webhook delivery with retry logic",
                "Caching layer (Redis, CDN)",
                "Monitoring, logging, and alerting",
                "Database migrations and seed data",
                "Health checks and readiness probes",
            ],
            feature_weights={
                "auth": 3.0, "rate_limit": 2.0, "validation": 2.0,
                "docs": 1.5, "webhook": 1.5, "monitoring": 2.0,
            },
            role_indicators={
                "developer": ["developer", "integration", "client app"],
                "admin": ["admin", "manage", "configure"],
            },
            domain_questions=[
                "Should the API be RESTful, GraphQL, or both?",
                "What authentication method do you prefer? (JWT, OAuth, API keys)",
                "Do you need webhook support for async events?",
                "What is the expected request volume and rate limit?",
                "Should there be a developer portal with documentation?",
            ],
            conflict_patterns=[
                ("simple", "secure"),
            ],
        ),
    }


# Module-level cache
_PROFILES: dict[str, DomainProfile] | None = None


def _get_profiles() -> dict[str, DomainProfile]:
    global _PROFILES
    if _PROFILES is None:
        _PROFILES = _build_profiles()
    return _PROFILES


def reset_profiles() -> None:
    """Reset the profile cache (useful for tests that modify profiles)."""
    global _PROFILES
    _PROFILES = None


# ---------------------------------------------------------------------------
# Domain detection — weighted multi-signal scoring
# ---------------------------------------------------------------------------

@dataclass
class DomainResult:
    """Result of domain detection."""

    primary_domain: str
    confidence: float            # 0.0 – 1.0
    all_scores: dict[str, float] # domain -> raw score
    matched_rules: dict[str, list[str]]  # domain -> list of matched rule labels


def detect_domain(text: str) -> str:
    """Return the best-matching domain name (backwards-compatible)."""
    result = detect_domain_detailed(text)
    return result.primary_domain


def detect_domain_detailed(text: str) -> DomainResult:
    """Return detailed domain detection results with confidence scores."""
    text_lower = text.lower()
    profiles = _get_profiles()
    scores: dict[str, float] = {}
    matched: dict[str, list[str]] = {}

    for name, profile in profiles.items():
        total = 0.0
        labels: list[str] = []
        for rule in profile.detection_rules:
            if rule.match_mode == "all":
                hit = all(kw in text_lower for kw in rule.keywords)
            else:
                hit = any(kw in text_lower for kw in rule.keywords)
            if hit:
                total += rule.weight
                if rule.label:
                    labels.append(rule.label)
        scores[name] = total
        matched[name] = labels

    if not scores or max(scores.values()) == 0:
        return DomainResult(primary_domain="general", confidence=0.0, all_scores=scores, matched_rules=matched)

    best_domain = max(scores, key=scores.get)
    best_score = scores[best_domain]

    # Normalize confidence: score relative to max possible for that domain
    max_possible = sum(r.weight for r in profiles[best_domain].detection_rules) if best_domain in profiles else 1
    confidence = min(1.0, best_score / max_possible) if max_possible > 0 else 0.0

    return DomainResult(
        primary_domain=best_domain,
        confidence=round(confidence, 2),
        all_scores=scores,
        matched_rules=matched,
    )


# ---------------------------------------------------------------------------
# Feature gap analysis — weighted missing-feature detection
# ---------------------------------------------------------------------------

def detect_missing_features(domain: str, text: str) -> list[str]:
    """Return missing features for the detected domain with weighted priority."""
    profiles = _get_profiles()
    profile = profiles.get(domain)
    if not profile:
        return []

    text_lower = text.lower()
    gaps: list[tuple[float, str]] = []  # (negative_weight, feature_name)

    for feature in profile.feature_template:
        feature_lower = feature.lower()
        # Check if any feature keyword appears in the text
        keywords = feature_lower.split()
        if not any(kw in text_lower for kw in keywords[:3]):
            # Find the matching feature weight
            weight = 1.0
            for key, w in profile.feature_weights.items():
                if key in feature_lower:
                    weight = w
                    break
            gaps.append((weight, feature))

    # Sort by weight (highest-weight missing features first)
    gaps.sort(key=lambda x: -x[0])
    return [feature for _, feature in gaps[:7]]


# ---------------------------------------------------------------------------
# Implied-user detection — profile-driven role inference
# ---------------------------------------------------------------------------

def detect_implied_users(text: str, domain: Optional[str] = None) -> list[str]:
    """Detect implied user roles from the text using profile-specific indicators."""
    text_lower = text.lower()
    profiles = _get_profiles()
    found: list[str] = []

    # Check domain-specific role indicators first
    if domain and domain in profiles:
        profile = profiles[domain]
        for role, indicators in profile.role_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                display_role = role.replace("_", " ").title()
                if display_role not in found:
                    found.append(display_role)

    # Fall back to generic indicators if domain-specific didn't match enough
    generic_indicators = {
        "Admin": ["admin", "administrator", "dashboard", "manage", "settings"],
        "Customer": ["customer", "user", "client", "buyer", "shopper"],
        "Employee": ["employee", "staff", "team member", "worker"],
        "Guest": ["guest", "visitor", "anonymous", "public"],
        "Vendor": ["vendor", "seller", "supplier", "partner"],
    }
    for role, indicators in generic_indicators.items():
        if any(indicator in text_lower for indicator in indicators):
            if role not in found:
                found.append(role)

    return found if found else ["User"]


# ---------------------------------------------------------------------------
# RMS (Requirements Maturity Score) — weighted scoring
# ---------------------------------------------------------------------------

def calculate_rms(requirements: str, domain: str) -> int:
    """Calculate a weighted Requirements Maturity Score (0-100)."""
    text_lower = requirements.lower()

    # 1. Completeness from text length (0-25 points)
    length_score = 0
    req_len = len(requirements)
    if req_len > 200:
        length_score = 25
    elif req_len > 100:
        length_score = 20
    elif req_len > 50:
        length_score = 15
    elif req_len > 20:
        length_score = 10

    # 2. Feature coverage against domain template (0-35 points)
    profiles = _get_profiles()
    profile = profiles.get(domain)
    feature_score = 0
    if profile:
        total_weight = sum(profile.feature_weights.values()) if profile.feature_weights else len(profile.feature_template)
        matched_weight = 0.0
        for feature in profile.feature_template:
            feature_lower = feature.lower()
            if any(kw in text_lower for kw in feature_lower.split()[:2]):
                # Find the weight for this feature
                fw = 1.0
                for key, w in profile.feature_weights.items():
                    if key in feature_lower:
                        fw = w
                        break
                matched_weight += fw
        feature_score = int((matched_weight / total_weight) * 35) if total_weight > 0 else 0

    # 3. Cross-cutting concerns (0-25 points)
    cross_cutting = {
        "security": ["security", "auth", "password", "encryption", "gdpr", "compliance"],
        "performance": ["performance", "speed", "load", "cache", "scalable"],
        "api": ["api", "endpoint", "integration", "webhook"],
        "mobile": ["mobile", "responsive", "ios", "android"],
        "admin": ["admin", "dashboard", "manage", "settings"],
        "data": ["database", "data", "backup", "migration"],
        "testing": ["test", "qa", "staging", "ci"],
    }
    cross_score = 0
    for terms in cross_cutting.values():
        if any(term in text_lower for term in terms):
            cross_score += 25 // len(cross_cutting)

    # 4. Conflict awareness (bonus 0-15 points)
    conflict_score = 0
    conflicts = detect_conflicts(requirements)
    if conflicts:
        conflict_score = min(15, len(conflicts) * 5)

    total = length_score + feature_score + cross_score + conflict_score
    return min(100, max(0, total))


# ---------------------------------------------------------------------------
# Conflict detection — pattern-based
# ---------------------------------------------------------------------------

def detect_conflicts(text: str) -> list[str]:
    """Detect conflicting or unrealistic expectations in requirements."""
    text_lower = text.lower()
    conflicts: list[str] = []
    profiles = _get_profiles()

    # Check domain-specific conflict patterns
    for profile in profiles.values():
        for trigger_a, trigger_b in profile.conflict_patterns:
            if trigger_a in text_lower and trigger_b in text_lower:
                msg = _conflict_message(trigger_a, trigger_b)
                if msg not in conflicts:
                    conflicts.append(msg)

    # Generic conflicts not covered by domain patterns
    _generic_conflicts(text_lower, conflicts)

    return conflicts


def _conflict_message(trigger_a: str, trigger_b: str) -> str:
    """Generate a human-readable conflict message."""
    templates = {
        ("fast", "complex"): "You want quick delivery but complex features — consider prioritizing MVP scope",
        ("cheap", "enterprise"): "Budget expectations may not match enterprise feature requirements",
        ("simple", "secure"): "Security features add complexity — balance simplicity with security needs",
    }
    key = (trigger_a, trigger_b)
    return templates.get(key, f"Tension detected between '{trigger_a}' and '{trigger_b}' requirements")


def _generic_conflicts(text_lower: str, conflicts: list[str]) -> None:
    """Add generic conflict messages not covered by domain patterns."""
    if "simple" in text_lower and "ai" in text_lower and "ml" in text_lower:
        conflicts.append("AI/ML features are inherently complex — 'simple' may be unrealistic for this scope")
    if ("free" in text_lower or "no cost" in text_lower) and ("custom" in text_lower or "bespoke" in text_lower):
        conflicts.append("Custom/bespoke development is not free — clarify budget expectations")
    # Fast + AI/advanced/custom tension
    if ("fast" in text_lower or "quick" in text_lower or "asap" in text_lower) and (
        "ai" in text_lower or "ml" in text_lower or "advanced" in text_lower or "custom" in text_lower
    ):
        msg = "Fast delivery with AI/advanced features is unrealistic — consider phased rollout"
        if msg not in conflicts:
            conflicts.append(msg)
    # Enterprise-grade + cheap/budget
    if ("enterprise" in text_lower or "enterprise-grade" in text_lower) and (
        "cheap" in text_lower or "low cost" in text_lower or "budget" in text_lower
    ):
        msg = "Enterprise-grade solutions require enterprise budgets — align expectations"
        if msg not in conflicts:
            conflicts.append(msg)


# ---------------------------------------------------------------------------
# Question generation — domain-specific and context-aware
# ---------------------------------------------------------------------------

def generate_questions(domain: str, text: str, missing_features: list[str]) -> list[str]:
    """Generate smart, contextual clarification questions."""
    del missing_features  # Reserved for future use
    text_lower = text.lower()
    profiles = _get_profiles()
    questions: list[str] = []

    # 1. Domain-specific questions from profile
    if domain in profiles:
        for q in profiles[domain].domain_questions:
            if q not in questions:
                questions.append(q)

    # 2. Conditional questions based on detected signals
    if "login" in text_lower or "auth" in text_lower or "sign" in text_lower:
        q = "What authentication methods do you need? (Password, Social login, SSO, 2FA, Magic links)"
        if q not in questions:
            questions.insert(0, q)

    if "payment" in text_lower or "buy" in text_lower or "order" in text_lower or "purchase" in text_lower:
        for q in [
            "Which payment providers should be integrated? (Stripe, PayPal, Razorpay, etc.)",
            "Do you need support for subscriptions or recurring payments?",
        ]:
            if q not in questions:
                questions.append(q)

    if "mobile" in text_lower or "ios" in text_lower or "android" in text_lower:
        q = "Do you need native mobile apps or a responsive web app?"
        if q not in questions:
            questions.append(q)

    # 3. Universal questions
    for q in [
        "What's your expected launch timeline? (Weeks/Months)",
        "What's your approximate budget range?",
    ]:
        if q not in questions:
            questions.append(q)

    return questions[:7]


# ---------------------------------------------------------------------------
# Functional requirements generation
# ---------------------------------------------------------------------------

def generate_functional_reqs(domain: str, text: str) -> list[str]:
    """Generate a domain-aware list of functional requirements."""
    profiles = _get_profiles()
    profile = profiles.get(domain)
    text_lower = text.lower()

    # Start with domain template features that are implied
    base_reqs: list[str] = [
        "User registration and authentication",
        "User profile management",
        f"{domain.replace('-', ' ').title()} core functionality",
        "Admin dashboard with analytics",
        "Data management (CRUD operations)",
        "Basic reporting",
    ]

    # Add profile template features that are strongly implied
    if profile:
        for feature in profile.feature_template[:4]:
            if feature not in base_reqs:
                base_reqs.append(feature)

    # Conditional features based on detected signals
    if any(w in text_lower for w in ["payment", "buy", "order", "purchase", "checkout"]):
        for r in ["Payment gateway integration", "Order history and receipt"]:
            if r not in base_reqs:
                base_reqs.append(r)

    if any(w in text_lower for w in ["search", "find", "filter", "browse"]):
        r = "Advanced search and filtering"
        if r not in base_reqs:
            base_reqs.append(r)

    if any(w in text_lower for w in ["notify", "email", "message", "alert"]):
        r = "Notification system (email, push, in-app)"
        if r not in base_reqs:
            base_reqs.append(r)

    if any(w in text_lower for w in ["report", "analytics", "metric", "chart", "graph"]):
        r = "Analytics and reporting dashboard"
        if r not in base_reqs:
            base_reqs.append(r)

    return base_reqs[:15]
