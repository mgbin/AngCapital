from datetime import date
from typing import Optional

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models import AdminUser, FrontendUser, ResearchReport
from app.schemas import AdminUserCreate, FrontendUserCreate, ReportCreate


def list_reports(db: Session, keyword: str = "") -> list[ResearchReport]:
    stmt = select(ResearchReport).where(ResearchReport.status == "published")
    cleaned_keyword = keyword.strip()
    if cleaned_keyword:
        like_pattern = f"%{cleaned_keyword}%"
        stmt = stmt.where(
            or_(
                ResearchReport.title.like(like_pattern),
                ResearchReport.summary.like(like_pattern),
            )
        )
    stmt = stmt.order_by(desc(ResearchReport.publish_date), desc(ResearchReport.id))
    return list(db.scalars(stmt).all())


def list_all_reports(db: Session) -> list[ResearchReport]:
    stmt = select(ResearchReport).order_by(desc(ResearchReport.created_at), desc(ResearchReport.id))
    return list(db.scalars(stmt).all())


def featured_report(db: Session) -> Optional[ResearchReport]:
    stmt = (
        select(ResearchReport)
        .where(ResearchReport.status == "published")
        .order_by(desc(ResearchReport.publish_date), desc(ResearchReport.id))
    )
    return db.scalars(stmt).first()


def get_report_by_slug(db: Session, slug: str) -> Optional[ResearchReport]:
    stmt = select(ResearchReport).where(
        ResearchReport.slug == slug,
        ResearchReport.status == "published",
    )
    return db.scalars(stmt).first()


def create_report(db: Session, payload: ReportCreate) -> ResearchReport:
    report = ResearchReport(**payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report_by_id(db: Session, report_id: int) -> Optional[ResearchReport]:
    stmt = select(ResearchReport).where(ResearchReport.id == report_id)
    return db.scalars(stmt).first()


def update_report_status(db: Session, report: ResearchReport, status_value: str) -> ResearchReport:
    report.status = status_value
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def update_report(
    db: Session,
    report: ResearchReport,
    *,
    title: str,
    summary: str,
    category: str,
    publish_date: date,
    status_value: str,
    pdf_url: Optional[str] = None,
) -> ResearchReport:
    report.title = title
    report.summary = summary
    report.category = category
    report.publish_date = publish_date
    report.status = status_value
    if pdf_url:
        report.pdf_url = pdf_url
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_user_by_email(db: Session, email: str) -> Optional[FrontendUser]:
    stmt = select(FrontendUser).where(FrontendUser.email == email)
    return db.scalars(stmt).first()


def get_user_by_username(db: Session, username: str) -> Optional[FrontendUser]:
    stmt = select(FrontendUser).where(FrontendUser.username == username)
    return db.scalars(stmt).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[FrontendUser]:
    stmt = select(FrontendUser).where(FrontendUser.id == user_id)
    return db.scalars(stmt).first()


def list_all_users(db: Session) -> list[FrontendUser]:
    stmt = select(FrontendUser).order_by(desc(FrontendUser.created_at), desc(FrontendUser.id))
    return list(db.scalars(stmt).all())


def update_user_active_status(db: Session, user: FrontendUser, is_active: bool) -> FrontendUser:
    user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_admin_fields(
    db: Session,
    user: FrontendUser,
    *,
    is_active: bool,
    level: str,
) -> FrontendUser:
    user.is_active = is_active
    user.level = level
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_frontend_user(db: Session, payload: FrontendUserCreate) -> FrontendUser:
    user = FrontendUser(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_all_admin_users(db: Session) -> list[AdminUser]:
    stmt = select(AdminUser).order_by(desc(AdminUser.created_at), desc(AdminUser.id))
    return list(db.scalars(stmt).all())


def get_admin_user_by_id(db: Session, admin_user_id: int) -> Optional[AdminUser]:
    stmt = select(AdminUser).where(AdminUser.id == admin_user_id)
    return db.scalars(stmt).first()


def get_admin_user_by_username(db: Session, username: str) -> Optional[AdminUser]:
    stmt = select(AdminUser).where(AdminUser.username == username)
    return db.scalars(stmt).first()


def create_admin_user(db: Session, payload: AdminUserCreate) -> AdminUser:
    admin_user = AdminUser(**payload.model_dump())
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user


def update_admin_user_password(db: Session, admin_user: AdminUser, password_hash: str) -> AdminUser:
    admin_user.password_hash = password_hash
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user


def seed_reports(db: Session) -> None:
    if list_reports(db):
        return

    samples = [
        ReportCreate(
            title="China AI Infrastructure Outlook 2026",
            slug="china-ai-infrastructure-outlook-2026",
            summary="从算力资本开支、IDC 升级与服务器链条三个维度，梳理 AI 基建投资的中期机会。",
            category="AI Strategy",
            publish_date=date(2026, 4, 10),
            pdf_url="https://example.com/reports/china-ai-infrastructure-outlook-2026.pdf",
            status="published",
        ),
        ReportCreate(
            title="Global Liquidity Watch: Q2 Playbook",
            slug="global-liquidity-watch-q2-playbook",
            summary="围绕美元流动性、利率预期与风险资产风格切换，提出二季度配置框架。",
            category="Macro",
            publish_date=date(2026, 4, 5),
            pdf_url="https://example.com/reports/global-liquidity-watch-q2-playbook.pdf",
            status="published",
        ),
    ]

    for report in samples:
        create_report(db, report)
