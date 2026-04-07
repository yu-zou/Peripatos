import builtins
import sys
import time
import types
from typing import Callable, Protocol, cast
from types import SimpleNamespace
from typing_extensions import override

import pytest

from peripatos.eye.vlm import create_vlm_converter

class _ConverterProtocol(Protocol):
    format_options: dict[object, object]


class _DocumentConverterStub(Protocol):
    convert_impl: Callable[[object], str]
    call_count: int


class _DoclingDocumentModule(Protocol):
    DocumentConverter: type[_DocumentConverterStub]


class _Module(types.ModuleType):
    @override
    def __setattr__(self, name: str, value: object) -> None:
        types.ModuleType.__setattr__(self, name, value)


def _install_torch_stub(monkeypatch: pytest.MonkeyPatch, cuda_available: bool) -> None:
    torch_module = _Module("torch")

    class _Cuda:
        @staticmethod
        def is_available() -> bool:
            return cuda_available

    torch_module.cuda = _Cuda()
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "transformers", _Module("transformers"))


def _install_docling_stubs(monkeypatch: pytest.MonkeyPatch) -> _Module:
    _ = monkeypatch
    docling = _Module("docling")
    datamodel = _Module("docling.datamodel")
    vlm_specs = _Module("docling.datamodel.vlm_model_specs")
    vlm_specs.GRANITEDOCLING_MLX = "mlx-spec"
    vlm_specs.GRANITEDOCLING_TRANSFORMERS = "transformers-spec"

    base_models = _Module("docling.datamodel.base_models")

    class InputFormat:
        PDF: str = "pdf"

    base_models.InputFormat = InputFormat

    pipeline_options = _Module("docling.datamodel.pipeline_options")

    class VlmPipelineOptions:
        def __init__(self, vlm_options: object | None = None) -> None:
            self.vlm_options: object | None = vlm_options

    pipeline_options.VlmPipelineOptions = VlmPipelineOptions

    class VlmConvertOptions:
        def __init__(self, vlm_options: object | None = None) -> None:
            self.vlm_options = vlm_options

        @classmethod
        def from_preset(cls, preset: str, engine_options: object | None = None) -> "VlmConvertOptions":
            _ = preset
            if isinstance(engine_options, MlxVlmEngineOptions):
                vlm_spec = vlm_specs.GRANITEDOCLING_MLX
            else:
                vlm_spec = vlm_specs.GRANITEDOCLING_TRANSFORMERS
            instance = cls(vlm_options=vlm_spec)
            instance.model_spec = SimpleNamespace(max_new_tokens=8192)
            return instance

    pipeline_options.VlmConvertOptions = VlmConvertOptions

    vlm_engine_options = _Module("docling.datamodel.vlm_engine_options")

    class MlxVlmEngineOptions:
        def __init__(self) -> None:
            pass

    vlm_engine_options.MlxVlmEngineOptions = MlxVlmEngineOptions

    pipeline = _Module("docling.pipeline")
    vlm_pipeline = _Module("docling.pipeline.vlm_pipeline")

    class VlmPipeline:
        pass

    vlm_pipeline.VlmPipeline = VlmPipeline

    document_converter = _Module("docling.document_converter")

    class PdfFormatOption:
        def __init__(self, pipeline_cls: type | None = None, pipeline_options: object | None = None) -> None:
            self.pipeline_cls: type | None = pipeline_cls
            self.pipeline_options: object | None = pipeline_options

    class DocumentConverter:
        @staticmethod
        def convert_impl(source: object) -> str:
            _ = source
            return "ok"

        call_count: int = 0

        def __init__(self, format_options: dict[object, object] | None = None) -> None:
            self.format_options: dict[object, object] = format_options or {}

        def convert(self, source: object) -> str:
            DocumentConverter.call_count += 1
            return DocumentConverter.convert_impl(source)

    document_converter.PdfFormatOption = PdfFormatOption
    document_converter.DocumentConverter = DocumentConverter

    monkeypatch.setitem(sys.modules, "docling", docling)
    monkeypatch.setitem(sys.modules, "docling.datamodel", datamodel)
    monkeypatch.setitem(sys.modules, "docling.datamodel.vlm_model_specs", vlm_specs)
    monkeypatch.setitem(sys.modules, "docling.datamodel.base_models", base_models)
    monkeypatch.setitem(sys.modules, "docling.datamodel.pipeline_options", pipeline_options)
    monkeypatch.setitem(sys.modules, "docling.datamodel.vlm_engine_options", vlm_engine_options)
    monkeypatch.setitem(sys.modules, "docling.pipeline", pipeline)
    monkeypatch.setitem(sys.modules, "docling.pipeline.vlm_pipeline", vlm_pipeline)
    monkeypatch.setitem(sys.modules, "docling.document_converter", document_converter)

    return document_converter


