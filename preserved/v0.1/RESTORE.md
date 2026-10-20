# Recover v0.1

This archive includes untracked source, documentation, tests, and original results. It excludes Git metadata, caches, secrets, environments, and backups. The original Git HEAD was absent.

Verify archive SHA-256 against manifest.json. Extract into a NEW empty directory inside this repository, never over current work:

```sh
mkdir -p preserved/v0.1/recovered
tar -xzf preserved/v0.1/tree.tar.gz -C preserved/v0.1/recovered
cd preserved/v0.1/recovered
python3 -m unittest discover -s tests -v
python3 -m continuum benchmark --seeds 30 --output regenerated
```

Compare regenerated/runs.csv and summary.json with the archived results. Source hashes are listed in manifest.json. No Git commit is required.
