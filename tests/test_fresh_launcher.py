"""Lifecycle guards must fail closed before touching another installation."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('fresh_fury', Path(__file__).parents[1] / 'scripts/fresh_fury.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_container_name_alone_does_not_prove_ownership():
    assert not launcher.owned_container({'Name':'/hp-nemotron-serve', 'Mounts':[]})
    assert not launcher.owned_container({'Name':'/cyber-siege-challenger', 'Mounts':[], 'Config':{'Labels':{'cyber-siege.repo':str(launcher.ROOT)}}})


def test_hero_requires_this_installations_model_mount():
    mount = launcher.MODEL_CACHE / 'models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4'
    assert launcher.owned_container({'Name':'/hp-nemotron-serve', 'Mounts':[{'Type':'bind','Source':str(mount)}]})
    assert not launcher.owned_container({'Name':'/hp-nemotron-serve', 'Mounts':[{'Type':'bind','Source':'/another/install/models'}]})


def test_unknown_listener_prevents_model_start(monkeypatch):
    monkeypatch.setattr(launcher, 'inspect', lambda _:None)
    monkeypatch.setattr(launcher, 'listening', lambda _:True)
    with pytest.raises(RuntimeError, match='another service'):
        launcher.validate_ownership()


def test_other_installation_prevents_any_stop(monkeypatch):
    mutations=[]
    monkeypatch.setattr(launcher, 'inspect', lambda _: {'Name':'/hp-nemotron-serve','Mounts':[]})
    monkeypatch.setattr(launcher, 'run', lambda *a,**k: mutations.append(a))
    with pytest.raises(RuntimeError, match='another installation'):
        launcher.stop()
    assert not mutations


def test_legacy_pid_does_not_authorize_an_unrelated_process(tmp_path, monkeypatch):
    # The current test PID exists, but its command is not app.serve.
    import os
    (tmp_path/'runtime').mkdir()
    (tmp_path/'runtime/app.pid').write_text(str(os.getpid()))
    monkeypatch.setattr(launcher, 'ROOT', tmp_path)
    signals=[]
    monkeypatch.setattr(launcher.signal, 'pidfd_send_signal', lambda *a:signals.append(a))
    with pytest.raises(RuntimeError, match='identity does not match'):
        launcher.stop_legacy()
    assert not signals


def permissions_module():
    spec=importlib.util.spec_from_file_location('model_permissions',Path(__file__).parents[1]/'scripts/public_model_permissions.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_service_can_read_shared_public_blobs_with_private_umask(tmp_path):
    repo=tmp_path/'models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4'
    repo.mkdir(mode=0o700)
    blob=tmp_path/'blobs/ab/weights';blob.parent.mkdir(mode=0o700,parents=True)
    blob.write_bytes(b'public weights');blob.chmod(0o600)
    (repo/'model.safetensors').symlink_to(blob)
    permissions_module().prepare(tmp_path)
    assert blob.stat().st_mode & 0o004
    assert blob.parent.stat().st_mode & 0o005 == 0o005
    assert repo.stat().st_mode & 0o005 == 0o005


def test_permissions_reject_private_symlink_before_any_mutation(tmp_path):
    cache=tmp_path/'cache';cache.mkdir()
    repo=cache/'models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4';repo.mkdir(mode=0o700)
    private=tmp_path/'private';private.write_bytes(b'not a model');private.chmod(0o600)
    (repo/'unexpected').symlink_to(private)
    with pytest.raises(ValueError,match='escapes'):
        permissions_module().prepare(cache)
    assert private.stat().st_mode & 0o777 == 0o600
    assert repo.stat().st_mode & 0o777 == 0o700


def test_verified_legacy_child_exits_without_pid_reuse_race(tmp_path, monkeypatch):
    import subprocess
    import sys
    import time
    (tmp_path/'app').mkdir();(tmp_path/'app/__init__.py').write_text('')
    (tmp_path/'app/serve.py').write_text('import time; time.sleep(60)')
    (tmp_path/'runtime').mkdir()
    child=subprocess.Popen([sys.executable,'-m','app.serve'],cwd=tmp_path)
    try:
        (tmp_path/'runtime/app.pid').write_text(str(child.pid))
        monkeypatch.setattr(launcher,'ROOT',tmp_path)
        launcher.stop_legacy()
        assert child.wait(timeout=2)<0
    finally:
        if child.poll() is None:
            child.terminate();child.wait(timeout=2)
