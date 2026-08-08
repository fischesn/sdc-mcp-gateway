# WP3 Software SDC Protocol Evidence

## Status and scope

- Completed: 2026-08-08
- Primary stack: `sdc11073` 2.4.1
- Profiles: monitor, ventilator, heterogeneous/unsupported
- Repetitions: 5 per profile
- Full prototype suite after WP3: 77 tests passed
- Focused profile/extractor suite: 8 tests passed
- Provider placement: process separate from the gateway consumer
- Physical medical devices: none available
- Hold-out LLM evaluation: not executed

This is a local-host software-reference experiment. It is not evidence for a
physical device, a clinical network, clinical real-time behavior, or general
SDC conformance.

## Reproduction

Use an active local IPv4 interface address in place of `<local-ip>`:

```powershell
sdc-mcp-gateway evaluate-sdc-protocol `
  --local-ip <local-ip> `
  --repetitions 5 `
  --discovery-timeout-s 0.3 `
  --output data/revision/development/wp3-protocol-testbed.json
```

The command creates a short-lived test identity, runs each provider in a
separate hidden process, initializes the gateway's `Sdc11073Consumer`, reads
all advertised MCP resources, records unmapped and unsupported elements, and
removes the temporary key material and provider process afterward. The JSON
report omits the host address, process identifier, temporary paths, and dynamic
port numbers.

## Exercised protocol elements

- WS-Discovery listener plus Probe/Hello attempt;
- mutual TLS with an ephemeral experiment-only identity;
- HTTPS and SOAP `GetMdib` exchange;
- BICEPS XML schema validation;
- `ConsumerMdib` initialization;
- descriptor and state extraction;
- semantic mapping and read-only MCP resource construction.

Subscriptions, periodic reports, effective Set Service calls, ActivateOperation
invocations, physical devices, and clinical network behavior were not
exercised. The provider can contain operation descriptors to test explicit
unsupported-element reporting, but the gateway never invokes them.

## Primary results

| Profile | Snapshots | Resource reads | Descr./states | Mapping | Median local-host path |
|---|---:|---:|---:|---:|---:|
| Monitor | 5/5 | 40/40 | 12/10 | 3/4 (75%) | 1.133 s |
| Ventilator | 5/5 | 40/40 | 11/10 | 3/4 (75%) | 1.069 s |
| Heterogeneous | 5/5 | 40/40 | 15/12 | 1/3 (33%) | 1.066 s |
| **Total** | **15/15** | **120/120** | - | **7/11 (64%)** | - |

The median covers connection, TLS/HTTPS/SOAP, `GetMdib`, XML/MDIB processing,
normalization, catalogue construction, and eight resource reads. It is a
software-reference engineering measurement, not clinical-network latency.

The heterogeneous profile made five unsupported descriptor containers visible:
one Clock, one SCO, and three ActivateOperation containers. Corresponding
structural and operation states were also reported rather than silently mapped.
Unmapped metric codes were reported for every profile.

## WS-Discovery limitation

The persistent listener was started before the provider process, and the
standard Probe/Hello path was attempted in all 15 repetitions. On this Windows
host, two same-interface processes did not both receive the multicast traffic,
so discovery returned 0/15 matches. The runner therefore used the XAddr
published by the provider process for the subsequent TLS/SOAP path. This
fallback is counted explicitly in the report and is not presented as successful
WS-Discovery interoperability. A two-host or virtual-network rerun remains
necessary to evaluate discovery delivery independently of this host behavior.

## Second implementation attempt

The independent SDCLib/C repository was shallow-cloned into a temporary
directory and configured with CMake and GNU C++ 13.2. Compiler detection and
OpenSSL 3.6.1 succeeded, but configuration stopped because the required XercesC
include tree was unavailable. No executable provider was produced, so no
cross-stack interoperability result is claimed. The temporary source and build
directories were removed after the attempt.

## SDCcc assessment

SDCcc assumes the SDC consumer role and evaluates a provider/DUT. It could
therefore assess the virtual provider, but it would not validate this gateway,
which is also a consumer. The documented SDCcc setup additionally requires TLS.
No Java runtime or active container engine was available in the evaluation
environment, so SDCcc was not executed. The paper states this boundary rather
than implying gateway conformance from a provider-oriented test.
