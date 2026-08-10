from pathlib import Path

import pytest

from sdc_mcp_gateway.revision.consolidated_evaluation import (
    ConsolidatedEvaluationConfig,
    run_consolidated_evaluation,
)


def test_consolidated_evaluation_requires_relative_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repository-relative"):
        run_consolidated_evaluation(
            ConsolidatedEvaluationConfig(
                project_root=Path.cwd(),
                output_dir=tmp_path,
            )
        )
