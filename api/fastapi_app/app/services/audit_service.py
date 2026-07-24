from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.db.models import Audit, AuditIssue, Project
from app.utils.serializers import model_to_dict
from app.services.notification_service import create_notification


def fetch_website_content(url: str, timeout: int = 10) -> dict:
    """Fetch website content and return HTML, status code, and headers."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    try:
        response = requests.get(
            url, 
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; RankCareBot/1.0; +https://rankcare.com/bot)"
            },
            allow_redirects=True
        )
        return {
            "success": True,
            "status_code": response.status_code,
            "content": response.text,
            "headers": dict(response.headers),
            "url": response.url
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "status_code": None,
            "content": None,
            "headers": {},
            "url": url
        }


def analyze_seo_metrics(url: str, html: str, headers: dict) -> list[dict]:
    """Analyze website for SEO issues and return list of issues."""
    issues = []
    
    if not html:
        issues.append({
            "title": "Website is unreachable",
            "description": "Could not fetch the website content. Please check if the domain is accessible.",
            "category": "TECHNICAL",
            "severity": "CRITICAL",
            "recommendation": "Verify the domain is correct and the server is running."
        })
        return issues
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Title Tag Analysis
    title_tag = soup.find('title')
    if not title_tag or not title_tag.get_text().strip():
        issues.append({
            "title": "Missing title tag",
            "description": "The page does not have a <title> tag. This is critical for SEO.",
            "category": "ON_PAGE",
            "severity": "CRITICAL",
            "recommendation": "Add a unique, descriptive title tag (50-60 characters) to each page."
        })
    else:
        title_text = title_tag.get_text().strip()
        if len(title_text) < 30:
            issues.append({
                "title": "Title tag is too short",
                "description": f"Title length is {len(title_text)} characters. Recommended: 50-60 characters.",
                "category": "ON_PAGE",
                "severity": "WARNING",
                "recommendation": "Expand the title to be more descriptive while staying within 50-60 characters."
            })
        elif len(title_text) > 60:
            issues.append({
                "title": "Title tag is too long",
                "description": f"Title length is {len(title_text)} characters. Recommended: 50-60 characters.",
                "category": "ON_PAGE",
                "severity": "WARNING",
                "recommendation": "Shorten the title to avoid truncation in search results."
            })
        else:
            issues.append({
                "title": "Title tag is optimized",
                "description": f"Title length is {len(title_text)} characters (optimal range).",
                "category": "ON_PAGE",
                "severity": "PASSED",
                "recommendation": "No action needed."
            })
    
    # 2. Meta Description Analysis
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if not meta_desc or not meta_desc.get('content', '').strip():
        issues.append({
            "title": "Missing meta description",
            "description": "The page does not have a meta description tag.",
            "category": "ON_PAGE",
            "severity": "WARNING",
            "recommendation": "Add a compelling meta description (150-160 characters) to improve click-through rates."
        })
    else:
        desc_content = meta_desc.get('content', '').strip()
        if len(desc_content) < 120:
            issues.append({
                "title": "Meta description is too short",
                "description": f"Description length is {len(desc_content)} characters. Recommended: 150-160 characters.",
                "category": "ON_PAGE",
                "severity": "WARNING",
                "recommendation": "Expand the description to provide more context."
            })
        elif len(desc_content) > 160:
            issues.append({
                "title": "Meta description is too long",
                "description": f"Description length is {len(desc_content)} characters. Recommended: 150-160 characters.",
                "category": "ON_PAGE",
                "severity": "WARNING",
                "recommendation": "Shorten the description to avoid truncation."
            })
        else:
            issues.append({
                "title": "Meta description is optimized",
                "description": f"Description length is {len(desc_content)} characters (optimal range).",
                "category": "ON_PAGE",
                "severity": "PASSED",
                "recommendation": "No action needed."
            })
    
    # 3. H1 Tag Analysis
    h1_tags = soup.find_all('h1')
    if len(h1_tags) == 0:
        issues.append({
            "title": "Missing H1 heading",
            "description": "The page does not have an <h1> tag.",
            "category": "ON_PAGE",
            "severity": "WARNING",
            "recommendation": "Add exactly one H1 tag that describes the page content."
        })
    elif len(h1_tags) > 1:
        issues.append({
            "title": "Multiple H1 headings found",
            "description": f"Found {len(h1_tags)} H1 tags. Best practice is to have only one.",
            "category": "ON_PAGE",
            "severity": "WARNING",
            "recommendation": "Use only one H1 tag per page for better structure."
        })
    else:
        h1_text = h1_tags[0].get_text().strip()
        if len(h1_text) < 10:
            issues.append({
                "title": "H1 heading is too short",
                "description": "H1 tag content is very brief. Consider making it more descriptive.",
                "category": "ON_PAGE",
                "severity": "WARNING",
                "recommendation": "Expand the H1 to better describe the page content."
            })
        else:
            issues.append({
                "title": "H1 heading is present",
                "description": f"H1 tag found with {len(h1_text)} characters.",
                "category": "ON_PAGE",
                "severity": "PASSED",
                "recommendation": "No action needed."
            })
    
    # 4. Image Alt Text Analysis
    images = soup.find_all('img')
    images_without_alt = [img for img in images if not img.get('alt', '').strip()]
    
    if len(images) > 0 and len(images_without_alt) > 0:
        issues.append({
            "title": "Images missing alt text",
            "description": f"{len(images_without_alt)} out of {len(images)} images are missing alt attributes.",
            "category": "ON_PAGE",
            "severity": "WARNING",
            "recommendation": "Add descriptive alt text to all images for accessibility and SEO."
        })
    elif len(images) > 0:
        issues.append({
            "title": "All images have alt text",
            "description": f"All {len(images)} images have alt attributes.",
            "category": "ON_PAGE",
            "severity": "PASSED",
            "recommendation": "No action needed."
        })
    
    # 5. Internal Links Analysis
    links = soup.find_all('a', href=True)
    internal_links = []
    external_links = []
    
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    for link in links:
        href = link.get('href', '')
        if href.startswith(('http://', 'https://')):
            if domain in href:
                internal_links.append(href)
            else:
                external_links.append(href)
        elif href.startswith('/'):
            internal_links.append(href)
    
    if len(internal_links) < 3:
        issues.append({
            "title": "Low internal linking",
            "description": f"Only {len(internal_links)} internal links found. Internal linking helps SEO.",
            "category": "ON_PAGE",
            "severity": "WARNING",
            "recommendation": "Add more internal links to related pages on your site."
        })
    else:
        issues.append({
            "title": "Good internal linking",
            "description": f"Found {len(internal_links)} internal links.",
            "category": "ON_PAGE",
            "severity": "PASSED",
            "recommendation": "No action needed."
        })
    
    # 6. Mobile-Friendly Check (Viewport Meta Tag)
    viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
    if not viewport_meta:
        issues.append({
            "title": "Missing viewport meta tag",
            "description": "The page does not have a viewport meta tag. This affects mobile usability.",
            "category": "TECHNICAL",
            "severity": "CRITICAL",
            "recommendation": "Add <meta name='viewport' content='width=device-width, initial-scale=1'> to make the page mobile-friendly."
        })
    else:
        issues.append({
            "title": "Viewport meta tag present",
            "description": "Page has viewport meta tag for mobile responsiveness.",
            "category": "TECHNICAL",
            "severity": "PASSED",
            "recommendation": "No action needed."
        })
    
    # 7. HTTPS Check
    if not url.startswith('https://'):
        issues.append({
            "title": "Website not using HTTPS",
            "description": "The website is not served over HTTPS. This affects security and SEO.",
            "category": "TECHNICAL",
            "severity": "CRITICAL",
            "recommendation": "Install an SSL certificate and redirect all HTTP traffic to HTTPS."
        })
    else:
        issues.append({
            "title": "HTTPS enabled",
            "description": "Website is served securely over HTTPS.",
            "category": "TECHNICAL",
            "severity": "PASSED",
            "recommendation": "No action needed."
        })
    
    # 8. Canonical Tag Check
    canonical_tag = soup.find('link', rel='canonical')
    if not canonical_tag or not canonical_tag.get('href', '').strip():
        issues.append({
            "title": "Missing canonical tag",
            "description": "The page does not have a canonical URL specified.",
            "category": "ON_PAGE",
            "severity": "WARNING",
            "recommendation": "Add a canonical tag to prevent duplicate content issues."
        })
    else:
        issues.append({
            "title": "Canonical tag present",
            "description": "Page has a canonical URL specified.",
            "category": "ON_PAGE",
            "severity": "PASSED",
            "recommendation": "No action needed."
        })
    
    # 9. Robots Meta Tag Check
    robots_meta = soup.find('meta', attrs={'name': 'robots'})
    if robots_meta:
        content = robots_meta.get('content', '').lower()
        if 'noindex' in content:
            issues.append({
                "title": "Page set to noindex",
                "description": "The page has a 'noindex' directive which prevents search engines from indexing it.",
                "category": "TECHNICAL",
                "severity": "CRITICAL",
                "recommendation": "Remove 'noindex' from robots meta tag if you want this page indexed."
            })
        elif 'nofollow' in content:
            issues.append({
                "title": "Page set to nofollow",
                "description": "The page has a 'nofollow' directive which prevents search engines from following links.",
                "category": "TECHNICAL",
                "severity": "WARNING",
                "recommendation": "Review if 'nofollow' is intentional for this page."
            })
        else:
            issues.append({
                "title": "Robots meta tag is properly configured",
                "description": "Robots meta tag allows indexing and following links.",
                "category": "TECHNICAL",
                "severity": "PASSED",
                "recommendation": "No action needed."
            })
    else:
        issues.append({
            "title": "No robots meta tag",
            "description": "Page does not have explicit robots directives (defaults to index, follow).",
            "category": "TECHNICAL",
            "severity": "PASSED",
            "recommendation": "No action needed unless you want to restrict crawling."
        })
    
    # 10. Content Length Analysis
    # Remove script and style elements
    for script in soup(['script', 'style']):
        script.decompose()
    
    text_content = soup.get_text(separator=' ', strip=True)
    word_count = len(text_content.split())
    
    if word_count < 300:
        issues.append({
            "title": "Low content length",
            "description": f"Page has only {word_count} words. Search engines prefer content-rich pages.",
            "category": "CONTENT",
            "severity": "WARNING",
            "recommendation": "Add more high-quality, relevant content (aim for 500+ words)."
        })
    elif word_count < 500:
        issues.append({
            "title": "Content length could be improved",
            "description": f"Page has {word_count} words. Consider adding more content.",
            "category": "CONTENT",
            "severity": "WARNING",
            "recommendation": "Expand content to provide more value to users."
        })
    else:
        issues.append({
            "title": "Good content length",
            "description": f"Page has {word_count} words of content.",
            "category": "CONTENT",
            "severity": "PASSED",
            "recommendation": "No action needed."
        })
    
    return issues


def normalize_domain(value: str = "") -> str:
    return (
        value.strip()
        .lower()
        .removeprefix("https://")
        .removeprefix("http://")
        .removeprefix("www.")
        .rstrip("/")
    )


def ensure_project_access(db: Session, user_id: str, project_id: str) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id, Project.userId == user_id)
        .options(
            selectinload(Project.keywords),
            selectinload(Project.competitors),
            selectinload(Project.rankResults),
        )
    )

    if not project:
        raise ApiError(404, "Project not found")
    return project


def build_audit_issues(project: Project) -> list[dict]:
    issues: list[dict] = []
    clean_domain = normalize_domain(project.domain or "")
    keywords = project.keywords or []
    competitors = project.competitors or []
    rankings = sorted(project.rankResults or [], key=lambda row: row.checkedAt, reverse=True)

    if not clean_domain:
        issues.append(
            {
                "title": "Project domain is missing",
                "description": "This project does not have a valid domain configured.",
                "category": "TECHNICAL",
                "severity": "CRITICAL",
                "recommendation": "Add a valid project domain in the project setup.",
            }
        )
    elif "." not in clean_domain:
        issues.append(
            {
                "title": "Project domain format looks incomplete",
                "description": "The saved domain does not appear to include a full hostname.",
                "category": "TECHNICAL",
                "severity": "WARNING",
                "recommendation": "Update the project domain to a valid value like example.com.",
            }
        )
    else:
        issues.append(
            {
                "title": "Project domain is configured",
                "description": f"Domain {clean_domain} is available for this project.",
                "category": "TECHNICAL",
                "severity": "PASSED",
                "recommendation": "No action needed.",
            }
        )

    if len(keywords) == 0:
        issues.append(
            {
                "title": "No keywords added",
                "description": "The project has no tracked keywords yet.",
                "category": "CONTENT",
                "severity": "CRITICAL",
                "recommendation": "Add at least 5 target keywords for meaningful tracking.",
            }
        )
    elif len(keywords) < 5:
        suffix = "" if len(keywords) == 1 else "s"
        issues.append(
            {
                "title": "Keyword coverage is low",
                "description": f"Only {len(keywords)} keyword{suffix} added to this project.",
                "category": "CONTENT",
                "severity": "WARNING",
                "recommendation": "Add more target keywords to improve audit usefulness.",
            }
        )
    else:
        issues.append(
            {
                "title": "Keyword coverage is healthy",
                "description": f"{len(keywords)} keywords are available for analysis.",
                "category": "CONTENT",
                "severity": "PASSED",
                "recommendation": "No action needed.",
            }
        )

    if len(competitors) == 0:
        issues.append(
            {
                "title": "No competitors added",
                "description": "Competitor benchmarking is not available yet.",
                "category": "ON_PAGE",
                "severity": "WARNING",
                "recommendation": "Add at least 2 competitors for comparison insights.",
            }
        )
    elif len(competitors) < 2:
        issues.append(
            {
                "title": "Competitor set is limited",
                "description": f"Only {len(competitors)} competitor has been added.",
                "category": "ON_PAGE",
                "severity": "WARNING",
                "recommendation": "Add at least one more competitor for better benchmarking.",
            }
        )
    else:
        issues.append(
            {
                "title": "Competitor coverage is available",
                "description": f"{len(competitors)} competitors are available for comparison.",
                "category": "ON_PAGE",
                "severity": "PASSED",
                "recommendation": "No action needed.",
            }
        )

    if len(rankings) == 0:
        issues.append(
            {
                "title": "No ranking data found",
                "description": "Rank checks have not been run for this project yet.",
                "category": "PERFORMANCE",
                "severity": "CRITICAL",
                "recommendation": "Run a rank check to populate ranking performance data.",
            }
        )
    else:
        latest_checked_at = rankings[0].checkedAt if rankings else None
        top10_count = len(
            [row for row in rankings if isinstance(row.position, int) and row.position > 0 and row.position <= 10]
        )

        issues.append(
            {
                "title": "Ranking data is available",
                "description": (
                    f"Latest rank check was recorded on {latest_checked_at.strftime('%m/%d/%Y')}."
                    if latest_checked_at
                    else "Ranking data exists for this project."
                ),
                "category": "PERFORMANCE",
                "severity": "PASSED",
                "recommendation": "No action needed.",
            }
        )

        if top10_count == 0:
            issues.append(
                {
                    "title": "No top 10 rankings found",
                    "description": "Tracked keywords are not yet ranking in the top 10 positions.",
                    "category": "PERFORMANCE",
                    "severity": "WARNING",
                    "recommendation": "Improve pages targeting these keywords and rerun rank checks.",
                }
            )
        else:
            suffix = "" if top10_count == 1 else "s"
            issues.append(
                {
                    "title": "Top 10 visibility detected",
                    "description": f"{top10_count} ranking result{suffix} found in the top 10.",
                    "category": "PERFORMANCE",
                    "severity": "PASSED",
                    "recommendation": "Continue monitoring and optimize remaining keywords.",
                }
            )

    return issues


def build_audit_summary(issues: list[dict]) -> dict:
    critical_issues = len([item for item in issues if item["severity"] == "CRITICAL"])
    warning_issues = len([item for item in issues if item["severity"] == "WARNING"])
    passed_checks = len([item for item in issues if item["severity"] == "PASSED"])
    total_issues = len(issues)
    score = max(0, min(100, passed_checks * 20 - critical_issues * 15 - warning_issues * 5 + 50))

    summary = "Audit completed."
    if critical_issues > 0:
        crit_suffix = "" if critical_issues == 1 else "s"
        warn_suffix = "" if warning_issues == 1 else "s"
        summary = f"Audit found {critical_issues} critical issue{crit_suffix} and {warning_issues} warning{warn_suffix}."
    elif warning_issues > 0:
        warn_suffix = "" if warning_issues == 1 else "s"
        summary = f"Audit found {warning_issues} warning{warn_suffix} and no critical issues."
    else:
        summary = "Audit completed with no critical or warning issues."

    return {
        "score": score,
        "totalIssues": total_issues,
        "criticalIssues": critical_issues,
        "warningIssues": warning_issues,
        "passedChecks": passed_checks,
        "summary": summary,
    }


def run_project_audit(db: Session, user_id: str, project_id: str) -> dict:
    project = ensure_project_access(db, user_id, project_id)
    
    # Fetch real website data if domain exists
    website_issues = []
    clean_domain = normalize_domain(project.domain or "")
    
    if clean_domain and "." in clean_domain:
        # Fetch and analyze real website
        fetch_result = fetch_website_content(clean_domain)
        
        if fetch_result["success"]:
            # Analyze SEO metrics from real website
            website_issues = analyze_seo_metrics(
                fetch_result["url"],
                fetch_result["content"],
                fetch_result["headers"]
            )
        else:
            # Website unreachable - add critical issue
            website_issues.append({
                "title": "Website is unreachable",
                "description": f"Could not connect to {clean_domain}. Error: {fetch_result.get('error', 'Unknown error')}",
                "category": "TECHNICAL",
                "severity": "CRITICAL",
                "recommendation": "Verify the domain is correct and the server is running."
            })
    
    # Build issues from project data (keywords, competitors, rankings)
    project_issues = build_audit_issues(project)
    
    # Combine both sets of issues
    all_issues = website_issues + project_issues
    
    summary = build_audit_summary(all_issues)

    audit = Audit(
        projectId=project_id,
        status="COMPLETED",
        score=summary["score"],
        totalIssues=summary["totalIssues"],
        criticalIssues=summary["criticalIssues"],
        warningIssues=summary["warningIssues"],
        passedChecks=summary["passedChecks"],
        summary=summary["summary"],
    )
    db.add(audit)
    db.flush()

    for issue in all_issues:
        db.add(AuditIssue(auditId=audit.id, **issue))

    db.commit()

    create_notification(
        db,
        user_id=user_id,
        project_id=project_id,
        type="AUDIT_COMPLETED",
        title="Audit completed",
        message=f"{project.name} audit completed successfully.",
        severity="info",
        entity_type="audit",
        entity_id=audit.id,
        metadata={
            "auditId": audit.id,
            "projectId": project_id,
            "score": audit.score,
            "criticalIssues": audit.criticalIssues,
            "warningIssues": audit.warningIssues,
        },
    )

    db.commit()

    return get_audit_by_id(db, audit.id)


def get_audit_by_id(db: Session, audit_id: str) -> dict:
    audit = db.scalar(select(Audit).where(Audit.id == audit_id).options(selectinload(Audit.issues)))
    if not audit:
        raise ApiError(404, "Audit not found")

    data = model_to_dict(audit)
    issues = [model_to_dict(issue) for issue in audit.issues]
    issues.sort(key=lambda item: (item["severity"], item["createdAt"]), reverse=False)
    data["issues"] = issues
    return data


def get_project_audits(db: Session, user_id: str, project_id: str) -> list[dict]:
    ensure_project_access(db, user_id, project_id)

    audits = db.scalars(
        select(Audit)
        .where(Audit.projectId == project_id)
        .order_by(desc(Audit.createdAt))
        .options(selectinload(Audit.issues))
    ).all()

    result = []
    for audit in audits:
        item = model_to_dict(audit)
        issues = [model_to_dict(issue) for issue in audit.issues]
        issues.sort(key=lambda row: (row["severity"], row["createdAt"]))
        item["issues"] = issues
        result.append(item)

    return result
