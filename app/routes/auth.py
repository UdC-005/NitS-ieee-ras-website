from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
)

from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User

from ..auth import (
    hash_password,
    verify_password,
    create_access_token,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


@router.post("/register")
def register(
    request: Request,

    full_name: str = Form(...),
    scholar_id: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),

    db: Session = Depends(get_db)
):

    full_name = full_name.strip()
    scholar_id = scholar_id.strip()
    email = email.strip().lower()

    # Password confirmation

    if password != confirm_password:

        return RedirectResponse(
            "/register?error=Passwords+do+not+match",
            status_code=303
        )

    # Password length

    if len(password) < 8:

        return RedirectResponse(
            "/register?error=Password+must+be+at+least+8+characters",
            status_code=303
        )

    # Existing email

    existing_email = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_email:

        return RedirectResponse(
            "/register?error=Email+already+registered",
            status_code=303
        )

    # Existing scholar ID

    existing_scholar = (
        db.query(User)
        .filter(User.scholar_id == scholar_id)
        .first()
    )

    if existing_scholar:

        return RedirectResponse(
            "/register?error=Scholar+ID+already+registered",
            status_code=303
        )

    # Create user

    user = User(
        full_name=full_name,
        scholar_id=scholar_id,
        email=email,
        password_hash=hash_password(password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return RedirectResponse(
        "/login?registered=true",
        status_code=303
    )


@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),

    db: Session = Depends(get_db)
):

    email = email.strip().lower()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:

        return RedirectResponse(
            "/login?error=Invalid+email+or+password",
            status_code=303
        )

    if not verify_password(
        password,
        user.password_hash
    ):

        return RedirectResponse(
            "/login?error=Invalid+email+or+password",
            status_code=303
        )

    token = create_access_token(user.id)

    response = RedirectResponse(
        "/",
        status_code=303
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=3600
    )

    return response


@router.post("/logout")
def logout():

    response = RedirectResponse(
        "/",
        status_code=303
    )

    response.delete_cookie(
        "access_token"
    )

    return response