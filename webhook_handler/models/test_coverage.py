from dataclasses import dataclass


@dataclass
class TestCoverage:
    """
    Holds all data about the generated test's coverage.
    """
    augmented_line_coverage: float | None
    non_augmented_line_coverage: float | None
    augmented_coverage: float | None
    non_augmented_coverage: float | None
    
    def coverage_exists(self) -> bool:
        return (
            self.augmented_line_coverage is not None
            and self.non_augmented_line_coverage is not None
            and self.augmented_coverage is not None
            and self.non_augmented_coverage is not None
        )
        
    def coverage_improved(self) -> bool:
        if not self.coverage_exists():
            return False
        
        return (
            self.augmented_line_coverage > self.non_augmented_line_coverage # type: ignore[comparison-overlap]
            and self.augmented_coverage > self.non_augmented_coverage # type: ignore[comparison-overlap]
        )