import csv
import io
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.restaurant_order import RestaurantOrder
from app.models.restaurant_profile import RestaurantProfile
from app.models.staff_user import StaffUser

router = APIRouter(prefix="/analytics", tags=["Business Analytics"])

MANAGEMENT = require_roles("OWNER", "MANAGER", "ASSISTANT_MANAGER")


def money(value):
    return float(value or 0)


def get_report_data(db: Session, start_date: date, end_date: date):
    if end_date < start_date:
        raise HTTPException(400, "End date must be on or after start date.")

    if (end_date - start_date).days > 3653:
        raise HTTPException(400, "Maximum reporting range is 10 years.")

    start = datetime.combine(start_date, time.min, tzinfo=UTC)
    end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)

    orders = (
        db.scalars(
            select(RestaurantOrder)
            .options(joinedload(RestaurantOrder.table))
            .where(
                RestaurantOrder.created_at >= start,
                RestaurantOrder.created_at < end_exclusive,
            )
            .order_by(RestaurantOrder.created_at.asc())
        )
        .unique()
        .all()
    )

    valid_orders = [o for o in orders if o.status != "CANCELLED"]
    paid = [o for o in valid_orders if o.payment_status == "PAID"]
    refunded = [o for o in valid_orders if o.payment_status == "REFUNDED"]
    pending = [o for o in valid_orders if o.payment_status in {"PENDING", "UNPAID"}]
    failed = [o for o in valid_orders if o.payment_status == "FAILED"]

    gross = sum((o.total_amount for o in valid_orders), Decimal("0.00"))
    received = sum((o.total_amount for o in paid), Decimal("0.00"))
    refunded_amount = sum((o.total_amount for o in refunded), Decimal("0.00"))
    outstanding = sum((o.total_amount for o in pending), Decimal("0.00"))
    failed_amount = sum((o.total_amount for o in failed), Decimal("0.00"))

    payment_methods = defaultdict(
        lambda: {
            "orders": 0,
            "paid": 0.0,
            "pending": 0.0,
            "failed": 0.0,
            "refunded": 0.0,
        }
    )
    daily = defaultdict(lambda: {"orders": 0, "sales": 0.0, "received": 0.0})

    for order in valid_orders:
        method = order.payment_method or "Not selected"
        entry = payment_methods[method]
        entry["orders"] += 1
        amount = money(order.total_amount)

        if order.payment_status == "PAID":
            entry["paid"] += amount
        elif order.payment_status in {"PENDING", "UNPAID"}:
            entry["pending"] += amount
        elif order.payment_status == "FAILED":
            entry["failed"] += amount
        elif order.payment_status == "REFUNDED":
            entry["refunded"] += amount

        day = order.created_at.date().isoformat()
        daily[day]["orders"] += 1
        daily[day]["sales"] += amount
        if order.payment_status == "PAID":
            daily[day]["received"] += amount

    previous_days = (end_date - start_date).days + 1
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=previous_days - 1)

    previous_start_dt = datetime.combine(previous_start, time.min, tzinfo=UTC)
    previous_end_dt = datetime.combine(
        previous_end + timedelta(days=1), time.min, tzinfo=UTC
    )

    previous_orders = db.scalars(
        select(RestaurantOrder).where(
            RestaurantOrder.created_at >= previous_start_dt,
            RestaurantOrder.created_at < previous_end_dt,
            RestaurantOrder.status != "CANCELLED",
        )
    ).all()

    previous_sales = sum((o.total_amount for o in previous_orders), Decimal("0.00"))
    previous_received = sum(
        (o.total_amount for o in previous_orders if o.payment_status == "PAID"),
        Decimal("0.00"),
    )

    profile = db.scalar(
        select(RestaurantProfile).order_by(RestaurantProfile.id).limit(1)
    )

    rows = []
    for order in valid_orders:
        rows.append(
            {
                "order_number": order.order_number,
                "table_number": order.table.table_number if order.table else "Unknown",
                "created_at": order.created_at.isoformat(),
                "total": money(order.total_amount),
                "payment_method": order.payment_method or "Not selected",
                "payment_provider": order.payment_provider or "",
                "payment_status": order.payment_status,
                "transaction_reference": order.transaction_reference or "",
                "order_status": order.status,
            }
        )

    return {
        "restaurant_name": (
            profile.restaurant_name if profile else "Restaurant profile not configured"
        ),
        "currency": profile.currency if profile else "PKR",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": {
            "orders": len(valid_orders),
            "gross_order_value": money(gross),
            "confirmed_revenue": money(received),
            "outstanding_amount": money(outstanding),
            "failed_amount": money(failed_amount),
            "refunded_amount": money(refunded_amount),
            "average_order_value": (
                money(gross) / len(valid_orders) if valid_orders else 0
            ),
            "paid_orders": len(paid),
            "pending_orders": len(pending),
            "failed_orders": len(failed),
            "refunded_orders": len(refunded),
            "cancelled_orders": len(orders) - len(valid_orders),
        },
        "comparison": {
            "previous_start": previous_start.isoformat(),
            "previous_end": previous_end.isoformat(),
            "previous_orders": len(previous_orders),
            "previous_gross_order_value": money(previous_sales),
            "previous_confirmed_revenue": money(previous_received),
            "gross_change_percent": (
                ((money(gross) - money(previous_sales)) / money(previous_sales)) * 100
                if previous_sales
                else None
            ),
            "revenue_change_percent": (
                (
                    (money(received) - money(previous_received))
                    / money(previous_received)
                )
                * 100
                if previous_received
                else None
            ),
        },
        "payment_methods": dict(payment_methods),
        "daily_sales": [{"date": key, **value} for key, value in sorted(daily.items())],
        "orders": rows,
    }


