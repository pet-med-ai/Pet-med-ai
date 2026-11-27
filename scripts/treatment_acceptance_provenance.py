"""Read candidate metadata from the pinned Git commit, including in shallow clones."""
import subprocess


def checkout_revision(git):
    commit = subprocess.check_output([*git, "rev-parse", "--verify", "HEAD^{commit}"], text=True).strip()
    raw = subprocess.check_output([*git, "cat-file", "commit", commit])
    # A shallow checkout can omit the parent objects, but their IDs are in this header.
    headers = raw.partition(b"\n\n")[0].split(b"\n")
    tree = headers[0].removeprefix(b"tree ").decode("ascii")
    parents = [line[7:].decode("ascii") for line in headers if line.startswith(b"parent ")]
    return {"commit": commit, "tree": tree, "parents": parents}
