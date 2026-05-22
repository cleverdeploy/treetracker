import uuid

from app import ratelimit


def test_under_limit():
    uid = uuid.uuid4()
    for _ in range(ratelimit.MAX_REQ):
        assert ratelimit.check(uid)


def test_over_limit():
    uid = uuid.uuid4()
    for _ in range(ratelimit.MAX_REQ):
        assert ratelimit.check(uid)
    assert ratelimit.check(uid) is False
