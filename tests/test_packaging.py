"""
Test suite for package configuration and optional dependencies.

Tests verify that optional dependency groups are correctly defined in pyproject.toml
and can be installed successfully.
"""

import tomllib
from pathlib import Path


def test_optional_dependencies_exist():
    """Test that vlm and eval optional dependency groups exist in pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    
    assert "optional-dependencies" in pyproject["project"], \
        "pyproject.toml missing [project.optional-dependencies] section"
    
    optional_deps = pyproject["project"]["optional-dependencies"]
    assert "vlm" in optional_deps, "Missing 'vlm' optional dependency group"
    assert "eval" in optional_deps, "Missing 'eval' optional dependency group"


def test_vlm_group_contains_required_packages():
    """Test that vlm group contains torch, transformers, accelerate, and mlx-vlm."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    
    vlm_deps = pyproject["project"]["optional-dependencies"]["vlm"]
    vlm_deps_str = "\n".join(vlm_deps)
    
    assert any("torch" in dep for dep in vlm_deps), \
        "vlm group missing torch dependency"
    assert any("transformers" in dep for dep in vlm_deps), \
        "vlm group missing transformers dependency"
    assert any("accelerate" in dep for dep in vlm_deps), \
        "vlm group missing accelerate dependency"
    assert any("mlx-vlm" in dep for dep in vlm_deps), \
        "vlm group missing mlx-vlm dependency"
    
    # Verify mlx-vlm has platform marker for Apple Silicon
    mlx_dep = next((dep for dep in vlm_deps if "mlx-vlm" in dep), None)
    assert mlx_dep is not None, "mlx-vlm dependency not found"
    assert "sys_platform" in mlx_dep or "platform_machine" in mlx_dep, \
        f"mlx-vlm missing platform marker: {mlx_dep}"


def test_eval_group_contains_docling_eval():
    """Test that eval group contains docling-eval."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    
    eval_deps = pyproject["project"]["optional-dependencies"]["eval"]
    
    assert any("docling-eval" in dep for dep in eval_deps), \
        "eval group missing docling-eval dependency"


def test_base_dependencies_do_not_include_vlm_packages():
    """Test that base dependencies exclude torch, transformers, and docling-eval."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    
    base_deps = pyproject["project"]["dependencies"]
    base_deps_str = "\n".join(base_deps).lower()
    
    assert "torch" not in base_deps_str, \
        "torch should NOT be in base dependencies (must be optional)"
    assert "transformers" not in base_deps_str, \
        "transformers should NOT be in base dependencies (must be optional)"
    assert "docling-eval" not in base_deps_str, \
        "docling-eval should NOT be in base dependencies (must be optional)"
