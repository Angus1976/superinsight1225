"""
Frontend Page Load Time Measurement Module.

This module provides utilities for measuring frontend page load performance
and tracking performance metrics over time.

**Validates: Requirements 13.4**
**Validates: Property 31**
"""

import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class PageLoadMetrics:
    """Metrics for a single page load."""
    page_name: str
    url: str
    load_time_ms: float
    dom_content_loaded_ms: float
    first_contentful_paint_ms: float
    largest_contentful_paint_ms: float
    time_to_interactive_ms: float
    first_byte_ms: float
    connection_time_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @property
    def is_healthy(self) -> bool:
        """Check if page load metrics are within acceptable range."""
        return (
            self.load_time_ms < 3000 and  # < 3s total load
            self.largest_contentful_paint_ms < 2500 and  # < 2.5s LCP
            self.time_to_interactive_ms < 3500  # < 3.5s TTI
        )
    
    @property
    def performance_score(self) -> int:
        """Calculate a performance score (0-100)."""
        score = 100
        
        # Deduct for slow LCP
        if self.largest_contentful_paint_ms > 2500:
            score -= min(30, int((self.largest_contentful_paint_ms - 2500) / 100))
        
        # Deduct for slow TTI
        if self.time_to_interactive_ms > 3500:
            score -= min(20, int((self.time_to_interactive_ms - 3500) / 100))
        
        # Deduct for slow load
        if self.load_time_ms > 3000:
            score -= min(20, int((self.load_time_ms - 3000) / 100))
        
        return max(0, score)


