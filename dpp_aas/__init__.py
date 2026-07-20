"""FIBROTOR Digital Product Passport AAS generator."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pipeline import GenerationResult

__all__ = ["GenerationResult", "run_pipeline"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from .pipeline import GenerationResult, run_pipeline

        return {
            "GenerationResult": GenerationResult,
            "run_pipeline": run_pipeline,
        }[name]
    raise AttributeError(name)
