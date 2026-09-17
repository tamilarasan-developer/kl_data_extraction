import json
import time
import requests

from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand
from django.utils import timezone

from data.models import ksldc


# ============================================================
# CONFIGURATION
# ============================================================

KPTCL_URL = (
    "https://kptclsldc.in/StateNCEP.aspx"
)

PUSH_URL = (
    "http://172.16.7.93:8002/ka/push.ksldc.php"
)

JSON_FILE = "kl_data_output.json"

# Run every 5 minutes
SLEEP_SECONDS = 300


# ============================================================
# KPTCL REQUEST HEADERS
# ============================================================

KPTCL_HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),

    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),

    "Accept-Language": (
        "en-US,en;q=0.9"
    ),

    "Connection": "keep-alive",
}


# ============================================================
# PUSH HEADERS
# ============================================================

PUSH_HEADERS = {

    "Content-Type": "application/json",

    "Accept": "application/json",
}


# ============================================================
# REQUIRED DATA FIELDS
# ============================================================

DATA_FIELDS = [

    "bio_mass",

    "cogen",

    "mini_hydro",

    "wind",

    "solar",

    "total",
]


# ============================================================
# CURRENT TIME
# ============================================================

def get_current_time():

    """
    Get current local time.

    Example:

    2026-09-10 14:34:42
    """

    current_time = timezone.now()

    if timezone.is_aware(current_time):

        current_time = timezone.localtime(
            current_time
        )

    return current_time


# ============================================================
# FORMAT DATETIME
# ============================================================

def format_datetime(value):

    """
    Exact required format:

    YYYY-MM-DD HH:MM:SS

    Example:

    2026-09-10 14:30:00
    """

    return value.strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# NULL CHECK
# ============================================================

def is_null(value):

    if value is None:

        return True

    if isinstance(value, str):

        value = value.strip()

        if value == "":

            return True

        if value.lower() in [

            "null",
            "none",
            "-",
            "--",
            "n/a",
            "na",
        ]:

            return True

    return False


# ============================================================
# CONVERT VALUE
# ============================================================

def convert_value(value):

    if is_null(value):

        return None

    try:

        value = str(value).strip()

        # Remove comma
        value = value.replace(
            ",",
            ""
        )

        return int(
            float(value)
        )

    except (
        ValueError,
        TypeError
    ):

        return None


# ============================================================
# CHECK CURRENT DATA NULL
# ============================================================

def has_null_value(data):

    for field in DATA_FIELDS:

        if data.get(field) is None:

            return True

    return False


# ============================================================
# GET 15-MINUTE BLOCK
# ============================================================

def get_block_datetime(current_time):

    """
    Current time is converted to
    the starting time of the 15-minute block.

    Example:

    14:31:42 -> 14:30:00
    14:35:42 -> 14:30:00
    14:40:42 -> 14:30:00

    14:45:42 -> 14:45:00
    """

    block_minute = (
        current_time.minute // 15
    ) * 15

    return current_time.replace(

        minute=block_minute,

        second=0,

        microsecond=0
    )


# ============================================================
# GET TRIGGER NUMBER
# ============================================================

def get_trigger_number(current_time):

    """
    Trigger is based on actual execution time.

    14:30 - 14:34 -> Trigger 1
    14:35 - 14:39 -> Trigger 2
    14:40 - 14:44 -> Trigger 3

    14:45 - 14:49 -> Trigger 1
    14:50 - 14:54 -> Trigger 2
    14:55 - 14:59 -> Trigger 3
    """

    position = (
        current_time.minute % 15
    )

    if position < 5:

        return 1

    elif position < 10:

        return 2

    else:

        return 3


# ============================================================
# FETCH KPTCL DATA
# ============================================================

def fetch_kptcl_data():

    print()
    print(
        "[FETCH] Connecting to KPTCL..."
    )

    try:

        session = requests.Session()

        response = session.get(

            KPTCL_URL,

            headers=KPTCL_HEADERS,

            timeout=30
        )

        response.raise_for_status()

        print(
            f"[FETCH] Success | "
            f"HTTP {response.status_code}"
        )

        print(
            f"[FETCH] Content length: "
            f"{len(response.text)}"
        )

        return response.text

    except requests.RequestException as error:

        print(
            f"[FETCH ERROR] {error}"
        )

        return None

    except Exception as error:

        print(
            f"[FETCH ERROR] {error}"
        )

        return None