@router.get("/report")
def analytics_report(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT),
):
    return get_report_data(db, start_date, end_date)


@router.get("/export.csv")
def export_csv(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT),
):
    report = get_report_data(db, start_date, end_date)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Order Number",
            "Table Number",
            "Date/Time",
            "Order Total",
            "Payment Method",
            "Payment Provider",
            "Payment Status",
            "Transaction Reference",
            "Order Status",
        ]
    )

    for order in report["orders"]:
        writer.writerow(
            [
                order["order_number"],
                order["table_number"],
                order["created_at"],
                order["total"],
                order["payment_method"],
                order["payment_provider"],
                order["payment_status"],
                order["transaction_reference"],
                order["order_status"],
            ]
        )

    output.seek(0)
    filename = f"restromind-orders-{start_date}-{end_date}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def make_bar_chart(labels, values, title):
    drawing = Drawing(480, 190)
    drawing.add(
        String(10, 170, title, fontSize=11, fillColor=colors.HexColor("#263a2d"))
    )
    chart = VerticalBarChart()
    chart.x = 45
    chart.y = 30
    chart.width = 410
    chart.height = 120
    chart.data = [values or [0]]
    chart.categoryAxis.categoryNames = labels or ["No data"]
    chart.categoryAxis.labels.angle = 25
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = colors.HexColor("#557a5b")
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(values or [1]) * 1.2 or 1
    drawing.add(chart)
    return drawing


def make_payment_chart(payment_methods):
    drawing = Drawing(480, 220)
    pie = Pie()
    pie.x = 115
    pie.y = 10
    pie.width = 180
    pie.height = 180
    labels = list(payment_methods)
    values = [payment_methods[key]["paid"] for key in labels]
    pie.data = values or [1]
    pie.labels = labels if values and sum(values) else ["No confirmed payments"]
    pie.slices.strokeWidth = 0.5
    pie.slices[0].fillColor = colors.HexColor("#557a5b")
    drawing.add(pie)
    drawing.add(String(10, 205, "Confirmed revenue by payment method", fontSize=11))
    return drawing


