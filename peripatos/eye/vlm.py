from __future__ import annotations

import platform
import importlib
import time
from typing import Callable, Protocol, TypeVar, cast


_T = TypeVar("_T")


class _VlmSpecsProtocol(Protocol):
    GRANITEDOCLING_MLX: object
    GRANITEDOCLING_TRANSFORMERS: object


class _InputFormatProtocol(Protocol):
    PDF: object


class _VlmPipelineOptionsProtocol(Protocol):
    def __init__(self, vlm_options: object) -> None: ...


class _PdfFormatOptionProtocol(Protocol):
    def __init__(self, pipeline_cls: type, pipeline_options: object) -> None: ...
    pipeline_cls: type
    pipeline_options: object


class _DocumentConverterProtocol(Protocol):
    format_options: dict[object, object]

    def __init__(self, format_options: dict[object, object]) -> None: ...
    def convert(self, source: object) -> object: ...


def _with_timeout(func: Callable[..., _T], timeout_seconds: float) -> Callable[..., _T]:
    def _wrapped(*args: object, **kwargs: object) -> _T:
        start = time.monotonic()
        result = func(*args, **kwargs)
        elapsed = time.monotonic() - start
        if elapsed > timeout_seconds:
            raise TimeoutError(f"VLM conversion exceeded {timeout_seconds:.1f}s timeout")
        return result

    return _wrapped


def _with_retry(func: Callable[..., _T], retries: int) -> Callable[..., _T]:
    def _wrapped(*args: object, **kwargs: object) -> _T:
        last_exc: Exception | None = None
        for _ in range(retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
        assert last_exc is not None
        raise last_exc

    return _wrapped


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() in {"arm64", "aarch64"}


def _load_docling() -> tuple[
    _VlmSpecsProtocol,
    type[_InputFormatProtocol],
    type[_VlmPipelineOptionsProtocol],
    type[_DocumentConverterProtocol],
    type[_PdfFormatOptionProtocol],
    type,
]:
    vlm_specs_module = importlib.import_module("docling.datamodel.vlm_model_specs")
    base_models_module = importlib.import_module("docling.datamodel.base_models")
    pipeline_options_module = importlib.import_module("docling.datamodel.pipeline_options")
    document_converter_module = importlib.import_module("docling.document_converter")
    vlm_pipeline_module = importlib.import_module("docling.pipeline.vlm_pipeline")

    _ = base_models_module, pipeline_options_module, document_converter_module, vlm_pipeline_module

    return (
        cast(_VlmSpecsProtocol, cast(object, vlm_specs_module)),
        cast(type[_InputFormatProtocol], base_models_module.InputFormat),
        cast(type[_VlmPipelineOptionsProtocol], pipeline_options_module.VlmPipelineOptions),
        cast(type[_DocumentConverterProtocol], document_converter_module.DocumentConverter),
        cast(type[_PdfFormatOptionProtocol], document_converter_module.PdfFormatOption),
        cast(type, vlm_pipeline_module.VlmPipeline),
    )


def _ensure_vlm_dependencies() -> None:
    try:
        _ = importlib.import_module("torch")
        _ = importlib.import_module("transformers")
    except ImportError as exc:
        raise ImportError(
            "VLM support requires additional dependencies. Install with: pip install peripatos[vlm]"
        ) from exc


def create_vlm_converter(
    timeout_seconds: float = 60.0, retries: int = 1, backend: str | None = None
) -> _DocumentConverterProtocol:
    _ensure_vlm_dependencies()
    try:
        import torch
    except ImportError as exc:
        raise ImportError(
            "VLM support requires additional dependencies. Install with: pip install peripatos[vlm]"
        ) from exc

    vlm_specs, input_format, vlm_options_cls, document_converter, pdf_format_option, vlm_pipeline = (
        _load_docling()
    )

    if backend == "mlx":
        vlm_options = vlm_specs.GRANITEDOCLING_MLX
    elif backend == "cuda":
        vlm_options = vlm_specs.GRANITEDOCLING_TRANSFORMERS
    elif backend == "cpu":
        vlm_options = vlm_specs.GRANITEDOCLING_TRANSFORMERS
    elif backend is None:
        # Auto-detect
        if _is_apple_silicon():
            vlm_options = vlm_specs.GRANITEDOCLING_MLX
        elif torch.cuda.is_available():
            vlm_options = vlm_specs.GRANITEDOCLING_TRANSFORMERS
        else:
            vlm_options = vlm_specs.GRANITEDOCLING_TRANSFORMERS
    else:
        raise ValueError(f"Unsupported backend: {backend}. Must be 'mlx', 'cuda', 'cpu', or None (auto)")

    pipeline_options = vlm_options_cls(vlm_options=vlm_options)
    format_options: dict[object, object] = {
        input_format.PDF: pdf_format_option(
            pipeline_cls=vlm_pipeline, pipeline_options=pipeline_options
        )
    }
    converter = document_converter(format_options=format_options)

    converter.convert = _with_retry(
        _with_timeout(converter.convert, timeout_seconds=timeout_seconds), retries=retries
    )
    return converter