def _assert_pipeline_options(converter: _ConverterProtocol, expected_vlm_option: str) -> None:
    format_option = converter.format_options["pdf"]
    pipeline_options = getattr(format_option, "pipeline_options", SimpleNamespace())
    vlm_options = getattr(pipeline_options, "vlm_options", None)
    if isinstance(vlm_options, str):
        actual = vlm_options
    else:
        actual = getattr(vlm_options, "vlm_options", None)
    assert actual == expected_vlm_option


def test_create_vlm_converter_prefers_mlx_on_apple_silicon(monkeypatch: pytest.MonkeyPatch):
    _install_torch_stub(monkeypatch, cuda_available=True)
    _ = _install_docling_stubs(monkeypatch)
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr("platform.machine", lambda: "arm64")

    converter = create_vlm_converter()

    _assert_pipeline_options(converter, "mlx-spec")


def test_create_vlm_converter_uses_cuda_when_available(monkeypatch: pytest.MonkeyPatch):
    _install_torch_stub(monkeypatch, cuda_available=True)
    _ = _install_docling_stubs(monkeypatch)
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("platform.machine", lambda: "x86_64")

    converter = create_vlm_converter()

    _assert_pipeline_options(converter, "transformers-spec")


def test_create_vlm_converter_falls_back_to_cpu(monkeypatch: pytest.MonkeyPatch):
    _install_torch_stub(monkeypatch, cuda_available=False)
    _ = _install_docling_stubs(monkeypatch)
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("platform.machine", lambda: "x86_64")

    converter = create_vlm_converter()

    _assert_pipeline_options(converter, "transformers-spec")


def test_create_vlm_converter_import_error_when_missing_deps(monkeypatch: pytest.MonkeyPatch):
    original_import = builtins.__import__

    def _blocked_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name in {"torch", "transformers"}:
            raise ImportError("missing")
        return cast(object, original_import(name, globals, locals, fromlist, level))

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    with pytest.raises(
        ImportError,
        match="VLM support requires additional dependencies. Install with: pip install peripatos\\[vlm\\]",
    ):
        _ = create_vlm_converter()


def test_create_vlm_converter_times_out(monkeypatch: pytest.MonkeyPatch):
    _install_torch_stub(monkeypatch, cuda_available=False)
    document_module = cast(_DoclingDocumentModule, cast(object, _install_docling_stubs(monkeypatch)))
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("platform.machine", lambda: "x86_64")

    def _slow_convert(source: object) -> str:
        _ = source
        time.sleep(0.05)
        return "ok"

    document_module.DocumentConverter.convert_impl = staticmethod(_slow_convert)
    _ = document_module.DocumentConverter.call_count

    converter = create_vlm_converter(timeout_seconds=0.01)

    with pytest.raises(TimeoutError):
        _ = converter.convert("sample.pdf")


def test_create_vlm_converter_retries_once(monkeypatch: pytest.MonkeyPatch):
    _install_torch_stub(monkeypatch, cuda_available=False)
    document_module = cast(_DoclingDocumentModule, cast(object, _install_docling_stubs(monkeypatch)))
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("platform.machine", lambda: "x86_64")

    calls = {"count": 0}

    def _flaky_convert(source: object) -> str:
        _ = source
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("loop")
        return "ok"

    document_module.DocumentConverter.convert_impl = staticmethod(_flaky_convert)
    _ = document_module.DocumentConverter.call_count

    converter = create_vlm_converter(timeout_seconds=1.0)

    assert converter.convert("sample.pdf") == "ok"
    assert calls["count"] == 2


