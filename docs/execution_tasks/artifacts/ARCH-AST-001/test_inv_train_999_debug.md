# INV-TRAIN-999 Debug Artifact

Debug test skeleton for invariant TRAIN-999 (development artifact).

```python

import pytest
from sqlalchemy.exc import IntegrityError

class TestInvTrain999Debug:
    """
    INV-TRAIN-999
    Classe: A
    Obrigação A: debug
    Obrigação B: debug
    """
    def test_sync_valid(self, db):
        pass

    def test_sync_invalid(self, db):
        with pytest.raises(IntegrityError):
            pass

    async def test_async_valid(self, async_db):
        pass

    async def test_async_invalid(self, async_db):
        with pytest.raises(IntegrityError):
            pass
        
    async def test_async_with_async_raises(self, *, async_db):
        async with pytest.raises(IntegrityError):
            pass
```
