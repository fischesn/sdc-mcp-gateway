# SDCri cross-stack experiment

This experiment evaluates the gateway's Python `sdc11073` consumer against the
independent Java SDCri provider implementation. It uses the unmodified SDCri
`provider1` example MDIB, mutual TLS with separate ephemeral provider and consumer
identities, WS-Discovery, HTTPS/SOAP GetMdib, normalized snapshot extraction, and
read access to every resulting MCP resource.

The experiment does not use a physical medical device or clinical network. It does
not test subscriptions, continuous reports, SetService, or ActivateOperation.

## Pinned software

- SDCri tag: `sdc-ri-7.0.0`
- SDCri commit: `cc46b3b8e113c80ef4977920160b858ac72f1343`
- Java: Eclipse Temurin 17.0.20+8
- Gateway consumer: `sdc11073` 2.4.1

## Preparing SDCri

With Java 17 or newer selected as `JAVA_HOME`, clone the official SDCri repository,
check out the pinned tag, and build the example plus its four internal runtime JARs:

```powershell
git clone https://github.com/Draegerwerk/sdc-ri.git
Set-Location sdc-ri
git checkout sdc-ri-7.0.0
./gradlew.bat :glue-examples:classes :common:jar :biceps:jar :dpws:jar :glue:jar `
  --no-daemon --console=plain
./gradlew.bat :glue-examples:writeRuntimeClasspath `
  --init-script <gateway-repo>\scripts\sdcri-runtime-classpath.init.gradle `
  --no-daemon --console=plain
```

The init script only adds a task that writes Gradle's resolved runtime classpath; it
does not alter SDCri source code.

## Running the experiment

From the gateway repository with the `sdc` optional dependency installed:

```powershell
python -m sdc_mcp_gateway.sdc.sdcri_testbed `
  --java <jdk>\bin\java.exe `
  --classpath <sdc-ri>\glue-examples\build\runtime-classpath.txt `
  --local-ip 127.0.0.1 `
  --repetitions 5 `
  --output experiments\2026-08-10-sdcri-cross-stack\sdcri-cross-stack.json
```

Loopback keeps the measurement independent of host firewall policy. The runner also
supports an active non-loopback IPv4 interface and records whether WS-Discovery
succeeded or a directed XAddr fallback was required.

## Interpretation

All five MDIB reads and all 40 MCP resource reads succeeded. The default SDCri example
uses generic metric codes that are outside the checked-in SDC-MIE table, so the 0/11
mapping result is an explicit semantic-coverage result, not a transport failure.
