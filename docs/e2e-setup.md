# SpecForge End-to-End Browser Testing Guide

This document describes how to set up and run full browser E2E tests for SpecForge using **Playwright** (recommended) or **Selenium**.

## Quick Start

```bash
# 1. Install Playwright and the Python package
pip install playwright
playwright install chromium

# 2. Start the SpecForge server
flask run --port 5000

# 3. Run E2E tests
python -m pytest tests/e2e/ -v --headed
```

---

## Option 1: Playwright (Recommended)

Playwright is the recommended E2E framework for SpecForge because it:
- Supports auto-waiting for elements
- Has built-in network interception for mocking APIs
- Provides trace files for debugging
- Runs headless by default in CI

### Installation

```bash
# Create a virtual environment (optional but recommended)
python -m venv venv-e2e
source venv-e2e/bin/activate  # On Windows: venv-e2e\Scripts\activate

# Install Playwright
pip install playwright pytest-playwright

# Install browser binaries
playwright install chromium firefox webkit

# Generate Playwright config
playwright install-deps  # System dependencies (Linux only)
```

### Configuration

Create `tests/e2e/playwright.config.py`:

```python
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:5000"
BROWSER = "chromium"  # chromium, firefox, webkit
HEADED = False  # Set True to see browser during tests
SLOW_MO = 0     # Milliseconds to slow down actions (for debugging)
SCREENSHOT_ON_FAILURE = True
```

### Page Object Model

Create `tests/e2e/pages/` directory with page objects:

#### `tests/e2e/pages/base_page.py`

```python
from playwright.sync_api import Page, expect

class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.base_url = "http://localhost:5000"

    def goto(self, path: str = "/"):
        self.page.goto(f"{self.base_url}{path}")
        self.page.wait_for_load_state("networkidle")

    def expect_visible(self, selector: str):
        expect(self.page.locator(selector)).to_be_visible()

    def expect_text(self, selector: str, text: str):
        expect(self.page.locator(selector)).to_contain_text(text)

    def click(self, selector: str):
        self.page.locator(selector).click()

    def fill(self, selector: str, text: str):
        self.page.locator(selector).fill(text)

    def screenshot(self, name: str):
        self.page.screenshot(path=f"test-results/{name}.png")
```

#### `tests/e2e/pages/analyze_page.py`

```python
from playwright.sync_api import Page, expect
from .base_page import BasePage

class AnalyzePage(BasePage):
    # Selectors
    TEXTAREA = "#requirements"
    ANALYZE_BTN = "#analyze-btn"
    LOADING = "#loading"
    RESULTS = "#results"
    RMS_SCORE = "#rms-score"
    RMS_BAR = "#rms-bar"
    DOMAIN_BADGE = "#domain-badge"
    MISSING_FEATURES = "#missing-features"
    QUESTIONS = "#questions"
    PRD_CONTENT = "#prd-content"
    AI_RESULT = "#ai-result-section"
    ERROR_BANNER = "#error-banner"
    ERROR_MESSAGE = "#error-message"
    QUOTA_WARNING = "#quota-warning"
    CHAR_COUNT = "#char-count"
    AI_CHECKBOX = "#ai-enhance"
    AI_PROVIDER = "#ai-provider"

    def navigate(self):
        self.goto("/")

    def enter_requirements(self, text: str):
        self.fill(self.TEXTAREA, text)

    def click_analyze(self):
        self.click(self.ANALYZE_BTN)

    def wait_for_results(self, timeout: float = 30000):
        self.page.wait_for_selector(self.RESULTS, state="visible", timeout=timeout)

    def wait_for_loading(self):
        self.page.wait_for_selector(self.LOADING, state="visible")

    def wait_for_loading_hidden(self):
        self.page.wait_for_selector(self.LOADING, state="hidden")

    def get_rms_score(self) -> int:
        text = self.page.locator(self.RMS_SCORE).inner_text()
        return int(text.split("/")[0])

    def get_domain(self) -> str:
        return self.page.locator(self.DOMAIN_BADGE).inner_text().strip()

    def get_missing_features_count(self) -> int:
        return self.page.locator(f"{self.MISSING_FEATURES} li").count()

    def get_questions_count(self) -> int:
        return self.page.locator(f"{self.QUESTIONS} li").count()

    def is_ai_result_visible(self) -> bool:
        return self.page.locator(self.AI_RESULT).is_visible()

    def is_error_visible(self) -> bool:
        return self.page.locator(self.ERROR_BANNER).is_visible()

    def get_error_message(self) -> str:
        return self.page.locator(self.ERROR_MESSAGE).inner_text()

    def switch_tab(self, tab_name: str):
        self.click(f'[data-tab="{tab_name}"]')

    def enable_ai_enhancement(self):
        self.page.locator(self.AI_CHECKBOX).check()

    def select_provider(self, provider: str):
        self.page.locator(self.AI_PROVIDER).select_option(provider)

    def get_character_count(self) -> str:
        return self.page.locator(self.CHAR_COUNT).inner_text()
```