# ============================================================
# PARSE KPTCL DATA
# ============================================================

def parse_data(html):

    soup = BeautifulSoup(

        html,

        "html.parser"
    )

    rows = soup.find_all("tr")

    print(
        f"[PARSE] Rows found: "
        f"{len(rows)}"
    )

    result = []

    for row in rows:

        columns = row.find_all(
            ["td", "th"]
        )

        values = [

            column.get_text(
                strip=True
            )

            for column in columns
        ]

        # We need 7 columns:
        #
        # ESCOMS
        # BIO-MASS
        # COGEN
        # MINI-HYDRO
        # WIND
        # SOLAR
        # TOTAL

        if len(values) < 7:

            continue

        escom_name = (
            values[0].strip()
        )

        # ====================================================
        # REMOVE HEADER ROW
        # ====================================================

        if escom_name.lower() in [

            "escom",
            "escoms",
            "escom name",
            "name",
        ]:

            print(
                f"[PARSE] Header skipped: "
                f"{escom_name}"
            )

            continue

        # ====================================================
        # CREATE DATA
        # ====================================================

        data = {

            "escom_name":
                escom_name,

            "bio_mass":
                convert_value(
                    values[1]
                ),

            "cogen":
                convert_value(
                    values[2]
                ),

            "mini_hydro":
                convert_value(
                    values[3]
                ),

            "wind":
                convert_value(
                    values[4]
                ),

            "solar":
                convert_value(
                    values[5]
                ),

            "total":
                convert_value(
                    values[6]
                ),
        }

        result.append(data)

    print(
        f"[PARSE] Valid rows: "
        f"{len(result)}"
    )

    return result


# ============================================================
# DATABASE PROCESSING
# ============================================================

