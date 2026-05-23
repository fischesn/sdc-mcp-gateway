# Implementation Notes

## Why v0.1 is read-only

The first version must establish a trustworthy observation path before any tool execution is considered. This keeps the experimental risk low and allows us to validate the semantic mapping independently of actuator/control risks.

## Why the paper is not in this repository

The manuscript is maintained separately in Overleaf. This repository contains only software, configuration, experiments, and development documentation.

## Why Python first

Python is used for the research prototype because it gives fast iteration, transparent instrumentation, and direct access to existing SDC demonstration tooling. Product-oriented or regulatory-grade implementations may later require a different stack.

## Current limitations

- The real `sdc11073` adapter is not implemented yet.
- Event subscriptions are not implemented yet.
- Tool generation is not implemented yet.
- Policy evaluation is a read-only deny-all placeholder.
- No authentication or authorization is implemented in v0.1.


## Real SDC validation note

For practical first-test instructions, see [REAL_SDC_TESTING.md](REAL_SDC_TESTING.md).
