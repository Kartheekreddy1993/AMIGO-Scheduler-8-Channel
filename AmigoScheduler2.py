import os
import re
import chardet
from lxml import etree
from datetime import datetime, timedelta

# ================= CONFIG =================

NOTEPAD_FILE = r"D:\Tools\Auto Schedule\list.txt"
CHANNEL_XML = r"D:\Tools\Auto Schedule\Channel1.xml"
DEFAULT_DURATION_SECONDS = 1800.0  # 30 minutes fallback

# ================= HELPERS =================

def format_duration(seconds: float) -> str:
    """Convert seconds to HH:MM:SS"""
    seconds = int(seconds)
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{h:02}:{m:02}:{s:02}"

def extract_info_durations(xml_text):
    """
    Extract ONLY duration values from <info ... duration='...'>
    Works even if XML is invalid.
    """
    pattern = r"<info[^>]*\bduration\s*=\s*['\"]([\d.]+)['\"]"
    return [float(x) for x in re.findall(pattern, xml_text, re.IGNORECASE)]

# ================= MAIN =================

# Read notepad list
with open(NOTEPAD_FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

for line in lines:
    if not line.strip():
        continue

    parts = line.strip().split(",")

    folder_path = parts[0]
    input_date_str = parts[1]
    time_slot_str = parts[2]

    combined_datetime_str = f"{input_date_str} {time_slot_str}"

    try:
        input_datetime = datetime.strptime(
            combined_datetime_str,
            "%d-%m-%Y %I:%M:%S %p"
        )
    except ValueError:
        print("❌ Invalid date/time in list.txt")
        continue

    # Iterate files inside folder
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith((".xml", ".txt")):
            continue

        file_path = os.path.join(folder_path, filename)
        file_name = os.path.splitext(filename)[0]

        # Detect encoding
        with open(file_path, "rb") as f:
            raw = f.read()
            encoding = chardet.detect(raw)["encoding"] or "utf-8"

        # Read file safely
        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            xml_data = f.read()

        # ---- EXTRACT DURATION (NO XML PARSING) ----
        info_durations = extract_info_durations(xml_data)

        if info_durations:
            total_duration = sum(info_durations)
            duration_source = "INFO"
        else:
            total_duration = DEFAULT_DURATION_SECONDS
            duration_source = "DEFAULT"

        formatted_duration = format_duration(total_duration)
        end_datetime = input_datetime + timedelta(seconds=total_duration)

        # ---- WRITE TO Channel1.xml ----
        tree = etree.parse(CHANNEL_XML)
        root = tree.getroot()

        new_record_id = str(len(root.findall("Record")))
        record = etree.Element("Record", ID=new_record_id)

        etree.SubElement(record, "ScheduleTime").text = input_datetime.strftime(
            "%d-%m-%Y %H:%M:%S"
        )
        etree.SubElement(record, "SchListPath").text = file_path
        etree.SubElement(record, "schListName").text = file_name
        etree.SubElement(record, "schListfilesCount").text = str(len(info_durations))
        etree.SubElement(record, "schListDuration").text = formatted_duration
        etree.SubElement(record, "SchListEndTime").text = end_datetime.strftime(
            "%d-%m-%Y %H:%M:%S"
        )
        #etree.SubElement(record, "DurationSource").text = duration_source

        root.append(record)

        with open(CHANNEL_XML, "wb") as f:
            tree.write(
                f,
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True
            )

        print(
            f"✔ Added: {file_name} | "
            f"Duration: {formatted_duration} | "
            f"Source: {duration_source}"
        )

        # Move to next day
        input_datetime += timedelta(days=1)
