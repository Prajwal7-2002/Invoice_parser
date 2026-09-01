from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def create_upload() -> None:
    """Reserved upload contract; secure R2 upload support is the next milestone."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Secure uploads are not enabled yet. Do not send invoice data to this environment.",
    )
