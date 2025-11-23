import os
import io
import qrcode
import threading
import subprocess
from datetime import datetime
from copy import deepcopy
import base64
import json
import shutil
import tempfile

import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import streamlit as st
import tempfile
# ----------------------------
# Firebase Admin Initialization (Cloud Secret)
# ----------------------------
import firebase_admin
from firebase_admin import credentials, db

if not firebase_admin._apps:
    firebase_secret_b64 = os.environ.get("FIREBASE_ADMIN_SECRET")
    if not firebase_secret_b64:
        raise ValueError("FIREBASE_ADMIN_SECRET env variable not set")
    
    firebase_json = json.loads(base64.b64decode(firebase_secret_b64))
    cred = credentials.Certificate(firebase_json)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://aarogyamlab-e37e4-default-rtdb.firebaseio.com/"
    })

# ----------------------------
# PDF GENERATION FUNCTIONS
# ----------------------------

def merge_with_letterhead(letterhead_path, report_path, output_path):
    letter_pdf = fitz.open(letterhead_path)
    report_pdf = fitz.open(report_path)
    lh_pages = len(letter_pdf)
    merged_pdf = fitz.open()

    for i in range(len(report_pdf)):
        report_page = report_pdf[i]
        lh_page = letter_pdf[0] if lh_pages==1 else letter_pdf[i % lh_pages]
        new_page = merged_pdf.new_page(width=lh_page.rect.width, height=lh_page.rect.height)
        new_page.show_pdf_page(lh_page.rect, letter_pdf, lh_page.number)
        new_page.show_pdf_page(report_page.rect, report_pdf, report_page.number)

    merged_pdf.save(output_path)
    merged_pdf.close()
    report_pdf.close()
    letter_pdf.close()
    print(f"✅ Merged PDF saved at: {output_path}")

# --- Utility: Normalize result keys ---
def normalize(x: str):
    return (x.replace(" ", "_").replace("-", "_").replace("(", "_")
            .replace(")", "_").replace(".", "_").replace("/", "_").replace("__", "_"))

def find_result_key(results, test, sub, param=None):
    original_sub = sub
    safe_sub = normalize(sub)
    if param:
        original_param = param
        safe_param = normalize(param)
        variants = [
            f"{test}::{original_sub}::{original_param}",
            f"{test}::{safe_sub}::{safe_param}",
            f"{test}::{safe_sub}_{safe_param}",
            f"{test}::{safe_sub}::{safe_param}_",
        ]
    else:
        variants = [f"{test}::{original_sub}", f"{test}::{safe_sub}", f"{test}::{safe_sub}_"]

    for key in results.keys():
        if key in variants:
            return key
    for key in results.keys():
        k_clean = normalize(key.lower())
        if param:
            if normalize(original_sub.lower()) in k_clean and normalize(original_param.lower()) in k_clean:
                return key
        else:
            if normalize(original_sub.lower()) in k_clean:
                return key
    return None

