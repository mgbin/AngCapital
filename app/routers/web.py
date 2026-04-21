from datetime import date
import hashlib
import hmac
import os
import secrets
import uuid
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud import (
    create_frontend_user,
    create_report,
    featured_report,
    get_report_by_id,
    get_report_by_slug,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    list_all_reports,
    list_all_users,
    list_reports,
    update_report,
    update_report_status,
    update_user_admin_fields,
)
from app.database import get_db
from app.dependencies import is_logged_in, is_user_logged_in
from app.schemas import FrontendUserCreate, ReportCreate


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()
UPLOAD_DIRECTORY = "app/static/uploads/reports"


def report_tags(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


templates.env.globals["report_tags"] = report_tags


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${derived_key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, password_hash = stored_hash.split("$", 1)
    except ValueError:
        return False
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return hmac.compare_digest(derived_key.hex(), password_hash)


def slugify_title(title: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "-" for character in title.strip())
    compact = "-".join(part for part in normalized.split("-") if part)
    if not compact:
        compact = "report"
    return f"{compact}-{uuid.uuid4().hex[:8]}"


def store_uploaded_pdf(upload: UploadFile) -> str:
    filename = upload.filename or "report.pdf"
    extension = os.path.splitext(filename)[1].lower() or ".pdf"
    safe_name = f"{uuid.uuid4().hex}{extension}"
    target_path = os.path.join(UPLOAD_DIRECTORY, safe_name)
    file_bytes = upload.file.read()
    with open(target_path, "wb") as output_file:
        output_file.write(file_bytes)
    return f"/static/uploads/reports/{quote(safe_name)}"


def get_current_frontend_user(request: Request, db: Session) -> Optional[Dict[str, Any]]:
    user_id = request.session.get("frontend_user_id")
    if not user_id:
        return None
    user = get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        request.session.pop("frontend_user_id", None)
        request.session.pop("frontend_username", None)
        return None
    return {"id": user.id, "username": user.username, "email": user.email, "level": user.level}


def render_template(
    request: Request,
    template_name: str,
    context: Dict[str, Any],
    db: Optional[Session] = None,
    status_code: int = status.HTTP_200_OK,
):
    frontend_user = get_current_frontend_user(request, db) if db else None
    merged_context = {
        "request": request,
        "settings": settings,
        "frontend_user": frontend_user,
        "nav_mode": "site",
        **context,
    }
    return templates.TemplateResponse(template_name, merged_context, status_code=status_code)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = Query("", alias="q"), db: Session = Depends(get_db)):
    search_query = q.strip()
    reports = list_reports(db, keyword=search_query)
    featured = None if search_query else (featured_report(db) or (reports[0] if reports else None))
    return render_template(
        request,
        "index.html",
        {
            "page_title": "Home",
            "featured": featured,
            "reports": reports,
            "search_query": search_query,
        },
        db=db,
    )


@router.get("/reports/{slug}", response_class=HTMLResponse)
def report_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    report = get_report_by_slug(db, slug)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return render_template(
        request,
        "report_detail.html",
        {"page_title": report.title, "report": report},
        db=db,
    )


@router.get("/contact", response_class=HTMLResponse)
def contact_page(request: Request, db: Session = Depends(get_db)):
    return render_template(
        request,
        "contact.html",
        {"page_title": "Contact", "search_query": ""},
        db=db,
    )


@router.get("/login", response_class=HTMLResponse)
def frontend_login_page(request: Request, db: Session = Depends(get_db)):
    if is_user_logged_in(request):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        request,
        "auth/login.html",
        {"page_title": "User Login", "error": None},
        db=db,
    )


@router.post("/login", response_class=HTMLResponse)
def frontend_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, email.strip().lower())
    if not user or not verify_password(password, user.password_hash):
        return render_template(
            request,
            "auth/login.html",
            {"page_title": "User Login", "error": "邮箱或密码错误"},
            db=db,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    request.session["frontend_user_id"] = user.id
    request.session["frontend_username"] = user.username
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/register", response_class=HTMLResponse)
def frontend_register_page(request: Request, db: Session = Depends(get_db)):
    if is_user_logged_in(request):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        request,
        "auth/register.html",
        {"page_title": "User Register", "error": None},
        db=db,
    )


