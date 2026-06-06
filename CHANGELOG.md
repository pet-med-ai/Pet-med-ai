# Changelog

All notable changes to Pet-Med-AI are tracked here.

This project uses manual release records plus git tags. Keep this file concise; detailed operational evidence belongs in `docs/ops/releases/`.

## Unreleased

### Added
- Release / Upgrade Framework V1.
- Version / Build Info V1.
- Feature Flag / Safety Gate V1.
- Release Status / Admin Ops Dashboard V1.
- EMR real import create-only pilot path protected by feature flags.

### Changed
- Release validation now checks upgrade readiness, system version, feature flags, and ops dashboard coverage.

### Safety
- High-risk features must remain disabled by default.
- Real EMR import execution requires explicit feature flag enablement, clinical approval, rollback snapshot, smoke tests, and pilot checklists.