# Tests for PDFParser VLM integration


class _StubVLMDocument:
    def __init__(self, markdown: str) -> None:
        self._markdown = markdown

    def export_to_markdown(self) -> str:
        return self._markdown


class _StubVLMResult:
    def __init__(self, markdown: str) -> None:
        self.document = _StubVLMDocument(markdown)


class _StubVLMConverter:
    def __init__(self) -> None:
        self.converted = False

    def convert(self, source: object) -> _StubVLMResult:
        self.converted = True
        return _StubVLMResult("# Test Paper\n\n## Abstract\n\nVLM-parsed content.")


def test_pdf_parser_with_use_vlm_parameter_creates_vlm_converter(monkeypatch: pytest.MonkeyPatch, sample_pdf_path):
    """Test that PDFParser(use_vlm=True) creates a VLM converter."""
    from peripatos.eye.parser import PDFParser

    _install_torch_stub(monkeypatch, cuda_available=False)
    _ = _install_docling_stubs(monkeypatch)
    monkeypatch.setattr("platform.system", lambda: "Linux")

    stub_converter = _StubVLMConverter()
    monkeypatch.setattr("peripatos.eye.vlm.create_vlm_converter", lambda **kwargs: stub_converter)

    parser = PDFParser(use_vlm=True)
    metadata = parser.parse(sample_pdf_path)

    assert stub_converter.converted is True
    assert metadata.title == "Test Paper"
    assert metadata.abstract
    assert "VLM-parsed" in metadata.abstract


def test_pdf_parser_without_use_vlm_uses_standard_converter(monkeypatch: pytest.MonkeyPatch, sample_pdf_path):
    """Test that PDFParser() without use_vlm uses the standard converter."""
    from peripatos.eye.parser import PDFParser

    vlm_called = {"value": False}

    def _fake_vlm_converter(**kwargs):
        vlm_called["value"] = True
        return _StubVLMConverter()

    monkeypatch.setattr("peripatos.eye.vlm.create_vlm_converter", _fake_vlm_converter)

    standard_markdown = "# Standard Title\n\n## Abstract\n\nStandard content."

    class _StubStandardConverter:
        def convert(self, source: object) -> _StubVLMResult:
            return _StubVLMResult(standard_markdown)

    parser = PDFParser(converter=_StubStandardConverter())
    metadata = parser.parse(sample_pdf_path)

    assert vlm_called["value"] is False
    assert metadata.title == "Standard Title"


def test_pdf_parser_vlm_produces_valid_paper_metadata(monkeypatch: pytest.MonkeyPatch, sample_pdf_path):
    """Test that VLM parser produces valid PaperMetadata with all required fields."""
    from peripatos.eye.parser import PDFParser
    from peripatos.models import PaperMetadata

    _install_torch_stub(monkeypatch, cuda_available=False)
    _ = _install_docling_stubs(monkeypatch)
    monkeypatch.setattr("platform.system", lambda: "Linux")

    vlm_markdown = """# VLM Paper Title

Authors: Alice, Bob

## Abstract

This is the abstract from VLM parsing.

## 1. Introduction

VLM introduction content.

## 2. Methodology

VLM methodology content.

## 3. Conclusion

VLM conclusion content.

## References

[1] Reference 1
"""

    class _DetailedVLMConverter:
        def convert(self, source: object) -> _StubVLMResult:
            return _StubVLMResult(vlm_markdown)

    monkeypatch.setattr("peripatos.eye.vlm.create_vlm_converter", lambda **kwargs: _DetailedVLMConverter())

    parser = PDFParser(use_vlm=True)
    metadata = parser.parse(sample_pdf_path)

    assert isinstance(metadata, PaperMetadata)
    assert metadata.title == "VLM Paper Title"
    assert metadata.authors == ["Alice", "Bob"]
    assert "abstract from VLM" in metadata.abstract
    assert metadata.source_path == sample_pdf_path
    assert len(metadata.sections) > 0
    assert any("Introduction" in s.title for s in metadata.sections)