def process_database(
    data_list,
    block_datetime,
    trigger_number
):

    """
    IMPORTANT LOGIC:

    1. Trigger number comes from actual clock time.

    2. Check whether this ESCOM already has
       a record for this 15-minute block.

    3. Record does NOT exist:
       --------------------------------
       Current data is first available data
       for this block.

       INSERT it.

       This can happen on Trigger 1,
       Trigger 2 or Trigger 3.

       Example:

       T1 -> MISS
       T2 -> SUCCESS

       T2 becomes first available data
       and gets INSERTED.

    4. Record already exists:
       --------------------------------
       Current data has NULL:
           HOLD old data.

       Current data is valid:
           UPDATE old data.

    """

    print()
    print(
        "[DATABASE] Processing..."
    )

    formatted_block_time = (
        format_datetime(
            block_datetime
        )
    )

    current_time = get_current_time()

    formatted_current_time = (
        format_datetime(
            current_time
        )
    )

    print(
        f"[DATABASE] Block   : "
        f"{formatted_block_time}"
    )

    print(
        f"[DATABASE] Trigger : "
        f"{trigger_number}"
    )

    json_output = []

    # ========================================================
    # PROCESS EACH ESCOM
    # ========================================================

    for data in data_list:

        escom_name = data[
            "escom_name"
        ]

        current_has_null = (
            has_null_value(data)
        )

        # ====================================================
        # FIND BLOCK RECORD
        # ====================================================

        try:

            obj = ksldc.objects.get(

                escom_name=escom_name,

                date_time=formatted_block_time
            )

            record_exists = True

        except ksldc.DoesNotExist:

            obj = None

            record_exists = False

        # ====================================================
        # RECORD DOES NOT EXIST
        # ====================================================

        if not record_exists:

            """
            FIRST AVAILABLE DATA

            It doesn't matter whether this is
            Trigger 1, 2 or 3.

            If no record exists for this block,
            save the available data.
            """

            try:

                obj = ksldc.objects.create(

                    escom_name=escom_name,

                    bio_mass=data[
                        "bio_mass"
                    ],

                    cogen=data[
                        "cogen"
                    ],

                    mini_hydro=data[
                        "mini_hydro"
                    ],

                    wind=data[
                        "wind"
                    ],

                    solar=data[
                        "solar"
                    ],

                    total=data[
                        "total"
                    ],

                    date_time=(
                        formatted_block_time
                    ),

                    updated_time=(
                        formatted_current_time
                    )
                )

                if current_has_null:

                    print(
                        f"[TRIGGER {trigger_number}]"
                        f"[INSERT] "
                        f"{escom_name} | "
                        f"PARTIAL NULL | "
                        f"FIRST AVAILABLE DATA SAVED"
                    )

                else:

                    print(
                        f"[TRIGGER {trigger_number}]"
                        f"[INSERT] "
                        f"{escom_name} | "
                        f"ALL VALID | "
                        f"FIRST AVAILABLE DATA SAVED"
                    )

            except Exception as error:

                print(
                    f"[DB INSERT ERROR] "
                    f"{escom_name} | "
                    f"{error}"
                )

                continue

        # ====================================================
        # RECORD EXISTS
        # ====================================================

        else:

            # =================================================
            # CURRENT DATA HAS NULL
            # =================================================

            if current_has_null:

                print(
                    f"[TRIGGER {trigger_number}]"
                    f"[HOLD] "
                    f"{escom_name} | "
                    f"NULL FOUND | "
                    f"OLD DATA KEPT"
                )

            # =================================================
            # CURRENT DATA IS VALID
            # =================================================

            else:

                try:

                    obj.bio_mass = data[
                        "bio_mass"
                    ]

                    obj.cogen = data[
                        "cogen"
                    ]

                    obj.mini_hydro = data[
                        "mini_hydro"
                    ]

                    obj.wind = data[
                        "wind"
                    ]

                    obj.solar = data[
                        "solar"
                    ]

                    obj.total = data[
                        "total"
                    ]

                    obj.updated_time = (
                        formatted_current_time
                    )

                    obj.save()

                    print(
                        f"[TRIGGER {trigger_number}]"
                        f"[UPDATE] "
                        f"{escom_name} | "
                        f"ALL VALID | "
                        f"UPDATED"
                    )

                except Exception as error:

                    print(
                        f"[DB UPDATE ERROR] "
                        f"{escom_name} | "
                        f"{error}"
                    )

        # ====================================================
        # GET FINAL DATABASE VALUE
        # ====================================================

        try:

            final_obj = ksldc.objects.get(

                escom_name=escom_name,

                date_time=formatted_block_time
            )

            json_output.append({

                "escom_name":
                    final_obj.escom_name,

                "bio_mass":
                    final_obj.bio_mass,

                "cogen":
                    final_obj.cogen,

                "mini_hydro":
                    final_obj.mini_hydro,

                "wind":
                    final_obj.wind,

                "solar":
                    final_obj.solar,

                "total":
                    final_obj.total,

                "date_time":
                    final_obj.date_time,

                "updated_time":
                    final_obj.updated_time
            })

        except ksldc.DoesNotExist:

            print(
                f"[JSON ERROR] "
                f"{escom_name} | "
                f"Record not found"
            )

    return json_output


# ============================================================
# SAVE JSON FILE
# ============================================================

def save_json_file(json_data):

    print()
    print(
        "[JSON] Saving JSON file..."
    )

    try:

        with open(

            JSON_FILE,

            "w",

            encoding="utf-8"
        ) as file:

            json.dump(

                json_data,

                file,

                indent=4,

                ensure_ascii=False
            )

        print(
            f"[JSON] "
            f"{JSON_FILE} saved."
        )

    except Exception as error:

        print(
            f"[JSON ERROR] {error}"
        )


# ============================================================
# PUSH JSON TO API
# ============================================================

