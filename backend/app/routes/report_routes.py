from ..models.report import RequestData, UserReport
from ..db import db
from fastapi import APIRouter, HTTPException, Response
from jose import jwt
from dotenv import load_dotenv

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER

import html
import csv
import httpx
import io
import re
import os

HIBP_PASSWORD_URL = "https://api.pwnedpasswords.com/range/"
HIBP_ALL_BREACHES_URL = "https://haveibeenpwned.com/api/v3/breaches"
HIBP_LATEST_BREACHES_URL = "https://haveibeenpwned.com/api/v3/latestbreach"

# Load .env file
load_dotenv()

# Access the API key from the environment
API_KEY = os.getenv('API_KEY')

router = APIRouter()

@router.post("/reports")
async def generate_report(data: RequestData):
    if data.reportType not in {"detailed", "user"}:
        raise HTTPException(status_code=400, detail="Invalid report type")
    else:
        if data.reportType == "detailed":
            report = await generate_detailed_report(data)

            if data.reportFormat == "json":
                return report
            elif data.reportFormat == "pdf":
                return await generate_pdf(data, report)
            else:
                return await generate_csv(data, report)
        else:
            report = await generate_report_on_auth_user(data)

            if data.reportFormat == "json":
                return report
            elif data.reportFormat == "pdf":
                return await generate_pdf(data, report)
            else:
                return await generate_csv(data, report)

# -------------------------- Helper functions --------------------------
"""
Generate report on the user's account.

"""
async def generate_report_on_auth_user(data: RequestData):
    # Retrieves the email of the user
    user_email = jwt.decode(data.token, key=None, algorithms=["HS256"], options={"verify_signature": False}).get("sub")

    # Checks the email in the db before using the HIBP_API
    user_data = await db.users.find_one({"email": user_email})

    # Return the local data breach in the db for faster responses
    if "breaches" in user_data:
        return user_data['breaches']
    else:
        headers = {"User-Agent": "Spearow", "hibp-api-key": API_KEY}

        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{user_email}", headers=headers)

            if response.status_code == 200:
                user_report = UserReport(
                    Name=user_data['name'],
                    Email=user_email,
                    Report=response.json()
                )

                # link the exposed data to an existing or new user breaches our the db
                await db.users.find_one_and_update(
                    {"email": user_email},
                    {"$set": {"breaches": user_report.model_dump()}})

                return user_report.model_dump_json()
            elif response.status_code == 404:
                user_report = UserReport(
                    Name=user_data['name'],
                    Email=user_email,
                    Report="Email address not found in any breaches."
                )

                # link the exposed data to an existing or new user breaches our the db
                await db.users.find_one_and_update(
                    {"email": user_email},
                    {"$set": {"breaches": user_report.model_dump()}})

                return user_report.model_dump()
            else:
                response.raise_for_status()

"""
Generate detailed report on data breaches.

"""
async def generate_detailed_report(data: RequestData):
    if data.reportCategory == "allbreaches":
        # Retrieves all the collection names in the db
        collection_names = await db.list_collection_names()

        if "breaches" in collection_names:
            elements = db['breaches'].find({})
            breached_data = []

            async for element in elements:
                # Removes the object id
                element.pop('_id', None)
                breached_data.append(element)
            return breached_data
        else:
            headers = {"User-Agent": "spearow", "hibp-api-key": API_KEY}

            async with httpx.AsyncClient() as client:
                response = await client.get(HIBP_ALL_BREACHES_URL, headers=headers)

                if response.status_code == 200:
                    # Create and link all breaches to the db
                    await db['breaches'].insert_many(response.json())
                    return response.json()
                else:
                    response.raise_for_status()
    elif data.reportCategory == "latestBreaches":
        headers = {"User-Agent": "spearow", "hibp-api-key": API_KEY}

        async with httpx.AsyncClient() as client:
            response = await client.get(HIBP_LATEST_BREACHES_URL, headers=headers)

            if response.status_code == 200:
                # link latest breaches to the db
                await db['breaches'].insert_one(response.json())
                return response.json()
            else:
                 response.raise_for_status()
    else:
        # Regular expression for a valid domain name
        pattern = r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.[A-Za-z]{2,6}$'

        if re.match(pattern, data.reportCategory) is None:
            breached_site = await db['breaches'].find_one({"Name": data.reportCategory})

            # checks the site in the db
            if breached_site:
                # Removes the object id
                breached_site.pop('_id', None)
                return breached_site
            else:
                headers = {"User-Agent": "spearow", "hibp-api-key": API_KEY}

                async with httpx.AsyncClient() as client:
                    response = await client.get(f"https://haveibeenpwned.com/api/v3/breach/{data.reportCategory}", headers=headers)

                    if response.status_code == 200:
                        # link new breached site to the db
                        await db['breaches'].insert_one(response.json())
                        return response.json()
                    elif response.status_code == 404:
                        return "Site not found"
                    else:
                        response.raise_for_status()
        else:
            return "Invalid site name"

