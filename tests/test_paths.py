import subprocess
import sys
import textwrap

from open_skill import paths

WORKER = textwrap.dedent("""
    import sys, time
    from pathlib import Path
    from open_skill import paths

    counter, n = Path(sys.argv[1]), int(sys.argv[2])
    for _ in range(n):
        with paths.locked(counter.with_name(".lock")):
            value = int(counter.read_text() or 0)
            time.sleep(0.001)  # widen the window between read and write
            counter.write_text(str(value + 1))
""")


def test_locked_serializes_read_modify_write_across_processes(tmp_path):
    counter = tmp_path / "counter"
    counter.write_text("0")
    procs, n = 4, 25
    workers = [subprocess.Popen([sys.executable, "-c", WORKER, str(counter), str(n)]) for _ in range(procs)]
    assert all(w.wait(timeout=120) == 0 for w in workers)
    assert int(counter.read_text()) == procs * n


def test_locked_can_be_taken_again_after_release(tmp_path):
    lock = tmp_path / "sub" / ".lock"
    for _ in range(3):
        with paths.locked(lock):
            pass
    assert lock.is_file()


def test_locked_releases_when_the_body_raises(tmp_path):
    lock = tmp_path / ".lock"
    try:
        with paths.locked(lock):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    with paths.locked(lock):  # would block forever if the first lock were still held
        pass
