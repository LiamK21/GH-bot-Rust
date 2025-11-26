from dataclasses import dataclass


@dataclass
class TestCoverage:
    """
    Holds all data about the generated test's coverage.
    """
    file_line_coverage_with: float | None
    file_line_coverage_without: float | None
    suite_line_coverage_with: float | None
    suite_line_coverage_without: float | None
    
    def coverage_exists(self) -> bool:
        return (
            self.file_line_coverage_with is not None
            and self.file_line_coverage_without is not None
            and self.suite_line_coverage_with is not None
            and self.suite_line_coverage_without is not None
        )
        
    def coverage_improved(self) -> bool:
        if not self.coverage_exists():
            return False
        
        return (
            self.file_line_coverage_with > self.file_line_coverage_without # type: ignore[comparison-overlap]
            and self.suite_line_coverage_with > self.suite_line_coverage_without # type: ignore[comparison-overlap]
        )