"""
Suggest mechanisms for better security of the user's account.

"""
async def suggest_mechanisms():
    return None

"""
Request reset of account.

"""
async def request_reset_of_account():
    return None


"""
Generates pdf

"""
async def generate_pdf(report_data: RequestData, json_data):
    content = io.BytesIO()
    doc = SimpleDocTemplate(
        content,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    elements = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Centered", alignment=TA_CENTER))

    # Add the report title
    elements.append(Paragraph("<u>User Report:</u>", styles["Heading1"]))
    elements.append(Spacer(1, 0.2 * inch))

    # If it's a user report, add name, email, and report generated date
    if isinstance(json_data, dict) and "Name" in json_data and "Email" in json_data:
        elements.append(
            Paragraph(f"<b>Name:</b> {json_data['Name']}", styles["Normal"])
        )
        elements.append(
            Paragraph(f"<b>Email:</b> {json_data['Email']}", styles["Normal"])
        )
        elements.append(
            Paragraph(
                f"<b>ReportGeneratedAt:</b> {json_data.get('ReportGeneratedAt', 'N/A')}",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 0.2 * inch))

        # Check if the report data contains breaches
        if "Report" in json_data:
            if isinstance(json_data["Report"], list) and len(json_data["Report"]) > 0:
                elements.append(Paragraph("<b>Breaches:</b>", styles["Heading3"]))
                # Process each breach in the list
                await process_data(
                    {"Breaches": json_data["Report"]}, 4, elements, styles
                )
            else:
                # If no breaches found, display the message
                elements.append(
                    Paragraph(f"<b>Report:</b> {json_data['Report']}", styles["Normal"])
                )
    else:
        # If it's not a detailed report, just display the JSON data
        elements.append(Paragraph(str(json_data), styles["Normal"]))

    doc.build(elements)
    content.seek(0)

    return Response(content=content.getvalue(), media_type="application/pdf")


async def process_data(data, level, elements, styles):
    for key, value in data.items():
        if isinstance(value, dict):
            elements.append(Paragraph(f"<b>{key}:</b>", styles[f"Heading{level}"]))
            await process_data(value, level + 1, elements, styles)
        elif isinstance(value, list):
            elements.append(Paragraph(f"<b>{key}:</b>", styles[f"Heading{level}"]))
            for item in value:
                if isinstance(item, dict):
                    await process_data(item, level + 1, elements, styles)
                else:
                    elements.append(Paragraph(f"- {item}", styles["Normal"]))
        else:
            elements.append(
                Paragraph(f"<b>{key}:</b> {html.escape(str(value))}", styles["Normal"])
            )

        elements.append(Spacer(1, 0.2 * inch))  # Add spacing between elements


"""
Generate csv

"""
async def generate_csv(report_data: RequestData, json_data):
    if report_data.reportType == "user":
        fieldnames = None

        if isinstance(json_data, dict):
            fieldnames = list(json_data.keys())

        content = io.StringIO()
        writer = csv.DictWriter(content, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        row_data = {}
        for name in fieldnames:
           row_data[name] = json_data[name]

        writer.writerow(row_data)
        csv_content = content.getvalue()
        content.close()

        return Response(
            content=csv_content,
            media_type="text/csv"
        )
    else:
        fieldnames = None

        if all(isinstance(data, dict) for data in json_data):
            fieldnames = list(json_data[0].keys())
        elif isinstance(json_data, dict):
            fieldnames = list(json_data.keys())

        content = io.StringIO()
        writer = csv.DictWriter(content, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        if all(isinstance(data, dict) for data in json_data):
            for items in json_data:
                row_data = {}
                for name in fieldnames:
                    row_data[name] = items[name]

                writer.writerow(row_data)
                writer.writerows([])
        elif isinstance(json_data, dict):
            row_data = {}
            for name in fieldnames:
                row_data[name] = json_data[name]
            writer.writerow(row_data)

        csv_content = content.getvalue()
        content.close()

        return Response(
            content=csv_content,
            media_type="text/csv"
        )
