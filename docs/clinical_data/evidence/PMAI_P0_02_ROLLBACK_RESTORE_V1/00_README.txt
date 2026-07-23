PMAI-P0-02 sanitized external evidence workspace

This directory must remain outside the Pet-Med-AI Git repository.
Do not place raw dumps, logical export archives, connection URLs, passwords,
tokens, owner contact information, patient names, or free-text clinical data here.

Recommended operation sequence:
1. Fill 01_environment_sanitized.txt with non-secret labels only.
2. Fill 02_provider_backup_sanitized.txt after provider backup/PITR selection.
3. Capture source baseline with the collector's capture command.
4. Restore into a disposable, isolated staging target.
5. Fill 03_provider_restore_sanitized.txt.
6. Capture restore target with the collector's capture command.
7. Run compare, scan, and hash-manifest commands.
8. Keep P0-02 on HOLD until repository evidence is reviewed and --require-complete passes.
