"""Project-local, process-safe limit: <=2 model subprocesses, <=2,000 invocations."""
import fcntl
import sqlite3
import time
from .common import ROOT,utc


class ModelSlot:
    def __init__(self,cancel,maximum=2000):self.cancel,self.maximum=cancel,maximum;self.file=None
    def __enter__(self):
        from .providers import ProviderError
        directory=ROOT/'.runtime';directory.mkdir(exist_ok=True)
        deadline=time.monotonic()+95
        while self.file is None:
            for i in range(2):
                f=(directory/f'provider-slot-{i}.lock').open('a+')
                try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);self.file=f;break
                except BlockingIOError:f.close()
            if self.file is not None:break
            if self.cancel.wait(.1) or time.monotonic()>deadline:
                raise ProviderError('model slot unavailable or cancelled',known_unsent=True)
        try:
            db=sqlite3.connect(directory/'provider-ledger.sqlite',timeout=10)
            try:
                with db:
                    db.execute('CREATE TABLE IF NOT EXISTS invocations(id INTEGER PRIMARY KEY,started TEXT)')
                    db.execute('BEGIN IMMEDIATE')
                    if db.execute('SELECT COUNT(*) FROM invocations').fetchone()[0]>=self.maximum:
                        raise ProviderError('project model-call ceiling reached',known_unsent=True)
                    db.execute('INSERT INTO invocations(started) VALUES (?)',(utc(),))
            finally:db.close()
        except BaseException:
            self.__exit__(None,None,None);raise
        return self
    def __exit__(self,*args):
        if self.file:
            fcntl.flock(self.file,fcntl.LOCK_UN);self.file.close();self.file=None