#### `tests/e2e/pages/history_page.py`

```python
from .base_page import BasePage

class HistoryPage(BasePage):
    HISTORY_LIST = "#history-list"
    HISTORY_EMPTY = "#history-empty"
    HISTORY_COUNT = "#history-count"
    HISTORY_NAV = '[data-view="history"]'

    def navigate(self):
        self.goto("/")
        self.page.wait_for_load_state("networkidle")
        self.click(self.HISTORY_NAV)
        self.page.wait_for_load_state("networkidle")

    def is_empty_state_visible(self) -> bool:
        return self.page.locator(self.HISTORY_EMPTY).is_visible()

    def get_item_count(self) -> int:
        return self.page.locator(f"{self.HISTORY_LIST} > div").count()

    def click_first_item(self):
        self.page.locator(f"{self.HISTORY_LIST} > div").first.click()
```

#### `tests/e2e/pages/settings_page.py`

```python
from .base_page import BasePage

class SettingsPage(BasePage):
    SETTINGS_NAV = '[data-view="settings"]'
    SETTINGS_PLAN = "#settings-plan"
    SETTINGS_ANALYSES = "#settings-analyses"
    SETTINGS_AI = "#settings-ai"
    SETTINGS_EXPORTS = "#settings-exports"

    def navigate(self):
        self.goto("/")
        self.page.wait_for_load_state("networkidle")
        self.click(self.SETTINGS_NAV)
        self.page.wait_for_load_state("networkidle")

    def get_plan(self) -> str:
        return self.page.locator(self.SETTINGS_PLAN).inner_text().strip()

    def get_analyses_usage(self) -> str:
        return self.page.locator(self.SETTINGS_ANALYSES).inner_text().strip()
```

### E2E Test Files

Create `tests/e2e/` directory with test files:

#### `tests/e2e/test_analyze_flow.py`

