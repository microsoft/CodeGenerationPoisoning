"""Report utils."""
# Standard Python Libraries
import csv
from datetime import datetime, timedelta
from io import StringIO
import json
import os
import os.path
import subprocess  # nosec

# Third-Party Libraries
from PyPDF2 import PdfFileReader, PdfFileWriter
from faker import Faker
from flask import render_template
from flask.templating import render_template_string

# cisagov Libraries
from api.manager import (
    CustomerManager,
    CycleManager,
    RecommendationManager,
    SendingProfileManager,
    SubscriptionManager,
)
from utils import time
from utils.emails import get_email_context, get_from_address
from utils.logging import setLogger
from utils.pdf import append_attachment
from utils.stats import get_all_customer_stats, get_cycle_stats
from utils.templates import get_indicators

logger = setLogger(__name__)

customer_manager = CustomerManager()
cycle_manager = CycleManager()
recommendation_manager = RecommendationManager()
sending_profile_manager = SendingProfileManager()
subscription_manager = SubscriptionManager()


def get_report(cycle_id: str, report_type: str, nonhuman: bool = False):
    """Get report by type and cycle."""
    cycle = cycle_manager.get(document_id=cycle_id)
    subscription = subscription_manager.get(
        document_id=cycle["subscription_id"],
        fields=[
            "_id",
            "name",
            "customer_id",
            "sending_profile_id",
            "target_domain",
            "start_date",
            "primary_contact",
            "admin_email",
            "status",
            "buffer_time_minutes",
        ],
    )
    customer = customer_manager.get(document_id=subscription["customer_id"])
    get_cycle_stats(cycle)
    previous_cycles = get_previous_cycles(cycle)
    recommendations = recommendation_manager.all()
    all_customer_stats = get_all_customer_stats()

    context = {
        "stats": cycle["nonhuman_stats"] if nonhuman else cycle["stats"],
        "cycle": cycle,
        "subscription": subscription,
        "customer": customer,
        "previous_cycles": previous_cycles,
        "recommendations": recommendations,
        "compare_svg": compare_svg,
        "percent_svg": percent_svg,
        "percent": percent,
        "preview_template": preview_template,
        "preview_from_address": preview_from_address,
        "all_customer_stats": all_customer_stats,
        "indicators": get_indicators(),
        "datetime": datetime,
        "timedelta": timedelta,
        "json": json,
        "str": str,
        "time": time,
        "getMostClickedTemplateLevel": getMostClickedTemplateLevel,
    }
    return render_template(f"reports/{report_type}.html", **context)


def get_report_pdf(
    cycle: dict,
    report_type: str,
    reporting_password: str = None,
    nonhuman: bool = False,
):
    """Get report pdf."""
    cycle_id = cycle["_id"]
    filename = f"{cycle_id}_report.pdf"
    args = [
        "node",
        "report.js",
        filename,
        cycle_id,
        report_type,
        str(nonhuman),
    ]
    subprocess.run(args)  # nosec

    filepath = f"/var/www/{filename}"
    new_filepath = f"/var/www/new-{filename}"

    if not os.path.exists(filepath):
        logger.error(f"Expected path {filepath} does not exist")
        raise Exception("Reporting Exception - Check Logs")

    writer = PdfFileWriter()
    reader = PdfFileReader(open(filepath, "rb"))
    for i in range(0, reader.getNumPages()):
        writer.addPage(reader.getPage(i))
    if reporting_password:
        writer.encrypt(reporting_password, use_128bit=True)

    if report_type == "cycle":
        # add csv pages
        _add_csv_attachments(writer=writer, cycle=cycle)

    output = open(new_filepath, "wb")
    writer.write(output)
    output.close()
    os.remove(filepath)

    return new_filepath