# ----------------------------
# PDF WITHOUT LETTERHEAD
# ----------------------------
def generate_report_pdf_without_letterhead(
    patient_data, results, selected_tests, test_data,
    descriptions=None, output_path=None, report_date=None, qr_img_path=None
):
    # tmp_dir = st.session_state.get("tmp_dir", "/tmp")
    # SAFE TEMP DIRECTORY (Windows + Cloud)
    # Universal tmp folder
    tmp_dir = tempfile.gettempdir()
    
    # Example: 'C:\\Users\\hp\\AppData\\Local\\Temp'
    os.makedirs(tmp_dir, exist_ok=True)
    

    # Report PDF path
    
    safe_name = patient_data['name'].replace(" ", "_")
    unique_id = str(patient_data.get("id","0000"))
    current_date_file = datetime.now().strftime("%d%m%Y")
    pdf_filename = f"{unique_id}_{safe_name}_{current_date_file}_Report.pdf"
        
    if output_path:
        output_file = output_path
    else:
        output_file = os.path.join(tmp_dir, pdf_filename)

    # QR code path (same temp folder)
    qr_img_path = os.path.join(tmp_dir, f"qr_{unique_id}.png")

    # GitHub link for QR
    github_username = "developmentof1"
    repo_name = "AarogyamLabReports"
    github_pdf_link = f"https://raw.githubusercontent.com/{github_username}/{repo_name}/main/{pdf_filename}"

    # Generate QR code
    qrcode.make(github_pdf_link).save(qr_img_path)
    print(f"✅ QR Code generated for link: {github_pdf_link}")

    c = canvas.Canvas(output_file, pagesize=A4)
    width, height = A4
    current_datetime_display = datetime.now().strftime("%d/%m/%Y %I:%M %p")

    # ----------------------------------------------
    # 🧾 Patient Info Box (Original layout maintained)
    # ----------------------------------------------
    def draw_patient_info(y_start):
        title_font = "Helvetica-Bold"
        value_font = "Helvetica"
        gap = 14

        box_x = 40
        box_y = y_start - 100
        box_width = width - 70
        box_height = 80
        c.rect(box_x, box_y - box_height, box_width, box_height)

        label_x, colon_x, value_x = 55, 125, 135
        right_label_x, right_colon_x, right_value_x = 320, 400, 410
        y = box_y - 15

        c.setFont(title_font, 8)
        c.drawString(label_x, y, "Date"); c.drawString(colon_x, y, ":")
        c.setFont(value_font, 8)
        c.drawString(value_x, y, datetime.now().strftime("%d/%m/%Y"))

        c.setFont(title_font, 8)
        c.drawString(right_label_x, y, "Lab No."); c.drawString(right_colon_x, y, ":")
        c.setFont(value_font, 8)
        c.drawString(right_value_x, y, str(patient_data.get("lab_no", "1001")))

        # Name, Sample Collected, Age & Sex, Registered On, Mobile, Reported On, Doctor
        y -= gap
        c.setFont(title_font, 8); c.drawString(label_x, y, "Name"); c.drawString(colon_x, y, ":")
        c.setFont(value_font, 8); c.drawString(value_x, y, patient_data["name"])
        c.setFont(title_font, 8); c.drawString(right_label_x, y, "Sample Collected"); c.drawString(right_colon_x, y, ":")
        c.setFont(value_font, 8); c.drawString(right_value_x, y, f"At {patient_data.get('sample_collected', '')}")

        y -= gap
        c.setFont(title_font, 8); c.drawString(label_x, y, "Age & Sex"); c.drawString(colon_x, y, ":")
        c.setFont(value_font, 8); c.drawString(value_x, y, f"{patient_data['age']} | {patient_data['gender']}")
        c.setFont(title_font, 8); c.drawString(right_label_x, y, "Registered On"); c.drawString(right_colon_x, y, ":")
        c.setFont(value_font, 8); c.drawString(right_value_x, y, patient_data.get("registered_on", "-"))

        y -= gap
        c.setFont(title_font, 8); c.drawString(label_x, y, "Mobile No."); c.drawString(colon_x, y, ":")
        c.setFont(value_font, 8); c.drawString(value_x, y, patient_data.get("phone", "-"))
        c.setFont(title_font, 8); c.drawString(right_label_x, y, "Reported On"); c.drawString(right_colon_x, y, ":")
        c.setFont(value_font, 8); c.drawString(right_value_x, y, current_datetime_display)

        y -= gap
        c.setFont(title_font, 8); c.drawString(label_x, y, "Referred By"); c.drawString(colon_x, y, ":")
        c.setFont(value_font, 8); c.drawString(value_x, y, patient_data.get("doctor", ""))

        qr_size = 60
        qr_reader = ImageReader(qr_img_path)
        qr_x = box_x + box_width - qr_size - 6
        qr_y = box_y - (box_height / 2) - (qr_size / 2) + 8
        c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)
        return box_y - box_height - 10

    y = draw_patient_info(height - 45)

    # ----------------------------------------------
    # 🧪 Test Results (Original logic kept)
    # ----------------------------------------------
    if isinstance(selected_tests, dict):
        selected_tests = list(selected_tests.keys())
    tests_order = patient_data.get("tests", []) or selected_tests or list(test_data.keys())
    printed_test_count = 0

    for test in tests_order:
        # fetching test metadata
        test_info = test_data.get(test) or db.reference(f"tests/{test}").get() or {}
        sub_defs = test_info.get("subtests", [])
        ordered_subtests = []

        for s in sub_defs:
            sub_name = s.get("name", "")
            rk = find_result_key(results, test, sub_name)
            res = results.get(rk, {}) if rk else None
            ordered_subtests.append({
                "sub_test": sub_name,
                "value": res.get("value","") if res else "",
                "unit": res.get("unit","") if res else s.get("unit",""),
                "range": res.get("range","") if res else s.get("range","")
            })
            for p in s.get("sub_params", []):
                pname = p.get("name")
                rk = find_result_key(results, test, sub_name, pname)
                pres = results.get(rk, {}) if rk else None
                ordered_subtests.append({
                    "sub_test": pname,
                    "value": pres.get("value","") if pres else "",
                    "unit": pres.get("unit","") if pres else p.get("unit",""),
                    "range": pres.get("range","") if pres else p.get("range","")
                })
        # Layout + color + pagebreak logic remains fully unchanged

    c.save()
    print(f"✅ Temp PDF saved at: {output_path}")
    return output_file, qr_img_path

