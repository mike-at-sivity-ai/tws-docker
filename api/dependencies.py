from fastapi import HTTPException
from ib_insync import IB


class IBState:
    def __init__(self) -> None:
        self.ib = IB()


ib_state = IBState()


def get_ib() -> IB:
    if not ib_state.ib.isConnected():
        raise HTTPException(
            status_code=503,
            detail="TWS is not connected. The service may still be starting up.",
        )
    return ib_state.ib
