from fastapi import Request


def is_logged_in(request: Request) -> bool:
    return bool(request.session.get("admin_user_id"))


def is_user_logged_in(request: Request) -> bool:
    return bool(request.session.get("frontend_user_id"))