def _add_csv_attachments(writer: PdfFileWriter, cycle: dict):
    """Add CSV attachments to PDF."""
    csv_data = [
        _add_overall_stats_csv,
        _add_template_stats_csv,
        _add_time_stats_csv,
        _user_group_stats_csv,
    ]

    for func in csv_data:
        filename, headers, data = func(cycle=cycle)
        csv_file = StringIO()
        csv_writer = csv.DictWriter(csv_file, fieldnames=headers)
        csv_writer.writeheader()

        if isinstance(data, list):
            csv_writer.writerows(data)
        else:
            csv_writer.writerow(data)

        append_attachment(writer, filename, csv_file.getvalue().encode())
        csv_file.close()


def _add_overall_stats_csv(cycle: dict):
    """Add Top Level Stats CSV attachment to PDF."""
    stats = cycle["stats"]

    average_click_time = stats["stats"]["all"]["clicked"]["average"]
    average_click_time_string = (
        f"{average_click_time} minutes"
        if average_click_time < 60
        else f"{average_click_time / 60} hours"
    )
    data = {
        "Start Date": datetime.strftime(cycle["start_date"], "%m/%d/%Y, %H:%M:%S"),
        "End Date": datetime.strftime(cycle["end_date"], "%m/%d/%Y, %H:%M:%S"),
        "Average Click Time": average_click_time_string,
        "Low Sent": stats["stats"]["low"]["sent"]["count"],
        "Low Opened": stats["stats"]["low"]["opened"]["count"],
        "Low Clicked": stats["stats"]["low"]["clicked"]["count"],
        "Moderate Sent": stats["stats"]["moderate"]["sent"]["count"],
        "Moderate Opened": stats["stats"]["moderate"]["opened"]["count"],
        "Moderate Clicked": stats["stats"]["moderate"]["clicked"]["count"],
        "High Sent": stats["stats"]["high"]["sent"]["count"],
        "High Opened": stats["stats"]["high"]["opened"]["count"],
        "High Clicked": stats["stats"]["high"]["clicked"]["count"],
        "All Sent": stats["stats"]["all"]["sent"]["count"],
        "All Opened": stats["stats"]["all"]["opened"]["count"],
        "All Clicked": stats["stats"]["all"]["clicked"]["count"],
    }
    headers = data.keys()

    return "overall_stats.csv", headers, data


def _user_group_stats_csv(cycle: dict):
    """Add User Group Stats CSV attachment to PDF."""
    stats = cycle["stats"]

    if not stats.get("target_stats"):
        return "user_group_stats.csv", [], {}

    data = [
        {
            "Group": t["group"] if t["group"] else "not grouped",
            "All Sent": t["sent"]["count"],
            "All Opened": t["opened"]["count"],
            "All Clicked": t["clicked"]["count"],
        }
        for t in stats["target_stats"]
    ]
    headers = data[0].keys()

    return "user_group_stats.csv", headers, data


def _add_time_stats_csv(cycle: dict):
    """Add Time Stats CSV attachment to PDF."""
    stats = cycle["stats"]
    data = {
        "opened__one_minute": stats["time_stats"]["opened"]["one_minutes"]["count"],
        "opened__three_minutes": stats["time_stats"]["opened"]["three_minutes"][
            "count"
        ],
        "opened__five_minutes": stats["time_stats"]["opened"]["five_minutes"]["count"],
        "opened__fifteen_minutes": stats["time_stats"]["opened"]["fifteen_minutes"][
            "count"
        ],
        "opened__thirty_minutes": stats["time_stats"]["opened"]["thirty_minutes"][
            "count"
        ],
        "opened__sixty_minutes": stats["time_stats"]["opened"]["sixty_minutes"][
            "count"
        ],
        "opened__two_hours": stats["time_stats"]["opened"]["two_hours"]["count"],
        "opened__three_hours": stats["time_stats"]["opened"]["three_hours"]["count"],
        "opened__four_hours": stats["time_stats"]["opened"]["four_hours"]["count"],
        "opened__one_day": stats["time_stats"]["opened"]["one_day"]["count"],
        "clicked__one_minute": stats["time_stats"]["clicked"]["one_minutes"]["count"],
        "clicked__three_minutes": stats["time_stats"]["clicked"]["three_minutes"][
            "count"
        ],
        "clicked__five_minutes": stats["time_stats"]["clicked"]["five_minutes"][
            "count"
        ],
        "clicked__fifteen_minutes": stats["time_stats"]["clicked"]["fifteen_minutes"][
            "count"
        ],
        "clicked__thirty_minutes": stats["time_stats"]["clicked"]["thirty_minutes"][
            "count"
        ],
        "clicked__sixty_minutes": stats["time_stats"]["clicked"]["sixty_minutes"][
            "count"
        ],
        "clicked__two_hours": stats["time_stats"]["clicked"]["two_hours"]["count"],
        "clicked__three_hours": stats["time_stats"]["clicked"]["three_hours"]["count"],
        "clicked__four_hours": stats["time_stats"]["clicked"]["four_hours"]["count"],
        "clicked__one_day": stats["time_stats"]["clicked"]["one_day"]["count"],
    }
    headers = data.keys()

    return "time_stats.csv", headers, data


