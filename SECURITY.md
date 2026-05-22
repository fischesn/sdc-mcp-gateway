# Security and Safety Policy

This repository contains a research prototype. It is not a medical device and must not be used for clinical care.

## Safety boundary

The prototype distinguishes between:

- read-only MCP Resources for exposing simulated or normalized device state;
- dry-run MCP Tools for validating action proposals.

Dry-run tools do not execute SDC write operations. They validate arguments, apply local policy checks, produce audit records, and return `executed=false`.

## Secrets

Do not commit API keys, certificates, VPN configuration, local gateway configuration, or real device credentials.

Local files such as `config/gateway.local.yaml`, `.env`, and `secrets/` are intentionally ignored by Git.

## Reporting issues

Please report safety- or security-relevant issues privately to the repository maintainer before public disclosure.