@dataclass
class FrontendPerformanceReport:
    """Complete frontend performance report."""
    timestamp: str
    browser: str
    pages: Dict[str, PageLoadMetrics]
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_summary(self):
        """Calculate summary statistics."""
        pages = list(self.pages.values())
        
        if not pages:
            self.summary = {"error": "No page data"}
            return
        
        healthy_count = sum(1 for p in pages if p.is_healthy)
        scores = [p.performance_score for p in pages]
        
        self.summary = {
            "total_pages": len(pages),
            "healthy_pages": healthy_count,
            "unhealthy_pages": len(pages) - healthy_count,
            "health_rate": round(healthy_count / len(pages) * 100, 2),
            "avg_performance_score": round(sum(scores) / len(scores), 2),
            "min_score": min(scores),
            "max_score": max(scores),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        self.calculate_summary()
        return {
            "timestamp": self.timestamp,
            "browser": self.browser,
            "pages": {
                name: {
                    "page_name": metrics.page_name,
                    "url": metrics.url,
                    "load_time_ms": round(metrics.load_time_ms, 2),
                    "dom_content_loaded_ms": round(metrics.dom_content_loaded_ms, 2),
                    "first_contentful_paint_ms": round(metrics.first_contentful_paint_ms, 2),
                    "largest_contentful_paint_ms": round(metrics.largest_contentful_paint_ms, 2),
                    "time_to_interactive_ms": round(metrics.time_to_interactive_ms, 2),
                    "first_byte_ms": round(metrics.first_byte_ms, 2),
                    "connection_time_ms": round(metrics.connection_time_ms, 2),
                    "timestamp": metrics.timestamp,
                    "is_healthy": metrics.is_healthy,
                    "performance_score": metrics.performance_score,
                }
                for name, metrics in self.pages.items()
            },
            "summary": self.summary,
        }


# =============================================================================
# Browser Performance Measurement (Playwright)
# =============================================================================

try:
    from playwright.sync_api import sync_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class FrontendPerformanceMeasurer:
    """Measures frontend page load performance using Playwright."""
    
    def __init__(self, browser: str = "chromium", headless: bool = True):
        self.browser = browser
        self.headless = headless
        self.results: Dict[str, PageLoadMetrics] = {}
    
    def measure_page(
        self,
        page_name: str,
        url: str,
        wait_until: str = "networkidle"
    ) -> PageLoadMetrics:
        """
        Measure page load performance.
        
        Args:
            page_name: Name to identify the page
            url: URL to measure
            wait_until: Wait condition (load, domcontentloaded, networkidle, commit)
            
        Returns:
            PageLoadMetrics with performance data
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is not installed. Run: pip install playwright")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            
            # Start performance tracking
            performance_entries = []
            
            def handle_console(msg):
                if msg.type == "log":
                    try:
                        data = json.loads(msg.text)
                        if data.get("type") == "performance_entry":
                            performance_entries.append(data)
                    except (json.JSONDecodeError, AttributeError):
                        pass
            
            page.on("console", handle_console)
            
            # Navigate and measure
            start_time = time.perf_counter()
            
            try:
                page.goto(url, wait_until=wait_until, timeout=30000)
            except Exception:
                pass
            
            end_time = time.perf_counter()
            load_time_ms = (end_time - start_time) * 1000
            
            # Get performance metrics from browser
            dom_content_loaded = page.evaluate("() => performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart")
            first_contentful_paint = page.evaluate("""() => {
                const paint = performance.getEntriesByType('paint').find(e => e.name === 'first-contentful-paint');
                return paint ? paint.startTime : 0;
            }""")
            
            # Calculate LCP (simplified)
            lcp = page.evaluate("""() => {
                const entries = performance.getEntriesByType('largest-contentful-paint');
                return entries.length > 0 ? entries[entries.length - 1].startTime : 0;
            }""")
            
            # Calculate TTI (simplified)
            tti = page.evaluate("""() => {
                // Simplified TTI calculation
                const timing = performance.timing;
                return timing.domInteractive - timing.navigationStart;
            }""")
            
            # First byte time
            first_byte = page.evaluate("""() => {
                const timing = performance.timing;
                return timing.responseStart - timing.requestStart;
            }""")
            
            # Connection time
            connection_time = page.evaluate("""() => {
                const timing = performance.timing;
                return timing.secureConnectionStart > 0 
                    ? timing.connectStart - timing.secureConnectionStart
                    : timing.connectEnd - timing.connectStart;
            }""")
            
            browser.close()
            
            return PageLoadMetrics(
                page_name=page_name,
                url=url,
                load_time_ms=load_time_ms,
                dom_content_loaded_ms=dom_content_loaded or 0,
                first_contentful_paint_ms=first_contentful_paint or 0,
                largest_contentful_paint_ms=lcp or 0,
                time_to_interactive_ms=tti or 0,
                first_byte_ms=first_byte or 0,
                connection_time_ms=connection_time or 0,
            )
    
    def measure_multiple_pages(
        self,
        pages: List[Dict[str, str]],
        delay_ms: int = 500
    ) -> Dict[str, PageLoadMetrics]:
        """
        Measure multiple pages.
        
        Args:
            pages: List of {name, url} dictionaries
            delay_ms: Delay between page measurements
            
        Returns:
            Dictionary of page name to metrics
        """
        results = {}
        
        for page_info in pages:
            name = page_info["name"]
            url = page_info["url"]
            
            try:
                metrics = self.measure_page(name, url)
                results[name] = metrics
                print(f"  {name}: {metrics.load_time_ms:.0f}ms (LCP: {metrics.largest_contentful_paint_ms:.0f}ms)")
            except Exception as e:
                print(f"  {name}: FAILED - {e}")
            
            time.sleep(delay_ms / 1000)
        
        self.results = results
        return results
    
    def get_report(self, browser: str = "chromium") -> FrontendPerformanceReport:
        """Generate a complete report."""
        return FrontendPerformanceReport(
            timestamp=datetime.utcnow().isoformat(),
            browser=browser,
            pages=self.results,
        )


# =============================================================================
# Frontend Performance Thresholds
# =============================================================================

class FrontendPerformanceThresholds:
    """Performance thresholds for frontend pages."""
    
    # Thresholds in milliseconds
    LOAD_TIME_MAX_MS = 3000
    LCP_MAX_MS = 2500
    FCP_MAX_MS = 1800
    TTI_MAX_MS = 3500
    DOM_CONTENT_LOADED_MAX_MS = 1500
    
    # Performance score thresholds
    EXCELLENT_SCORE = 90
    GOOD_SCORE = 70
    NEEDS_IMPROVEMENT_SCORE = 50
    
    @classmethod
    def validate_page(cls, metrics: PageLoadMetrics) -> tuple[bool, List[str]]:
        """Validate a page against thresholds."""
        violations = []
        
        if metrics.load_time_ms > cls.LOAD_TIME_MAX_MS:
            violations.append(
                f"Load time {metrics.load_time_ms:.0f}ms exceeds {cls.LOAD_TIME_MAX_MS}ms"
            )
        
        if metrics.largest_contentful_paint_ms > cls.LCP_MAX_MS:
            violations.append(
                f"LCP {metrics.largest_contentful_paint_ms:.0f}ms exceeds {cls.LCP_MAX_MS}ms"
            )
        
        if metrics.first_contentful_paint_ms > cls.FCP_MAX_MS:
            violations.append(
                f"FCP {metrics.first_contentful_paint_ms:.0f}ms exceeds {cls.FCP_MAX_MS}ms"
            )
        
        if metrics.time_to_interactive_ms > cls.TTI_MAX_MS:
            violations.append(
                f"TTI {metrics.time_to_interactive_ms:.0f}ms exceeds {cls.TTI_MAX_MS}ms"
            )
        
        return len(violations) == 0, violations
    
    @classmethod
    def get_performance_rating(cls, score: int) -> str:
        """Get performance rating based on score."""
        if score >= cls.EXCELLENT_SCORE:
            return "Excellent"
        elif score >= cls.GOOD_SCORE:
            return "Good"
        elif score >= cls.NEEDS_IMPROVEMENT_SCORE:
            return "Needs Improvement"
        else:
            return "Poor"


# =============================================================================
# Frontend Baseline Comparison
# =============================================================================

class FrontendBaselineManager:
    """Manages frontend performance baselines."""
    
    def __init__(self, baseline_dir: str = "tests/performance/frontend_baselines"):
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
    
    def save_baseline(
        self,
        name: str,
        report: FrontendPerformanceReport
    ) -> str:
        """Save current metrics as baseline."""
        baseline = {
            "name": name,
            "created_at": report.timestamp,
            "browser": report.browser,
            "pages": {},
        }
        
        for name, metrics in report.pages.items():
            baseline["pages"][name] = {
                "load_time_ms": metrics.load_time_ms,
                "lcp_ms": metrics.largest_contentful_paint_ms,
                "fcp_ms": metrics.first_contentful_paint_ms,
                "tti_ms": metrics.time_to_interactive_ms,
                "performance_score": metrics.performance_score,
            }
        
        filepath = self.baseline_dir / f"{name}.json"
        with open(filepath, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        return str(filepath)
    
    def load_baseline(self, name: str) -> Optional[Dict]:
        """Load a baseline by name."""
        filepath = self.baseline_dir / f"{name}.json"
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def compare(
        self,
        current_report: FrontendPerformanceReport,
        baseline_name: str
    ) -> Dict[str, Any]:
        """Compare current performance against baseline."""
        baseline = self.load_baseline(baseline_name)
        
        if not baseline:
            return {"error": f"Baseline '{baseline_name}' not found"}
        
        comparison = {
            "baseline_name": baseline_name,
            "baseline_created_at": baseline.get("created_at"),
            "comparison_time": current_report.timestamp,
            "page_comparisons": [],
            "degradations": [],
            "improvements": [],
        }
        
        for name, current in current_report.pages.items():
            if name in baseline.get("pages", {}):
                base = baseline["pages"][name]
                
                base_lcp = base.get("lcp_ms", 0)
                current_lcp = current.largest_contentful_paint_ms
                
                if base_lcp > 0:
                    lcp_degradation = (current_lcp - base_lcp) / base_lcp
                else:
                    lcp_degradation = 0 if current_lcp == 0 else 1.0
                
                page_comparison = {
                    "page": name,
                    "baseline_lcp_ms": base_lcp,
                    "current_lcp_ms": round(current_lcp, 2),
                    "lcp_degradation_percent": round(lcp_degradation * 100, 2),
                    "baseline_score": base.get("performance_score", 0),
                    "current_score": current.performance_score,
                    "passed": lcp_degradation <= 0.20,
                }
                
                comparison["page_comparisons"].append(page_comparison)
                
                if lcp_degradation > 0.20:
                    comparison["degradations"].append(page_comparison)
                elif lcp_degradation < -0.10:
                    comparison["improvements"].append(page_comparison)
        
        return comparison


# =============================================================================
# Common Frontend Pages
# =============================================================================

def get_common_pages(base_url: str) -> List[Dict[str, str]]:
    """Get list of common frontend pages to measure."""
    return [
        {"name": "home", "url": f"{base_url}/"},
        {"name": "login", "url": f"{base_url}/login"},
        {"name": "dashboard", "url": f"{base_url}/dashboard"},
        {"name": "tasks", "url": f"{base_url}/tasks"},
        {"name": "annotations", "url": f"{base_url}/annotations"},
        {"name": "exports", "url": f"{base_url}/exports"},
    ]


# =============================================================================
# CLI Interface
# =============================================================================

def measure_frontend_performance(
    base_url: str,
    pages: List[Dict[str, str]] = None,
    browser: str = "chromium",
    headless: bool = True
) -> FrontendPerformanceReport:
    """
    Measure frontend performance for specified pages.
    
    Args:
        base_url: Base URL of the frontend
        pages: List of {name, url} dictionaries (uses common pages if None)
        browser: Browser to use (chromium, firefox, webkit)
        headless: Run in headless mode
        
    Returns:
        FrontendPerformanceReport
    """
    if pages is None:
        pages = get_common_pages(base_url)
    
    measurer = FrontendPerformanceMeasurer(browser=browser, headless=headless)
    
    print("\n" + "=" * 60)
    print("FRONTEND PERFORMANCE MEASUREMENT")
    print("=" * 60)
    print(f"Browser: {browser}")
    print(f"Pages: {len(pages)}")
    print("-" * 60)
    
    measurer.measure_multiple_pages(pages)
    
    report = measurer.get_report(browser)
    
    print("-" * 60)
    print(f"Summary:")
    print(f"  Total Pages: {report.summary.get('total_pages', 0)}")
    print(f"  Healthy: {report.summary.get('healthy_pages', 0)}")
    print(f"  Avg Score: {report.summary.get('avg_performance_score', 0)}")
    print("=" * 60 + "\n")
    
    return report


# Export for use in other modules
__all__ = [
    "PageLoadMetrics",
    "FrontendPerformanceReport",
    "FrontendPerformanceMeasurer",
    "FrontendPerformanceThresholds",
    "FrontendBaselineManager",
    "measure_frontend_performance",
    "get_common_pages",
]