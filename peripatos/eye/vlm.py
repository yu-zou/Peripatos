from __future__ import annotations

import platform
import importlib
import time
from typing import Callable, Protocol, TypeVar, cast


_T = TypeVar("_T")


class _InputFormatProtocol(Protocol):
    PDF: object


class _VlmPipelineOptionsProtocol(Protocol):
    def __init__(self, vlm_options: object) -> None: ...


class _VlmConvertOptionsProtocol(Protocol):
    @classmethod
    def from_preset(cls, preset: str, engine_options: object | None = None) -> object: ...


class _MlxVlmEngineOptionsProtocol(Protocol):
    def __init__(self) -> None: ...


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
    type[_InputFormatProtocol],
    type[_VlmPipelineOptionsProtocol],
    type[_DocumentConverterProtocol],
    type[_PdfFormatOptionProtocol],
    type,
    type[_VlmConvertOptionsProtocol],
    type[_MlxVlmEngineOptionsProtocol],
]:
    base_models_module = importlib.import_module("docling.datamodel.base_models")
    pipeline_options_module = importlib.import_module("docling.datamodel.pipeline_options")
    vlm_engine_options_module = importlib.import_module("docling.datamodel.vlm_engine_options")
    document_converter_module = importlib.import_module("docling.document_converter")
    vlm_pipeline_module = importlib.import_module("docling.pipeline.vlm_pipeline")

    _ = (
        base_models_module,
        pipeline_options_module,
        document_converter_module,
        vlm_pipeline_module,
        vlm_engine_options_module,
    )

    return (
        cast(type[_InputFormatProtocol], base_models_module.InputFormat),
        cast(type[_VlmPipelineOptionsProtocol], pipeline_options_module.VlmPipelineOptions),
        cast(type[_DocumentConverterProtocol], document_converter_module.DocumentConverter),
        cast(type[_PdfFormatOptionProtocol], document_converter_module.PdfFormatOption),
        cast(type, vlm_pipeline_module.VlmPipeline),
        cast(type[_VlmConvertOptionsProtocol], pipeline_options_module.VlmConvertOptions),
        cast(type[_MlxVlmEngineOptionsProtocol], vlm_engine_options_module.MlxVlmEngineOptions),
    )


def _ensure_vlm_dependencies() -> None:
    try:
        _ = importlib.import_module("torch")
        _ = importlib.import_module("transformers")
    except ImportError as exc:
        raise ImportError(
            "VLM support requires additional dependencies. Install with: pip install peripatos[vlm]"
        ) from exc


def _tune_mlx_options(vlm_options: object) -> None:
    def _cap_max_tokens(target: object) -> None:
        current_max = getattr(target, "max_new_tokens", None)
        if isinstance(current_max, int) and current_max > 4096:
            setattr(target, "max_new_tokens", 4096)

    _cap_max_tokens(vlm_options)
    model_spec = getattr(vlm_options, "model_spec", None)
    if model_spec is not None:
        _cap_max_tokens(cast(object, model_spec))


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

    (
        input_format,
        vlm_options_cls,
        document_converter,
        pdf_format_option,
        vlm_pipeline,
        vlm_convert_options_cls,
        mlx_engine_options_cls,
    ) = _load_docling()

    if backend == "mlx":
        engine_options = mlx_engine_options_cls()
        vlm_options = vlm_convert_options_cls.from_preset("granite_docling", engine_options=engine_options)
        _tune_mlx_options(vlm_options)
    elif backend == "cuda":
        vlm_options = vlm_convert_options_cls.from_preset("granite_docling")
    elif backend == "cpu":
        vlm_options = vlm_convert_options_cls.from_preset("granite_docling")
    elif backend is None:
        # Auto-detect
        if _is_apple_silicon():
            engine_options = mlx_engine_options_cls()
            vlm_options = vlm_convert_options_cls.from_preset("granite_docling", engine_options=engine_options)
            _tune_mlx_options(vlm_options)
        elif torch.cuda.is_available():
            vlm_options = vlm_convert_options_cls.from_preset("granite_docling")
        else:
            vlm_options = vlm_convert_options_cls.from_preset("granite_docling")
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
