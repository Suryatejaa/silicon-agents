"""Phase 3 CLI wrapper."""

from __future__ import annotations

import click

from silicon_agents.agents.agent01_verify import VerificationAgent
from silicon_agents.agents.agent02_yield import YieldAgent
from silicon_agents.core.schemas import VerifyRequest, YieldRequest


@click.group()
def cli() -> None:
    """Silicon Agents CLI."""


@cli.command()
@click.option("--report", "report_path", required=True, type=click.Path(exists=True))
@click.option("--mode", default="coverage", type=click.Choice(["coverage", "triage"]))
def verify(report_path: str, mode: str) -> None:
    """Run Agent 01 from the CLI."""
    click.echo(f"Phase 3 stub: use the API or frontend for now. Requested {mode} with {report_path}.")


@cli.command(name="yield")
@click.option("--data", "data_path", required=True, type=click.Path(exists=True))
@click.option("--mode", default="ate", type=click.Choice(["ate", "spc"]))
def yield_cmd(data_path: str, mode: str) -> None:
    """Run Agent 02 from the CLI."""
    click.echo(f"Phase 3 stub: use the API or frontend for now. Requested {mode} with {data_path}.")


if __name__ == "__main__":
    cli()

