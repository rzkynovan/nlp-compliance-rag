"""
data_split.py — Pembagian dataset Gate Classifier Regulasi Perusahaan.

Rasio 80/10/10 (train/validation/test), stratified, sesuai Subbab 3.1.2
proposal. Dipakai bersama oleh train_indobert.py, train_gpt_finetune.py, dan
evaluate_gates.py agar ketiga pendekatan dievaluasi pada partisi uji yang sama
dan partisi validasi tidak pernah tumpang tindih dengan partisi uji.
"""

from typing import List, Tuple

from sklearn.model_selection import train_test_split

TRAIN_RATIO = 0.8
VAL_RATIO   = 0.1
TEST_RATIO  = 0.1
DEFAULT_SEED = 42


def split_80_10_10(
    texts: List[str],
    labels: List[int],
    seed: int = DEFAULT_SEED,
) -> Tuple[List[str], List[str], List[str], List[int], List[int], List[int]]:
    """
    Returns: X_train, X_val, X_test, y_train, y_val, y_test
    """
    X_train, X_hold, y_train, y_hold = train_test_split(
        texts, labels,
        test_size=VAL_RATIO + TEST_RATIO,
        stratify=labels,
        random_state=seed,
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_hold, y_hold,
        test_size=TEST_RATIO / (VAL_RATIO + TEST_RATIO),
        stratify=y_hold,
        random_state=seed,
    )
    return X_train, X_val, X_test, y_train, y_val, y_test