def _add_template_stats_csv(cycle: dict):
    """Add Template Stats CSV attachment to PDF."""
    stats = cycle["stats"]
    headers = [
        "sent",
        "opened",
        "clicked",
        "deception_level",
        "subject",
        "from_address",
    ]

    data = [
        {
            "sent": stat["sent"]["count"],
            "opened": stat["opened"]["count"],
            "clicked": stat["clicked"]["count"],
            "deception_level": stat["deception_level"],
            "subject": stat["template"]["subject"],
            "from_address": stat["template"]["from_address"],
        }
        for stat in stats["template_stats"]
    ]

    return "template_stats.csv", headers, data


def get_reports_sent(subscriptions):
    """Get reports sent."""
    response = {
        "status_reports_sent": 0,
        "cycle_reports_sent": 0,
        "yearly_reports_sent": 0,
    }
    for subscription in subscriptions:
        for notification in subscription.get("notification_history", []):
            if f"{notification['message_type']}s_sent" in response:
                response[f"{notification['message_type']}s_sent"] += 1
    return response


def get_customers_active():
    """Get number of customers with at least one active subscription."""
    active_subscriptions = subscription_manager.all(
        {"status": {"$in": ["queued", "running"]}}
    )
    customers_active = len(
        {subscription["customer_id"] for subscription in active_subscriptions}
    )
    return customers_active


def get_sector_industry_report():
    """Get reports on sector industries."""
    response = {
        "federal_stats": {
            "subscription_count": 0,
            "cycle_count": 0,
            "emails_sent": 0,
            "emails_clicked": 0,
            "emails_clicked_ratio": 0,
        },
        "state_stats": {
            "subscription_count": 0,
            "cycle_count": 0,
            "emails_sent": 0,
            "emails_clicked": 0,
            "emails_clicked_ratio": 0,
        },
        "local_stats": {
            "subscription_count": 0,
            "cycle_count": 0,
            "emails_sent": 0,
            "emails_clicked": 0,
            "emails_clicked_ratio": 0,
        },
        "tribal_stats": {
            "subscription_count": 0,
            "cycle_count": 0,
            "emails_sent": 0,
            "emails_clicked": 0,
            "emails_clicked_ratio": 0,
        },
        "private_stats": {
            "subscription_count": 0,
            "cycle_count": 0,
            "emails_sent": 0,
            "emails_clicked": 0,
            "emails_clicked_ratio": 0,
        },
    }
    customers = customer_manager.all(fields=["_id", "customer_type"])
    for customer in customers:
        stat = f"{customer['customer_type'].lower()}_stats"
        subscriptions = subscription_manager.all(
            params={"customer_id": customer["_id"]},
            fields=["_id"],
        )
        cycles = cycle_manager.all(
            params={"subscription_id": {"$in": [s["_id"] for s in subscriptions]}},
            fields=["_id", "stats"],
        )
        response[stat]["subscription_count"] += len(subscriptions)
        response[stat]["cycle_count"] += len(cycles)
        response[stat]["emails_sent"] = sum(
            cycle["stats"]["stats"]["all"]["sent"]["count"]
            for cycle in cycles
            if cycle.get("stats")
        )
        response[stat]["emails_clicked"] = sum(
            cycle["stats"]["stats"]["all"]["clicked"]["count"]
            for cycle in cycles
            if cycle.get("stats")
        )

        try:
            clicked_ratio = (
                response[stat]["emails_clicked"] / response[stat]["emails_sent"]
            )
        except ZeroDivisionError:
            clicked_ratio = 0

        response[stat]["emails_clicked_ratio"] = round(clicked_ratio * 100, 2)

    return response