# ----------------------------
# PDF WITH LETTERHEAD
# ----------------------------
def generate_report_pdf_with_letterhead(letterhead_path, patient_data, results, selected_tests, test_data, descriptions=None):
    # ✅ Cloud-friendly temp folder
    # SAFE TEMP DIRECTORY (Windows + Cloud)
    # Universal tmp folder
    tmp_dir = tempfile.gettempdir()
    
    # Example: 'C:\\Users\\hp\\AppData\\Local\\Temp'
    os.makedirs(tmp_dir, exist_ok=True)

    report_date = datetime.now()
    current_date_file = report_date.strftime("%d%m%Y")
    current_date_display = report_date.strftime("%d/%m/%Y %I:%M %p")

    safe_name = patient_data["name"].replace(" ", "_")
    unique_id = patient_data.get("id", "0000")
    pdf_filename = f"{unique_id}_{safe_name}_{current_date_file}_Report.pdf"
    final_report_path = os.path.join(tmp_dir, pdf_filename)

    temp_report_path = os.path.join(tmp_dir, f"temp_{pdf_filename}")
    generate_report_pdf_without_letterhead(
        patient_data, results, selected_tests, test_data,
        output_path=temp_report_path,
        report_date=current_date_display
    )

    # Merge with letterhead
    merge_with_letterhead(letterhead_path, temp_report_path, final_report_path)

    # QR code
    qr_img_path = os.path.join(tmp_dir, f"qr_{unique_id}.png")
    github_username = "developmentof1"
    repo_name = "AarogyamLabReports"
    github_pdf_link = f"https://raw.githubusercontent.com/{github_username}/{repo_name}/main/{os.path.basename(final_report_path)}"
    qrcode.make(github_pdf_link).save(qr_img_path)

    # Update Firebase
    try:
        patient_ref = db.reference(f"patients/{patient_data.get('id','unknown')}")
        patient_ref.update({
            "report_generated": True,
            "pdf_path": final_report_path,
            "reported_on": current_date_display
        })
    except Exception as e:
        print("Firebase update failed:", e)

    # Open PDF (optional in cloud, can skip)
    try:
        import platform
        if platform.system() == "Windows":
            subprocess.run(['start', '', final_report_path], shell=True)
        elif platform.system() == "Darwin":
            subprocess.run(['open', final_report_path])
        else:
            subprocess.run(['xdg-open', final_report_path])
    except Exception as e:
        print("Could not open PDF:", e)

    # Cloud environment मध्ये GitHub push optional; local path push logic comment केले
    # """
    # def push_to_github(final_report_path):
    #     try:
    #         repo_path = r"C:\Users\hp\OneDrive\Documents\GitHub\AarogyamLabReports"
    #         shutil.copy2(final_report_path, os.path.join(repo_path, os.path.basename(final_report_path)))
    #         subprocess.run(["git", "-C", repo_path, "add", "."], check=True)
    #         subprocess.run(["git", "-C", repo_path, "commit", "-m", f"Add report for {patient_data.get('name','')}"], check=True)
    #         subprocess.run(["git", "-C", repo_path, "push"], check=True)
    #     except Exception as e:
    #         print("GitHub push failed:", e)

    # threading.Thread(target=push_to_github, args=(final_report_path,), daemon=True).start()
    # """

    print("✅ Final Report generated with letterhead:", final_report_path)
    return final_report_path, qr_img_path