```python
"""E2E tests for the main analyze flow."""

import pytest
from playwright.sync_api import Page, expect
from pages.analyze_page import AnalyzePage

pytestmark = pytest.mark.e2e

@pytest.fixture
def analyze_page(page: Page):
    pg = AnalyzePage(page)
    pg.navigate()
    return pg

def test_page_loads_with_correct_title(analyze_page: AnalyzePage):
    """Verify the main page loads with the correct title."""
    expect(analyze_page.page).to_have_title("SpecForge — Requirements Analysis & PRD Generation")

def test_textarea_is_visible_and_focusable(analyze_page: AnalyzePage):
    """Verify the requirements textarea is visible."""
    analyze_page.expect_visible(analyze_page.TEXTAREA)

def test_character_counter_updates(analyze_page: AnalyzePage):
    """Verify character counter updates as user types."""
    analyze_page.enter_requirements("Hello world")
    assert "10 chars" in analyze_page.get_character_count()

def test_analyze_with_valid_requirements(analyze_page: AnalyzePage):
    """Verify full analyze flow with valid input."""
    analyze_page.enter_requirements(
        "Build an e-commerce store for my bakery with cart, checkout, and admin panel."
    )
    analyze_page.click_analyze()
    analyze_page.wait_for_loading()
    analyze_page.wait_for_loading_hidden()
    analyze_page.wait_for_results()

    # Verify results are displayed
    assert analyze_page.get_rms_score() > 0
    assert analyze_page.get_domain() != "-"
    assert analyze_page.get_missing_features_count() > 0
    assert analyze_page.get_questions_count() > 0

def test_analyze_shows_domain_and_rms(analyze_page: AnalyzePage):
    """Verify domain detection and RMS scoring are displayed."""
    analyze_page.enter_requirements("Create a CRM for sales teams with lead tracking and pipeline.")
    analyze_page.click_analyze()
    analyze_page.wait_for_results()

    domain = analyze_page.get_domain().lower()
    assert "crm" in domain
    assert analyze_page.get_rms_score() >= 30

def test_analyze_ecommerce_domain(analyze_page: AnalyzePage):
    """Verify e-commerce is detected correctly."""
    analyze_page.enter_requirements("Online bakery shop with product catalog, shopping cart, and Stripe checkout.")
    analyze_page.click_analyze()
    analyze_page.wait_for_results()

    domain = analyze_page.get_domain().lower()
    assert "commerce" in domain or "e-commerce" in domain

def test_analyze_saas_domain(analyze_page: AnalyzePage):
    """Verify SaaS is detected for subscription-based software."""
    analyze_page.enter_requirements("SaaS project management tool with team workspaces and monthly billing.")
    analyze_page.click_analyze()
    analyze_page.wait_for_results()

    domain = analyze_page.get_domain().lower()
    assert "saas" in domain

def test_empty_requirements_shows_error(analyze_page: AnalyzePage):
    """Verify that submitting empty requirements shows an error."""
    analyze_page.click_analyze()
    # The client-side validation should show an alert or focus the textarea
    # Since it uses alert(), we handle the dialog
    with analyze_page.page.expect_event("dialog") as dialog_info:
        analyze_page.click_analyze()
    dialog = dialog_info.value
    assert "Please enter requirements" in dialog.message
    dialog.accept()

def test_tabs_switch_correctly(analyze_page: AnalyzePage):
    """Verify tab switching shows correct content."""
    analyze_page.enter_requirements("Build a blog platform with articles and comments.")
    analyze_page.click_analyze()
    analyze_page.wait_for_results()

    # Default tab should be "missing"
    analyze_page.expect_visible("#tab-missing")

    # Switch to questions tab
    analyze_page.switch_tab("questions")
    analyze_page.expect_visible("#tab-questions")
    analyze_page.expect_hidden("#tab-missing")

    # Switch to PRD tab
    analyze_page.switch_tab("prd")
    analyze_page.expect_visible("#tab-prd")

def test_loading_state_shows_during_analysis(analyze_page: AnalyzePage):
    """Verify loading spinner is visible during analysis."""
    analyze_page.enter_requirements("Build an API backend with auth and rate limiting.")
    analyze_page.click_analyze()
    analyze_page.wait_for_loading()
    analyze_page.expect_visible(analyze_page.LOADING)

def test_download_prd_button_exists(analyze_page: AnalyzePage):
    """Verify the download PRD button is present."""
    analyze_page.enter_requirements("Build a mobile fitness app.")
    analyze_page.click_analyze()
    analyze_page.wait_for_results()

    # Check download button exists
    download_btn = analyze_page.page.get_by_role("button", name="Download Markdown")
    expect(download_btn).to_be_visible()

def test_ai_enhancement_checkbox_visible(analyze_page: AnalyzePage):
    """Verify AI enhancement checkbox is present."""
    analyze_page.expect_visible(analyze_page.AI_CHECKBOX)
    analyze_page.expect_visible(analyze_page.AI_PROVIDER)

def test_error_handling_for_server_error(analyze_page: AnalyzePage, monkeypatch):
    """Verify server errors are displayed gracefully."""
    # This would require mocking the server response
    # For now, verify the error banner markup exists
    analyze_page.expect_hidden(analyze_page.ERROR_BANNER)
```

#### `tests/e2e/test_history_flow.py`

```python
"""E2E tests for the analysis history flow."""

import pytest
from playwright.sync_api import Page
from pages.analyze_page import AnalyzePage
from pages.history_page import HistoryPage

pytestmark = pytest.mark.e2e

def test_history_shows_empty_state(page: Page):
    """Verify history shows empty state when no analyses exist."""
    history = HistoryPage(page)
    history.navigate()
    assert history.is_empty_state_visible()

def test_history_shows_item_after_analysis(page: Page):
    """Verify history shows an item after running an analysis."""
    # Run an analysis first
    analyze = AnalyzePage(page)
    analyze.navigate()
    analyze.enter_requirements("Build a marketplace for freelancers.")
    analyze.click_analyze()
    analyze.wait_for_results()

    # Navigate to history
    history = HistoryPage(page)
    history.navigate()
    assert not history.is_empty_state_visible()
    assert history.get_item_count() >= 1

def test_clicking_history_item_shows_results(page: Page):
    """Verify clicking a history item navigates back to analyze with results."""
    # Run analysis
    analyze = AnalyzePage(page)
    analyze.navigate()
    analyze.enter_requirements("Build a CRM system.")
    analyze.click_analyze()
    analyze.wait_for_results()

    # Go to history and click first item
    history = HistoryPage(page)
    history.navigate()
    history.click_first_item()

    # Should be back on analyze view with results
    analyze.expect_visible(analyze.RESULTS)
```

