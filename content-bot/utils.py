import requests
from bs4 import BeautifulSoup
import re

def extract_content_from_url(url: str) -> str:
    """
    Fetches the URL and extracts metadata and the main text content.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title metadata
        title = soup.title.string.strip() if soup.title else ""
        og_title_tag = soup.find("meta", attrs={"property": "og:title"})
        og_title = og_title_tag.get("content").strip() if og_title_tag and og_title_tag.get("content") else ""
        final_title = og_title or title or "No Title"

        # Extract description metadata
        meta_desc = ""
        description_tag = (
            soup.find("meta", attrs={"name": "description"}) or
            soup.find("meta", attrs={"property": "og:description"}) or
            soup.find("meta", attrs={"name": "twitter:description"})
        )
        if description_tag and description_tag.get("content"):
            meta_desc = description_tag.get("content").strip()

        # Remove irrelevant and non-content elements
        garbage_selectors = [
            "script", "style", "nav", "footer", "header", "aside", 
            "iframe", "noscript", "form", ".ads", ".advertisement", 
            "#footer", "#header", "#sidebar", ".comments", ".menu", ".nav"
        ]
        for selector in garbage_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Attempt to target primary content containers
        main_content = ""
        content_selectors = [
            "article", "main", "[role='main']", ".post-content", 
            ".entry-content", ".article-body", ".content", "#content"
        ]
        
        content_element = None
        for selector in content_selectors:
            found = soup.select_one(selector)
            if found:
                content_element = found
                break
                
        if content_element:
            paragraphs = content_element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
            main_content = "\n".join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
        else:
            body = soup.find('body')
            if body:
                paragraphs = body.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
                main_content = "\n".join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
            else:
                main_content = soup.get_text()

        # Clean up line breaks and spacing
        lines = (line.strip() for line in main_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        main_content_cleaned = '\n'.join(chunk for chunk in chunks if chunk)

        # Build clean structured output
        summary_parts = []
        summary_parts.append(f"Title: {final_title}")
        if meta_desc:
            summary_parts.append(f"Description: {meta_desc}")
        if main_content_cleaned:
            summary_parts.append(f"Content:\n{main_content_cleaned}")
            
        final_summary = "\n\n".join(summary_parts)
        
        # Limit text to 5000 characters to avoid huge prompts
        return final_summary[:5000]
    except Exception as e:
        print(f"Error extracting content from URL {url}: {e}")
        return ""

def is_url(text: str) -> bool:
    """
    Checks if a string is a valid URL.
    """
    url_pattern = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain...
        r'localhost|' # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(url_pattern, text) is not None
