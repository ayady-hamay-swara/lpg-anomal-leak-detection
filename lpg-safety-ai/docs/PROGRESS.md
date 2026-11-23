# Build progress

## M0
- Repository structure created.
- Placeholder plant configuration and rationalised alarm definitions added.
- Initial setup and test harness in progress.

## M1
- Implemented LPG saturation pressure, density, level expansion and thermal-lag helpers.
- Pressure reference and thermal expansion tests pass.

## M2-M3
- Implemented deterministic simulator engine, tag frames, controls, reset, speed and 12 scenario entry points.
- Engine and scenario tests pass.

## M4-M6
- Added alarm rationalisation loader, alarm state engine, assessment structure, risk scoring and prediction helpers.
- OPC UA remains a read-only stub.

## M7-M10
- Laravel authentication, HMI routes, polling API, playground controls and Blade pages are scaffolded.
- Both services run locally; notification jobs and full scenario scoring remain follow-up implementation work.