def push_json(json_data):

    print()
    print(
        "[PUSH] Sending JSON..."
    )

    if not json_data:

        print(
            "[PUSH] JSON is empty."
        )

        print(
            "[PUSH] Nothing to send."
        )

        return

    try:

        response = requests.post(

            PUSH_URL,

            headers=PUSH_HEADERS,

            json=json_data,

            timeout=30
        )

        print(
            f"[PUSH] HTTP Status: "
            f"{response.status_code}"
        )

        print(
            f"[PUSH RESPONSE] "
            f"{response.text}"
        )

        if response.ok:

            print(
                "[PUSH] SUCCESS"
            )

        else:

            print(
                f"[PUSH ERROR] "
                f"Server returned HTTP "
                f"{response.status_code}"
            )

            print(
                f"[PUSH ERROR BODY] "
                f"{response.text}"
            )

    except requests.RequestException as error:

        print(
            f"[PUSH ERROR] {error}"
        )

    except Exception as error:

        print(
            f"[PUSH ERROR] {error}"
        )


# ============================================================
# RUN ONE EXECUTION
# ============================================================

def run_once():

    print()
    print("=" * 70)

    print(
        "KSLDC DATA COLLECTION - START"
    )

    print("=" * 70)

    # ========================================================
    # CURRENT TIME
    # ========================================================

    current_time = get_current_time()

    print(
        f"[TIME] Current : "
        f"{format_datetime(current_time)}"
    )

    # ========================================================
    # 15 MINUTE BLOCK
    # ========================================================

    block_datetime = (
        get_block_datetime(
            current_time
        )
    )

    print(
        f"[TIME] Block   : "
        f"{format_datetime(block_datetime)}"
    )

    # ========================================================
    # TRIGGER
    # ========================================================

    trigger_number = (
        get_trigger_number(
            current_time
        )
    )

    print(
        f"[TIME] Trigger : "
        f"{trigger_number}"
    )

    # ========================================================
    # FETCH
    # ========================================================

    html = fetch_kptcl_data()

    # ========================================================
    # FETCH FAILED
    # ========================================================

    if not html:

        print()
        print(
            "[STOP] KPTCL fetch failed."
        )

        print(
            "[RETRY] Current attempt was "
            "not stored."
        )

        print(
            "[RETRY] Next execution will "
            "try again."
        )

        return

    # ========================================================
    # PARSE
    # ========================================================

    data_list = parse_data(
        html
    )

    if not data_list:

        print(
            "[STOP] No valid rows found."
        )

        return

    # ========================================================
    # DATABASE
    # ========================================================

    json_data = process_database(

        data_list,

        block_datetime,

        trigger_number
    )

    # ========================================================
    # SAVE JSON
    # ========================================================

    save_json_file(
        json_data
    )

    # ========================================================
    # PUSH JSON
    # ========================================================

    push_json(
        json_data
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("-" * 70)

    print(
        f"[SUMMARY] Trigger        : "
        f"{trigger_number}"
    )

    print(
        f"[SUMMARY] Block          : "
        f"{format_datetime(block_datetime)}"
    )

    print(
        f"[SUMMARY] Rows processed : "
        f"{len(json_data)}"
    )

    print("-" * 70)


# ============================================================
# DJANGO MANAGEMENT COMMAND
# ============================================================

class Command(BaseCommand):

    help = (
        "Fetch KSLDC data every 5 minutes "
        "and store data in 15-minute blocks."
    )

    def handle(
        self,
        *args,
        **options
    ):

        print()
        print(
            "KSLDC 5-MINUTE LOOP STARTED"
        )

        print(
            "Script will run every 5 minutes."
        )

        print(
            "Each 15-minute block has "
            "3 possible triggers."
        )

        print(
            "Trigger is based on actual "
            "execution time."
        )

        print(
            "Missed attempts will not "
            "lose the complete block."
        )

        print(
            "Press CTRL+C to stop."
        )

        print()

        try:

            while True:

                run_once()

                print()
                print(
                    "[WAIT] Next execution "
                    "in 5 minutes..."
                )

                print()

                time.sleep(
                    SLEEP_SECONDS
                )

        except KeyboardInterrupt:

            print()
            print("=" * 70)

            print(
                "KSLDC 5-MINUTE LOOP STOPPED"
            )

            print("=" * 70)