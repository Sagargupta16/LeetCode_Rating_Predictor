"""Utilities for loading Keras models, including legacy HDF5 format migration."""

import json
import logging
import os
import shutil

logger = logging.getLogger(__name__)

# Keys that Keras 2.x saved in HDF5 configs but Keras 3.x no longer accepts
_LEGACY_KERAS_KEYS = {"time_major", "implementation"}


def load_keras_model(tf, model_path: str):
    """Load a Keras model, handling legacy HDF5 format from older TF versions.

    Keras 3.x expects ``.keras`` files to be zip archives.  Models saved with
    Keras 2.x may be HDF5 files with a ``.keras`` extension and may contain
    config keys (e.g. ``time_major``, ``implementation``) that Keras 3.x
    no longer recognises.  This helper detects that situation, patches the
    stored config, and loads via a temporary ``.h5`` copy.
    """
    # Fast-path: try the normal loader first
    try:
        return tf.keras.models.load_model(model_path)
    except Exception:
        pass  # fall through to legacy handling

    logger.info("Standard load failed — attempting legacy HDF5 migration")

    # Determine if the file is HDF5
    with open(model_path, "rb") as fh:
        is_hdf5 = fh.read(4) == b"\x89HDF"
    if not is_hdf5:
        raise RuntimeError(
            f"Cannot load {model_path}: not a valid .keras zip or HDF5 file"
        )

    # Create a temporary .h5 copy so Keras uses the HDF5 code path
    h5_path = (
        model_path.rsplit(".keras", 1)[0] + ".h5"
        if model_path.endswith(".keras")
        else model_path + ".tmp.h5"
    )
    shutil.copy2(model_path, h5_path)

    try:
        # Patch out keys that Keras 3.x doesn't accept
        import h5py

        with h5py.File(h5_path, "r+") as hf:
            if "model_config" in hf.attrs:
                raw = hf.attrs["model_config"]
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                config = json.loads(raw)
                _strip_legacy_keys(config)
                hf.attrs["model_config"] = json.dumps(config)

        return tf.keras.models.load_model(h5_path, compile=False)
    finally:
        if os.path.exists(h5_path):
            os.remove(h5_path)


def _strip_legacy_keys(obj):
    """Recursively remove keys that Keras 3.x doesn't recognise."""
    if isinstance(obj, dict):
        for key in [*obj.keys()]:
            if key in _LEGACY_KERAS_KEYS:
                del obj[key]
            else:
                _strip_legacy_keys(obj[key])
    elif isinstance(obj, list):
        for item in obj:
            _strip_legacy_keys(item)
