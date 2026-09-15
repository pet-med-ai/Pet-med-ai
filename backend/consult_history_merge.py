"""Preserve mixed clinician/intake history when appending a consult snapshot.

Legacy history has no reliable machine-owned region or separate provenance
field. Treat it as opaque text: never parse, rewrite, strip, or remove it.
Identical complete snapshots already present on line boundaries are a no-op.
Changed snapshots append; they do not replace historical answers.
This helper does not write records or provide concurrent-update protection.
"""

from typing import Optional


UPDATE_HEADING = "【动态问诊更新补充】"


def _has_complete_block(existing: str, incoming: str) -> bool:
    offset = 0
    while True:
        index = existing.find(incoming, offset)
        if index < 0:
            return False
        end = index + len(incoming)
        starts_line = index == 0 or existing[index - 1] in "\r\n"
        ends_line = end == len(existing) or existing[end] in "\r\n"
        if starts_line and ends_line:
            return True
        offset = index + 1


def preserve_consult_history(
    existing: Optional[str], generated: Optional[str]
) -> str:
    """Keep every existing character and append a new nonempty snapshot once.

    De-duplication is exact and textual; it is not proof of record identity.
    A modified snapshot may repeat earlier questions. That is intentional:
    retaining an older narrative is safer than guessing which text to remove.
    """
    if existing is not None and not isinstance(existing, str):
        raise TypeError("existing history must be text or None")
    if generated is not None and not isinstance(generated, str):
        raise TypeError("generated history must be text or None")

    previous = existing if existing is not None else ""
    incoming = generated if generated is not None else ""
    if not incoming.strip():
        return previous
    if not previous:
        return incoming
    if _has_complete_block(previous, incoming):
        return previous
    return previous + "\n\n" + UPDATE_HEADING + "\n" + incoming
