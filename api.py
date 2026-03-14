from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from signal_engine import DEFAULT_WATCHLIST, SignalEngineError, generate_signal

app = FastAPI(title="BiBroker Signal API", version="0.1.0")


class SignalRequest(BaseModel):
    tickers: list[str] | None = Field(default=None, description="Ticker symbols to evaluate")
    notes: str | None = Field(default=None, description="Optional analyst notes")
    timeout: float | None = Field(default=None, description="Timeout in seconds for LLM call")
    retries: int | None = Field(default=None, description="Retry attempts")


class SignalResponse(BaseModel):
    action: str
    confidence: float | str
    rationale: str
    stop_loss: str | None = None
    raw: dict | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "default_watchlist_count": len(DEFAULT_WATCHLIST)}


@app.post("/signal", response_model=SignalResponse)
def signal(payload: SignalRequest) -> SignalResponse:
    try:
        result = generate_signal(
            tickers=payload.tickers or [item["ticker"] for item in DEFAULT_WATCHLIST],
            notes=payload.notes,
            timeout=payload.timeout,
            retries=payload.retries,
        )
    except SignalEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SignalResponse(
        action=result.get("action", "unknown"),
        confidence=result.get("confidence", "?"),
        rationale=result.get("rationale", ""),
        stop_loss=result.get("stop_loss"),
        raw=result,
    )
