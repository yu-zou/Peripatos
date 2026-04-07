"""Evaluation corpus module for Granite Docling VLM evaluation."""

import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CorpusEntry:
    """A single entry in the evaluation corpus."""

    arxiv_id: str
    category: str
    pdf_url: str
    expected_elements: list[str]


def get_corpus() -> list[CorpusEntry]:
    """Get the evaluation corpus with 5 diverse ArXiv papers.
    
    Returns:
        List of 5 CorpusEntry objects covering different paper complexity types.
    """
    return [
        CorpusEntry(
            arxiv_id="2501.17887",
            category="math-heavy",
            pdf_url="https://arxiv.org/pdf/2501.17887",
            expected_elements=["mathematical formulas", "equations", "proofs", "dense layout"]
        ),
        CorpusEntry(
            arxiv_id="2408.09869",
            category="table-heavy",
            pdf_url="https://arxiv.org/pdf/2408.09869",
            expected_elements=["tables", "metrics", "benchmarks", "comparison results"]
        ),
        CorpusEntry(
            arxiv_id="2310.06825",
            category="code-heavy",
            pdf_url="https://arxiv.org/pdf/2310.06825",
            expected_elements=["code snippets", "algorithms", "pseudocode", "syntax highlighting"]
        ),
        CorpusEntry(
            arxiv_id="2301.13848",
            category="multi-column",
            pdf_url="https://arxiv.org/pdf/2301.13848",
            expected_elements=["multi-column layout", "side-by-side text", "column breaks", "complex formatting"]
        ),
        CorpusEntry(
            arxiv_id="2312.00752",
            category="figure-heavy",
            pdf_url="https://arxiv.org/pdf/2312.00752",
            expected_elements=["figures", "diagrams", "charts", "visual illustrations", "subfigures"]
        ),
    ]


def download_corpus(output_dir: str) -> list[str]:
    """Download PDF files for all corpus entries.
    
    Implements caching: skips download if file already exists at output_dir/{arxiv_id}.pdf.
    Uses urllib.request (stdlib only, no external dependencies).
    
    Args:
        output_dir: Directory to save downloaded PDFs.
    
    Returns:
        List of paths to downloaded (or cached) PDF files.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    corpus = get_corpus()
    downloaded_paths = []
    
    for entry in corpus:
        pdf_path = output_path / f"{entry.arxiv_id}.pdf"
        
        if pdf_path.exists():
            downloaded_paths.append(str(pdf_path))
            continue
        
        try:
            with urllib.request.urlopen(entry.pdf_url) as response:
                pdf_content = response.read()
            
            pdf_path.write_bytes(pdf_content)
            downloaded_paths.append(str(pdf_path))
        except Exception as e:
            raise RuntimeError(f"Failed to download {entry.arxiv_id}: {e}")
    
    return downloaded_paths