def get_previous_cycles(current_cycle):
    """Get previous cycles for report."""
    cycles = cycle_manager.all(
        params={"subscription_id": current_cycle["subscription_id"]}
    )
    cycles = list(
        filter(
            lambda x: x["_id"] != current_cycle["_id"]
            and x["start_date"] < current_cycle["start_date"],
            cycles,
        )
    )

    # Sort timeline so most recent is first
    cycles = sorted(cycles, key=lambda x: x["start_date"], reverse=True)

    # Update stats for each cycle
    for cycle in cycles:
        get_cycle_stats(cycle)

    return cycles


def getMostClickedTemplateLevel(low_ratio, moderate_ratio, high_ratio):
    """Get Most Clicked Template Level for report."""
    levels = {
        "Low": low_ratio,
        "Moderate": moderate_ratio,
        "High": high_ratio,
    }
    return max(levels, key=levels.get)


def preview_from_address(template, subscription, customer):
    """Preview from address in a report."""
    if template.get("sending_profile_id"):
        sending_profile = sending_profile_manager.get(
            document_id=template["sending_profile_id"]
        )
    else:
        sending_profile = sending_profile_manager.get(
            document_id=subscription["sending_profile_id"]
        )
    from_address = get_from_address(sending_profile, template["from_address"])
    return preview_template(from_address, customer)


def preview_template(data, customer):
    """Preview template subject, from_address and html for reports."""
    fake = Faker()
    target = {
        "email": fake.email(),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "position": fake.job(),
    }
    context = get_email_context(customer=customer, target=target)
    return render_template_string(data, **context)


def percent(ratio):
    """Get percentage from ratio."""
    return round(ratio * 100, 1)