@router.post("/register", response_class=HTMLResponse)
def frontend_register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    clean_username = username.strip()
    clean_email = email.strip().lower()

    if len(clean_username) < 2:
        return render_template(
            request,
            "auth/register.html",
            {"page_title": "User Register", "error": "用户名至少需要 2 个字符"},
            db=db,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if len(password) < 6:
        return render_template(
            request,
            "auth/register.html",
            {"page_title": "User Register", "error": "密码至少需要 6 位"},
            db=db,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if password != confirm_password:
        return render_template(
            request,
            "auth/register.html",
            {"page_title": "User Register", "error": "两次输入的密码不一致"},
            db=db,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if get_user_by_username(db, clean_username):
        return render_template(
            request,
            "auth/register.html",
            {"page_title": "User Register", "error": "用户名已被占用"},
            db=db,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if get_user_by_email(db, clean_email):
        return render_template(
            request,
            "auth/register.html",
            {"page_title": "User Register", "error": "邮箱已注册"},
            db=db,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = create_frontend_user(
        db,
        FrontendUserCreate(
            username=clean_username,
            email=clean_email,
            password_hash=hash_password(password),
            level="User",
        ),
    )
    request.session["frontend_user_id"] = user.id
    request.session["frontend_username"] = user.username
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def frontend_logout(request: Request):
    request.session.pop("frontend_user_id", None)
    request.session.pop("frontend_username", None)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/me", response_class=HTMLResponse)
def frontend_profile(request: Request, db: Session = Depends(get_db)):
    if not is_user_logged_in(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    frontend_user = get_current_frontend_user(request, db)
    if not frontend_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        request,
        "auth/profile.html",
        {"page_title": "Profile", "profile_user": frontend_user},
        db=db,
    )


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse(url="/admin/reports/new", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        request,
        "admin/login.html",
        {"page_title": "Admin Login", "error": None, "nav_mode": "admin_auth"},
    )


@router.post("/admin/login", response_class=HTMLResponse)
def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if username == settings.admin_username and password == settings.admin_password:
        request.session["admin_authenticated"] = True
        return RedirectResponse(url="/admin/reports", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        request,
        "admin/login.html",
        {"page_title": "Admin Login", "error": "账号或密码错误", "nav_mode": "admin_auth"},
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@router.get("/admin/reports", response_class=HTMLResponse)
def admin_reports_page(request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    reports = list_all_reports(db)
    return render_template(
        request,
        "admin/report_list.html",
        {"page_title": "Reports", "reports": reports, "nav_mode": "admin"},
        db=db,
    )


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users_page(request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    users = list_all_users(db)
    return render_template(
        request,
        "admin/user_list.html",
        {"page_title": "Users", "users": users, "nav_mode": "admin"},
        db=db,
    )


@router.get("/admin/reports/new", response_class=HTMLResponse)
def new_report_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(
        request,
        "admin/new_report.html",
        {"page_title": "New Report", "today": date.today().isoformat(), "nav_mode": "admin"},
    )


@router.get("/admin/reports/{report_id}/edit", response_class=HTMLResponse)
def edit_report_page(report_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="研报不存在")
    return render_template(
        request,
        "admin/edit_report.html",
        {
            "page_title": "Edit Report",
            "report": report,
            "nav_mode": "admin",
        },
        db=db,
    )


@router.post("/admin/reports/new")
def new_report(
    request: Request,
    title: str = Form(...),
    summary: str = Form(...),
    category: str = Form(...),
    publish_date: date = Form(...),
    status_value: str = Form(..., alias="status"),
    pdf_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    pdf_filename = pdf_file.filename or ""
    if (
        pdf_file.content_type not in {"application/pdf", "application/x-pdf", "application/octet-stream"}
        and not pdf_filename.lower().endswith(".pdf")
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请上传 PDF 文件")
    if status_value not in {"draft", "published"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的研报状态")

    payload = ReportCreate(
        title=title,
        slug=slugify_title(title),
        summary=summary,
        category=category,
        publish_date=publish_date,
        pdf_url=store_uploaded_pdf(pdf_file),
        status=status_value,
    )
    report = create_report(db, payload)
    if report.status == "published":
        return RedirectResponse(url=f"/reports/{report.slug}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin/reports", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/reports/{report_id}/edit")
def edit_report(
    report_id: int,
    request: Request,
    title: str = Form(...),
    summary: str = Form(...),
    category: str = Form(...),
    publish_date: date = Form(...),
    status_value: str = Form(..., alias="status"),
    pdf_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    if status_value not in {"draft", "published"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的研报状态")

    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="研报不存在")

    new_pdf_url = None
    if pdf_file and (pdf_file.filename or "").strip():
        pdf_filename = pdf_file.filename or ""
        if (
            pdf_file.content_type not in {"application/pdf", "application/x-pdf", "application/octet-stream"}
            and not pdf_filename.lower().endswith(".pdf")
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请上传 PDF 文件")
        new_pdf_url = store_uploaded_pdf(pdf_file)

    updated_report = update_report(
        db,
        report,
        title=title,
        summary=summary,
        category=category,
        publish_date=publish_date,
        status_value=status_value,
        pdf_url=new_pdf_url,
    )
    if updated_report.status == "published":
        return RedirectResponse(url=f"/reports/{updated_report.slug}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin/reports", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/users/{user_id}/status")
def admin_update_user_status(
    user_id: int,
    request: Request,
    is_active: str = Form(...),
    level: str = Form(...),
    db: Session = Depends(get_db),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    if is_active not in {"true", "false"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的用户状态")
    if level not in {"User", "VIP1", "VIP2", "VIP3"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的用户等级")

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    update_user_admin_fields(db, user, is_active=is_active == "true", level=level)
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/reports/{report_id}/status")
def admin_update_report_status(
    report_id: int,
    request: Request,
    status_value: str = Form(..., alias="status"),
    db: Session = Depends(get_db),
):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    if status_value not in {"draft", "published"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的研报状态")

    report = get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="研报不存在")

    update_report_status(db, report, status_value)
    return RedirectResponse(url="/admin/reports", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/logout")
def admin_logout(request: Request):
    request.session.pop("admin_authenticated", None)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
