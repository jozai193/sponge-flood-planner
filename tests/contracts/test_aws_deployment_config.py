from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_TRUSTED_HOSTS = "$HOSTNAME_FQDN,localhost,127.0.0.1"


def test_aws_bootstrap_allows_its_loopback_health_probe() -> None:
    bootstrap = (ROOT / "infra" / "aws" / "bootstrap-ec2.sh").read_text(encoding="utf-8")

    assert f"SPONGE_TRUSTED_HOSTS={REQUIRED_TRUSTED_HOSTS}" in bootstrap


def test_cloudformation_bootstrap_allows_its_loopback_health_probe() -> None:
    template = (ROOT / "infra" / "aws" / "sponge-judge-stack.yaml").read_text(encoding="utf-8")

    assert f"SPONGE_TRUSTED_HOSTS={REQUIRED_TRUSTED_HOSTS}" in template
