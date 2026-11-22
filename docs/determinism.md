# Determinism

Reports and coverage manifests are generated in sorted key/file/ref order. Commit SHAs and timestamps remain native Git values. Before comparing two runs, normalize absolute repository paths and timestamps. The hash comparison test treats two normalized JSON documents as identical only after sorted serialization.
