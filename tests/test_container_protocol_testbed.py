from pathlib import Path

import pytest

from sdc_mcp_gateway.sdc.container_protocol_testbed import (
    ContainerProtocolTestbedConfig,
    run_container_protocol_testbed,
)


def test_container_protocol_testbed_rejects_unknown_profile(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown profiles"):
        run_container_protocol_testbed(
            ContainerProtocolTestbedConfig(
                project_root=Path.cwd(),
                mapping_path=Path("config/sdc_mie.yaml"),
                output_path=tmp_path / "report.json",
                profiles=("not-a-profile",),
                repetitions=1,
                build_image=False,
            )
        )
