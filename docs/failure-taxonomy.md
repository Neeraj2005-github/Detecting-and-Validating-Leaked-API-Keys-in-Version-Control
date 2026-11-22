# Failure taxonomy

| Case category | Gitleaks | Wrapper compensation |
|---|---|---|
| Archives | Misses archived nested files | Records archive as skipped |
| Submodules | Does not follow external submodule objects | Records submodule and performs no external fetch |
| LFS pointers | May scan pointer text, not LFS blob | Records LFS pointer as skipped |
| Base64/URL encoding | Rule-dependent miss | Reports limitation and measures as missed |
| Split secret | Misses split credential | Documents miss; no unsafe reconstruction |
| Deleted branch | Misses unreachable commit unless retained by a supplied ref | Coverage reports unreachable objects |
| Stash | Not a normal reachable branch | Stash handling is measured separately |
| Binary/oversized/too-long | Skips content | Coverage manifest counts skipped files and lines |
| False-positive documentation | May detect examples | Allowlist and suppression metadata |