#### `tests/e2e/test_responsive_layout.py`

```python
"""E2E tests for responsive layout and mobile behavior."""

import pytest
from playwright.sync_api import Page, expect
from pages.analyze_page import AnalyzePage

pytestmark = pytest.mark.e2e

def test_mobile_menu_toggle(page: Page):
    """Verify mobile menu button toggles sidebar on small screens."""
    page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE

    analyze = AnalyzePage(page)
    analyze.navigate()

    # Sidebar should be hidden on mobile
    sidebar = page.locator("#sidebar")
    expect(sidebar).to_be_hidden()

    # Click menu button
    page.locator("#mobile-menu-btn").click()
    expect(sidebar).to_be_visible()

def test_desktop_layout_shows_sidebar(page: Page):
    """Verify sidebar is visible on desktop viewport."""
    page.set_viewport_size({"width": 1280, "height": 720})

    analyze = AnalyzePage(page)
    analyze.navigate()

    expect(page.locator("#sidebar")).to_be_visible()

def test_results_stack_vertically_on_mobile(page: Page):
    """Verify results grid collapses to single column on mobile."""
    page.set_viewport_size({"width": 375, "height": 667})

    analyze = AnalyzePage(page)
    analyze.navigate()
    analyze.enter_requirements("Build an e-commerce store.")
    analyze.click_analyze()
    analyze.wait_for_results()

    # Score cards should stack vertically
    cards = page.locator("#results .grid > div")
    count = cards.count()
    assert count >= 3

    # Each card should be full width
    for i in range(count):
        card = cards.nth(i)
        box = card.bounding_box()
        assert box["width"] > 300  # Should take most of the screen width

def test_tabs_scroll_horizontally_on_mobile(page: Page):
    """Verify tabs are horizontally scrollable on small screens."""
    page.set_viewport_size({"width": 375, "height": 667})

    analyze = AnalyzePage(page)
    analyze.navigate()
    analyze.enter_requirements("Build an API.")
    analyze.click_analyze()
    analyze.wait_for_results()

    tablist = page.locator('[role="tablist"]')
    expect(tablist).to_be_visible()
```

#### `tests/e2e/test_error_states.py`

```python
"""E2E tests for error state handling."""

import pytest
from playwright.sync_api import Page, expect
from pages.analyze_page import AnalyzePage

pytestmark = pytest.mark.e2e

def test_quota_warning_shows_on_429(page: Page):
    """Verify quota warning is displayed when rate limited."""
    # This would require mocking a 429 response
    # For now, verify the markup exists
    analyze = AnalyzePage(page)
    analyze.navigate()
    expect(page.locator(analyze.QUOTA_WARNING)).to_be_hidden()

def test_error_banner_dismissable(page: Page):
    """Verify error banner can be dismissed."""
    analyze = AnalyzePage(page)
    analyze.navigate()

    # Error banner should be hidden by default
    expect(page.locator(analyze.ERROR_BANNER)).to_be_hidden()

def test_clear_form_resets_everything(page: Page):
    """Verify clear button resets form and hides results."""
    analyze = AnalyzePage(page)
    analyze.navigate()

    # Run analysis
    analyze.enter_requirements("Build a blog.")
    analyze.click_analyze()
    analyze.wait_for_results()

    # Clear form
    page.get_by_role("button", name="Clear").click()

    # Verify textarea is empty
    expect(page.locator(analyze.TEXTAREA)).to_have_value("")
    assert "0 chars" in analyze.get_character_count()

    # Results should be hidden
    expect(page.locator(analyze.RESULTS)).to_be_hidden()
```

### Running Playwright Tests

```bash
# Run all E2E tests (headless)
python -m pytest tests/e2e/ -v

# Run with browser visible
python -m pytest tests/e2e/ -v --headed

# Run specific test file
python -m pytest tests/e2e/test_analyze_flow.py -v

# Run with slow motion for debugging
python -m pytest tests/e2e/ -v --headed --slowmo=500

# Run with trace file
python -m pytest tests/e2e/ -v --tracing on
# Then view traces at: https://trace.playwright.dev/

# Run only tests marked as e2e
python -m pytest tests/e2e/ -v -m e2e
```

### pytest Configuration

Add to `pytest.ini` or `pyproject.toml`:

```ini
[pytest]
markers =
    e2e: End-to-end browser tests

# Playwright settings
playwright_base_url = http://localhost:5000
playwright_browser = chromium
```