@router.get("/export.pdf")
def export_pdf(
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT),
):
    report = get_report_data(db, start_date, end_date)
    summary = report["summary"]
    currency = report["currency"]
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#263a2d"),
            fontSize=21,
        )
    )

    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=13 * mm,
    )
    story = [
        Paragraph("RESTAURANT BUSINESS REPORT", styles["ReportTitle"]),
        Paragraph(report["restaurant_name"], styles["Heading2"]),
        Paragraph(
            f"Reporting period: {start_date:%d %b %Y} – {end_date:%d %b %Y}",
            styles["Normal"],
        ),
        Spacer(1, 8 * mm),
    ]

    summary_rows = [
        ["Metric", "Value", "Metric", "Value"],
        [
            "Orders",
            str(summary["orders"]),
            "Average order value",
            f"{currency} {summary['average_order_value']:,.2f}",
        ],
        [
            "Gross order value",
            f"{currency} {summary['gross_order_value']:,.2f}",
            "Confirmed revenue",
            f"{currency} {summary['confirmed_revenue']:,.2f}",
        ],
        [
            "Outstanding",
            f"{currency} {summary['outstanding_amount']:,.2f}",
            "Refunded",
            f"{currency} {summary['refunded_amount']:,.2f}",
        ],
        [
            "Failed amount",
            f"{currency} {summary['failed_amount']:,.2f}",
            "Cancelled orders",
            str(summary["cancelled_orders"]),
        ],
    ]
    story.append(Table(summary_rows, colWidths=[45 * mm, 55 * mm, 45 * mm, 55 * mm]))
    story.append(Spacer(1, 7 * mm))

    comparison = report["comparison"]
    change = comparison["gross_change_percent"]
    change_text = "Not available" if change is None else f"{change:+.1f}%"
    story.append(Paragraph("Period comparison", styles["Heading2"]))
    story.append(
        Paragraph(
            f"Previous period ({comparison['previous_start']} to "
            f"{comparison['previous_end']}): "
            f"{comparison['previous_orders']} orders, "
            f"{currency} {comparison['previous_gross_order_value']:,.2f} gross value. "
            f"Gross value change: {change_text}.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 4 * mm))

    trend = report["daily_sales"]
    if len(trend) > 20:
        step = max(1, len(trend) // 20)
        trend = trend[::step]
    story.append(
        make_bar_chart(
            [entry["date"][5:] for entry in trend],
            [entry["sales"] for entry in trend],
            "Daily gross order value",
        )
    )
    story.append(make_payment_chart(report["payment_methods"]))
    story.append(PageBreak())

    story.append(Paragraph("Payment method breakdown", styles["Heading2"]))
    payment_rows = [["Method", "Orders", "Confirmed", "Pending", "Failed", "Refunded"]]
    for method, values in report["payment_methods"].items():
        payment_rows.append(
            [
                method,
                str(values["orders"]),
                f"{currency} {values['paid']:,.2f}",
                f"{currency} {values['pending']:,.2f}",
                f"{currency} {values['failed']:,.2f}",
                f"{currency} {values['refunded']:,.2f}",
            ]
        )
    if len(payment_rows) == 1:
        payment_rows.append(["No payment records", "0", "-", "-", "-", "-"])
    story.append(Table(payment_rows, repeatRows=1))
    story.append(Spacer(1, 7 * mm))

    story.append(Paragraph("Order details", styles["Heading2"]))
    order_rows = [
        [
            "Order",
            "Table",
            "Date / Time",
            "Total",
            "Method",
            "Payment",
            "Transaction reference",
        ]
    ]
    for order in report["orders"]:
        order_rows.append(
            [
                order["order_number"],
                order["table_number"],
                order["created_at"][:16].replace("T", " "),
                f"{currency} {order['total']:,.2f}",
                order["payment_method"],
                order["payment_status"],
                order["transaction_reference"] or "Not recorded",
            ]
        )
    if len(order_rows) == 1:
        order_rows.append(["No orders in selected period", "", "", "", "", "", ""])
    story.append(
        Table(
            order_rows,
            repeatRows=1,
            colWidths=[28 * mm, 18 * mm, 35 * mm, 28 * mm, 30 * mm, 24 * mm, 48 * mm],
        )
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(14 * mm, 7 * mm, "RestroMind Business Analytics")
        canvas.drawRightString(landscape(A4)[0] - 14 * mm, 7 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    output.seek(0)
    filename = f"restromind-report-{start_date}-{end_date}.pdf"
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class RestaurantProfileUpdate(BaseModel):
    restaurant_name: str = Field(min_length=2, max_length=150)
    currency: str = Field(default="PKR", min_length=3, max_length=10)


@router.get("/profile")
def get_restaurant_profile(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT),
):
    profile = db.get(RestaurantProfile, 1)
    return {
        "restaurant_name": (profile.restaurant_name if profile else ""),
        "currency": profile.currency if profile else "PKR",
    }


@router.put("/profile")
def update_restaurant_profile(
    payload: RestaurantProfileUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(MANAGEMENT),
):
    profile = db.get(RestaurantProfile, 1)

    if profile is None:
        profile = RestaurantProfile(
            id=1,
            restaurant_name=payload.restaurant_name.strip(),
            currency=payload.currency.strip().upper(),
        )
        db.add(profile)
    else:
        profile.restaurant_name = payload.restaurant_name.strip()
        profile.currency = payload.currency.strip().upper()

    db.commit()
    db.refresh(profile)

    return {
        "restaurant_name": profile.restaurant_name,
        "currency": profile.currency,
    }
