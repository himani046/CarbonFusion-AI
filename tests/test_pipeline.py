import numpy as np
import pandas as pd
import pytest
from src.pipeline import prepare, score

def test_score_perfect():
    m=score(np.array([2,4,6]),np.array([2,4,6]))
    assert m['rmse_mg_ha']==0
    assert m['r2']==1

def test_missing_columns_raises():
    with pytest.raises(ValueError, match='Missing columns'):
        prepare(pd.DataFrame({'agbd':[10]}))
