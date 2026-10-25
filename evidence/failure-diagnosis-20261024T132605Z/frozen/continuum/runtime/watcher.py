from .common import confined, digest


class FixtureWatcher:
    """Only an explicitly approved fixture directory; no arbitrary filesystem watch."""
    def __init__(self, runtime):
        self.runtime=runtime
    def poll(self):
        root=self.runtime.capabilities.fixture_root
        known=self.runtime.db.get('fixture_hashes',{})
        if not root.is_dir():return
        for entry in sorted(root.glob('*.md')):
            try:path=confined(root,entry.name,exists=True)
            except ValueError:continue
            if path.stat().st_size>16000:continue
            fingerprint=digest(path.read_bytes())
            if known.get(entry.name)!=fingerprint:
                self.runtime.observe('document.available',{'path':entry.name,'checksum':fingerprint},source='fixture-watcher',event_id='doc-'+digest({'path':entry.name,'hash':fingerprint}))
                known[entry.name]=fingerprint
        self.runtime.db.set('fixture_hashes',known)