def compare_svg(
    current,
    previous,
    up_color="default",
    down_color="default",
    neutral_color="default",
):
    """Compare current and previous value and return an SVG based on the result."""
    colors = {
        "good": "#5e9732",
        "bad": "#c41230",
        "neutral": "#fdc010",
        "default": "#006c9c",
    }
    up_svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 22" style="width: 0.25in">
            <g id="Layer_2" data-name="Layer 2">
                <g id="Layer_1-2" data-name="Layer 1">
                <polygon
                    style="
                        fill: {colors.get(up_color)};
                        stroke: {colors.get(up_color)};
                        stroke-linecap: round;
                        stroke-linejoin: round;
                        stroke-width: 2px;
                    "
                    points="31 14.78 23.5 7.89 16 1 8.5 7.89 1 14.78 6.66 14.78 6.66 21 10.32 21 22.04 21 25.42 21 25.42 14.78 31 14.78"
                />
                </g>
            </g>
        </svg>
    """

    down_svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 22" style="width: 0.25in; height: 0.25in">
            <g id="Layer_2" data-name="Layer 2">
                <g id="Layer_1-2" data-name="Layer 1">
                <polygon
                    style="
                        fill: {colors.get(down_color)};
                        stroke: {colors.get(down_color)};
                        stroke-linecap: round;
                        stroke-linejoin: round;
                        stroke-width: 2px;
                        width: .25in;
                    "
                    points="1 7.22 8.5 14.11 16 21 23.5 14.11 31 7.22 25.34 7.22 25.34 1 21.68 1 9.96 1 6.58 1 6.58 7.22 1 7.22"
                />
                </g>
            </g>
        </svg>
    """

    neutral_svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 22" style="width: 0.25in; height: 0.25in;">
            <g id="Layer_2" data-name="Layer 2">
                <g id="Layer_1-2" data-name="Layer 1">
                <polygon
                    style="
                        fill: {colors.get(neutral_color)};
                        stroke: {colors.get(neutral_color)};
                        stroke-linecap: round;
                        stroke-linejoin: round;
                        stroke-width: 2px;
                    "
                    points="31 14.78 23.5 7.89 16 1 8.5 7.89 1 14.78 6.66 14.78 6.66 21 10.32 21 22.04 21 25.42 21 25.42 14.78 31 14.78"
                    transform="rotate(90, 17, 11)"
                />
                </g>
            </g>
        </svg>
    """

    if not previous:
        return neutral_svg
    if current > previous:
        return up_svg
    if current < previous:
        return down_svg
    if current == previous:
        return neutral_svg


def percent_change(current_percent, previous_percent):
    """Get percent change."""
    try:
        return round(
            (current_percent - previous_percent) / abs(previous_percent) * 100, 2
        )
    except ZeroDivisionError:
        return 0


def percent_svg(current_percent, previous_percent):
    """Get an increase/decrease svg with a percentage."""
    change = percent_change(current_percent, previous_percent)
    up_svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 22" style="width: 50px; height: 40px">
            <g id="Layer_2" data-name="Layer 2">
                <g id="Layer_1-2" data-name="Layer 1">
                <polygon
                    style="
                        fill: #C41230;
                        stroke: #C41230;
                        stroke-linecap: round;
                        stroke-linejoin: round;
                        stroke-width: 2px;
                    "
                    points="31 14.78 23.5 7.89 16 1 8.5 7.89 1 14.78 6.66 14.78 6.66 21 10.32 21 22.04 21 25.42 21 25.42 14.78 31 14.78"
                />
                </g>
            </g>
        </svg>
        <p style="color: #C41230; margin: 0 0 0">+{change}%</p>
    """

    down_svg = f"""
        <p style="color: #5E9732; margin: 0 0 0">{change}%</p>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 22" style="width: 50px; height: 40px">
            <g id="Layer_2" data-name="Layer 2">
                <g id="Layer_1-2" data-name="Layer 1">
                <polygon
                    style="
                        fill: #5E9732;
                        stroke: #5E9732;
                        stroke-linecap: round;
                        stroke-linejoin: round;
                        stroke-width: 2px;
                        width: .25in;
                    "
                    points="1 7.22 8.5 14.11 16 21 23.5 14.11 31 7.22 25.34 7.22 25.34 1 21.68 1 9.96 1 6.58 1 6.58 7.22 1 7.22"
                />
                </g>
            </g>
        </svg>
    """

    neutral_svg = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 22" style="width: 50px; height: 60px">
            <g id="Layer_2" data-name="Layer 2">
                <g id="Layer_1-2" data-name="Layer 1">
                <polygon
                    style="
                        fill: #006c9c;
                        stroke: #006c9c;
                        stroke-linecap: round;
                        stroke-linejoin: round;
                        stroke-width: 2px;
                    "
                    points="31 14.78 23.5 7.89 16 1 8.5 7.89 1 14.78 6.66 14.78 6.66 21 10.32 21 22.04 21 25.42 21 25.42 14.78 31 14.78"
                    transform="rotate(90, 17, 11)"
                />
                </g>
            </g>
        </svg>
    """

    if current_percent > previous_percent:
        return up_svg
    if current_percent < previous_percent:
        return down_svg
    if current_percent == previous_percent:
        return neutral_svg