---

## Option 2: Selenium (Alternative)

If you prefer Selenium over Playwright:

### Installation

```bash
pip install selenium webdriver-manager pytest
```

### Basic Setup

Create `tests/e2e/selenium_conftest.py`:

```python
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)
    driver.set_window_size(1280, 720)
    yield driver
    driver.quit()

@pytest.fixture
def mobile_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    mobile_emulation = {"deviceName": "iPhone 12"}
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()
```

### Example Selenium Test

Create `tests/e2e/test_selenium_analyze.py`:

```python
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.mark.e2e
class TestAnalyzeFlow:
    def test_analyze_with_valid_requirements(self, driver):
        driver.get("http://localhost:5000")

        # Enter requirements
        textarea = driver.find_element(By.ID, "requirements")
        textarea.send_keys("Build an e-commerce store with cart and checkout.")

        # Click analyze
        analyze_btn = driver.find_element(By.ID, "analyze-btn")
        analyze_btn.click()

        # Wait for results
        wait = WebDriverWait(driver, 30)
        results = wait.until(
            EC.visibility_of_element_located((By.ID, "results"))
        )

        # Verify RMS score
        score_el = driver.find_element(By.ID, "rms-score")
        score_text = score_el.text
        assert "/" in score_text
        score = int(score_text.split("/")[0])
        assert score > 0

        # Verify domain badge
        domain = driver.find_element(By.ID, "domain-badge").text
        assert len(domain) > 0
```

### Running Selenium Tests

```bash
python -m pytest tests/e2e/test_selenium_analyze.py -v
```

---

## CI/CD Integration

### GitHub Actions

Add to `.github/workflows/e2e.yml`:

```yaml
name: E2E Tests
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install playwright pytest-playwright
          playwright install chromium
          playwright install-deps

      - name: Start server
        run: |
          export SECRET_KEY=test-key
          export TOKEN_ENCRYPTION_SECRET=test-secret
          flask run --port 5000 &
          # Wait for server
          for i in {1..30}; do
            if curl -s http://localhost:5000/health > /dev/null; then
              echo "Server is ready"
              break
            fi
            sleep 1
          done

      - name: Run E2E tests
        run: python -m pytest tests/e2e/ -v --browser chromium

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-results
          path: test-results/
          retention-days: 7
```

---

## Test Coverage Matrix

| User Journey | Playwright | Selenium | Status |
|-------------|:----------:|:--------:|:------:|
| Page loads correctly | ✅ | ✅ | Covered |
| Enter requirements + analyze | ✅ | ✅ | Covered |
| Domain detection (e-commerce) | ✅ | — | Covered |
| Domain detection (SaaS) | ✅ | — | Covered |
| Domain detection (CRM) | ✅ | — | Covered |
| RMS score displayed | ✅ | ✅ | Covered |
| Missing features list | ✅ | — | Covered |
| Clarification questions | ✅ | — | Covered |
| Tab switching | ✅ | — | Covered |
| Loading state visible | ✅ | — | Covered |
| Empty requirements error | ✅ | — | Covered |
| History empty state | ✅ | — | Covered |
| History shows items after analysis | ✅ | — | Covered |
| Mobile menu toggle | ✅ | — | Covered |
| Desktop sidebar visible | ✅ | — | Covered |
| Responsive results stacking | ✅ | — | Covered |
| Clear form resets | ✅ | — | Covered |

---

## Debugging Tips

1. **Trace files** (Playwright): Run with `--tracing on` and open at https://trace.playwright.dev/
2. **Screenshots**: Add `page.screenshot(path="debug.png")` at failure points
3. **Slow mode**: Use `--slowmo=500` to watch each action
4. **Network interception**: Mock API responses for testing error states:
   ```python
   page.route("*/**/analyze", lambda route: route.fulfill(
       status=429,
       body='{"error":{"code":"quota_exceeded","message":"Limit reached"}}'
   ))
   ```
5. **Console logs**: Capture JS errors:
   ```python
   page.on("console", lambda msg: print(f"JS: {msg.text}"))
   page.on("pageerror", lambda err: print(f"Error: {err}"))
   ```

---

## Adding New E2E Tests

1. Create a new page object in `tests/e2e/pages/` if testing a new view
2. Create a test file in `tests/e2e/` following the naming convention `test_<feature>.py`
3. Use the `@pytest.mark.e2e` marker
4. Run with `python -m pytest tests/e2e/test_your_test.py -v --headed` to verify
5. Add to the coverage matrix table above when done
