# AWS judge deployment

`infra/aws/sponge-judge-stack.yaml` deploys the exact submitted SPONGE commit to a
single Ubuntu EC2 host for short-lived judging access. It creates:

- one `t3.medium` instance in CPU-credit `standard` mode;
- one encrypted 30 GB `gp3` root volume;
- one static Elastic IP;
- a security group exposing only HTTP and HTTPS; and
- Caddy automatic HTTPS at `<elastic-ip>.sslip.io`.

The host installs Docker, creates 4 GB of swap for image builds, generates the
database password locally, starts the production Compose stack, and waits for the
public readiness endpoint. No database password, SSH key, or application secret is
stored in CloudFormation or source control.

## Deploy

Create a CloudFormation stack in `us-east-1` from
`infra/aws/sponge-judge-stack.yaml`. Keep the default parameters unless a different
tested commit or instance size is intentional. Stack creation incurs AWS usage; set
a cost budget and verify available credits before deployment.

For a console launch without CloudFormation, paste `infra/aws/bootstrap-ec2.sh` into
EC2 user data after replacing `__SPONGE_PUBLIC_IP__` with the allocated Elastic IP.
Launch with automatic public IPv4 assignment disabled, then associate that Elastic IP
with the new instance. This ensures the trusted host and TLS certificate use the final
stable address from the first boot.

CloudFormation finishes creating infrastructure before the Docker image build and
certificate issuance necessarily finish. Use the stack's `ReadinessUrl` output and
wait for HTTP 200 before publishing `JudgeDemoUrl`.

The live 2026-09-21 judge deployment was launched manually on `t3.small` because
the account's Free Plan disabled `t3.medium`. The 4 GB swap configured by the
bootstrap keeps the production image build viable on the smaller host.

## Verify

Run the public smoke suite after readiness succeeds:

```powershell
$env:SPONGE_BASE_URL = '<JudgeDemoUrl without ?tour=1>'
pnpm smoke:production
```

Confirm `/api/v1/health`, `/api/v1/ready`, the judge tour, and the prepared demo
before replacing any existing public link.

## Remove after judging

Delete the CloudFormation stack after judging and confirm that the instance, root
volume, Elastic IP, and security group are gone. An allocated Elastic IP continues
to incur charges even when it is not attached, so do not leave a failed or partial
stack behind.
