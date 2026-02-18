"""ArXiv paper extraction and metadata."""

import re
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List


class FetchError(Exception):
    """Exception raised when fetching from ArXiv fails."""
    pass


class ArxivFetcher:
    """Fetches PDFs and metadata from ArXiv."""
    
    # ArXiv ID regex: YYMM.NNNNN or YYMM.NNNNNvN format
    ARXIV_ID_PATTERN = re.compile(r'^\d{4}\.\d{4,5}(v\d+)?$')
    
    def __init__(self, output_dir: str | None = None):
        """Initialize the ArxivFetcher.
        
        Args:
            output_dir: Optional directory to save PDFs. Uses temp dir if not specified.
        """
        self.output_dir = output_dir or tempfile.mkdtemp()
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def validate_id(self, arxiv_id: str) -> bool:
        """Validate ArXiv ID format.
        
        Args:
            arxiv_id: The ArXiv ID to validate (e.g., "2408.09869" or "2408.09869v1")
        
        Returns:
            True if valid
        
        Raises:
            FetchError: If the ID format is invalid
        """
        if not arxiv_id or not self.ARXIV_ID_PATTERN.match(arxiv_id):
            raise FetchError(f"Invalid ArXiv ID format: {arxiv_id}")
        return True
    
    def fetch(self, arxiv_id: str) -> Path:
        """Download PDF from ArXiv.
        
        Args:
            arxiv_id: The ArXiv ID (e.g., "2408.09869" or "2408.09869v1")
        
        Returns:
            Path to the downloaded PDF file
        
        Raises:
            FetchError: If ID is invalid, download fails, or network error occurs
        """
        # Validate ID first
        self.validate_id(arxiv_id)
        
        # Construct PDF URL
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        
        try:
            # Download PDF
            with urllib.request.urlopen(pdf_url) as response:
                pdf_content = response.read()
            
            # Save to file
            output_path = Path(self.output_dir) / f"{arxiv_id}.pdf"
            output_path.write_bytes(pdf_content)
            
            return output_path
            
        except Exception as e:
            raise FetchError(f"Failed to fetch PDF from ArXiv: {str(e)}")
    
    def extract_metadata(self, arxiv_id: str) -> Dict[str, Any]:
        """Extract metadata from ArXiv API.
        
        Args:
            arxiv_id: The ArXiv ID (e.g., "2408.09869" or "2408.09869v1")
        
        Returns:
            Dictionary with keys: "title", "authors" (list), "summary"
        
        Raises:
            FetchError: If ID is invalid or API call fails
        """
        # Validate ID first
        self.validate_id(arxiv_id)
        
        # Construct API URL
        # Strip version suffix if present for API query
        base_id = arxiv_id.split('v')[0] if 'v' in arxiv_id else arxiv_id
        api_url = f"http://export.arxiv.org/api/query?id_list={base_id}"
        
        try:
            # Fetch XML from API
            with urllib.request.urlopen(api_url) as response:
                xml_content = response.read()
            
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Define namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            # Extract entry
            entry = root.find('atom:entry', ns)
            if entry is None:
                raise FetchError(f"No entry found in ArXiv API response for {arxiv_id}")
            
            # Extract title
            title_elem = entry.find('atom:title', ns)
            title = title_elem.text if title_elem is not None else ""
            
            # Extract authors
            authors = []
            for author_elem in entry.findall('atom:author', ns):
                name_elem = author_elem.find('atom:name', ns)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text)
            
            # Extract summary
            summary_elem = entry.find('atom:summary', ns)
            summary = summary_elem.text if summary_elem is not None else ""
            
            return {
                "title": title,
                "authors": authors,
                "summary": summary
            }
            
        except ET.ParseError as e:
            raise FetchError(f"Failed to parse ArXiv API response: {str(e)}")
        except Exception as e:
            raise FetchError(f"Failed to fetch metadata from ArXiv: {str(e)}")
