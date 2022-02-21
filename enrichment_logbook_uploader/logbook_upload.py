import pandas
import requests
import json
import warnings
from dateutil import parser


_ACTIVITY_ENRICHMENT_URL = "https://activity-enrichment.apps.binus.ac.id"


class ParserInfo(parser.parserinfo):
    MONTHS = [("Jan", "Januari"),
              ("Feb", "Februari"),
              ("Mar", "Maret"),
              ("Apr", "April"),
              ("Mei", "Mei"),
              ("Jun", "Juni"),
              ("Jul", "Juli"),
              ("Agu", "Agustus"),
              ("Sep", "September"),
              ("Okt", "Oktober"),
              ("Nov", "November"),
              ("Des", "Desember")]


def date_parser(date):
    return parser.parse(date)


def date_parser_id(date):
    return parser.parse(date, parserinfo=ParserInfo())


def read_excel(name):
    try:
        return pandas.read_excel(name, skiprows=8, parse_dates=[1], date_parser=date_parser_id)
    except parser.ParserError:
        pass

    try:
        return pandas.read_excel(name, skiprows=8, parse_dates=[1], date_parser=date_parser)
    except parser.ParserError:
        raise


def format_time(time):
    return time.strftime("%I:%M %p").replace("AM", "am").replace("PM", "pm")


def format_date_iso(time):
    return time.isoformat()


def format_date_custom(time):
    return time.strftime("%d %b %Y")


def remove_newline(string):
    return string.replace("\n", "")


def yn_prompt(string):
    return input(string + " [Y/n] ").casefold() in ["y", "yes", ""]


def get_logbookheaderid(month_name, headers):
    get_month_response = requests.get(_ACTIVITY_ENRICHMENT_URL + "/LogBook/GetMonths", headers=headers)

    if get_month_response.status_code != 200:
        if get_month_response.status_code == 403:
            print("Check your cookies")

        raise ConnectionError(
            f"Error getting logbook months: {get_month_response.status_code} {get_month_response.reason}"
        )

    for month in json.loads(get_month_response.text)["data"]:
        if month["month"] == month_name:
            return month["logBookHeaderID"]

    raise KeyError(f"Month '{month_name}' not found")


def generate_payload(df, logbook_header_id):
    payload_list = []
    skipped_dates = []

    for i in range(df.__len__()):
        try:
            payload = {"model[ID]": "00000000-0000-0000-0000-000000000000",
                       "model[LogBookHeaderID]": logbook_header_id,
                       "model[Date]": format_date_iso(df["Tanggal"][i]),
                       "model[Activity]": df["Kegiatan"][i],
                       "model[ClockIn]": format_time(df["Clock In"][i]),
                       "model[ClockOut]": format_time(df["Clock Out"][i]),
                       "model[Description]": remove_newline(df["Uraian/ Catatan/ Perubahan"][i]),
                       "model[flagjulyactive]": "false"}

            payload_list.append(payload)
            print("Generated payload for {}".format(format_date_custom(df["Tanggal"][i])))

        except Exception as e:
            payload_list.append("")
            skipped_dates.append(format_date_custom(df["Tanggal"][i]))
            print("Payload for {} skipped, Error message: {}".format(format_date_custom(df["Tanggal"][i]), e))

    print()
    print("Skipped dates:")
    for date in skipped_dates:
        print(date)
    print()

    return payload_list


def build_headers(activity_enrichment_cookies):
    return {"User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": _ACTIVITY_ENRICHMENT_URL + "/LearningPlan/StudentIndex",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": _ACTIVITY_ENRICHMENT_URL,
            "Cookie": activity_enrichment_cookies}


def send_requests(payloads, df, headers):
    with requests.Session() as session:
        for i in range(len(payloads)):
            if payloads[i]:
                print("Sending logbook payload - {}".format(format_date_custom(df["Tanggal"][i])))
                r = session.post(_ACTIVITY_ENRICHMENT_URL + "/LogBook/StudentSave", headers=headers, json=payloads[i])
                print(r.text)
                print()


def main(activity_enrichment_cookies=None):
    while True:
        excel_file_name = input("Excel file name: ")  # "february.xlsx"

        try:
            with warnings.catch_warnings():
                warnings.simplefilter(action="ignore", category=FutureWarning)

                df = read_excel(excel_file_name)
            break

        except FileNotFoundError:
            print(f"File {excel_file_name} not found")
            if yn_prompt("Re-enter file name?"):
                continue

            raise SystemExit(1)

        except parser.ParserError as e:
            print("Check your excel file")
            print("Error reading excel file: " + str(e))

    if not activity_enrichment_cookies:
        while True:
            activity_enrichment_cookies = input("Activity enrichment cookies: ")  # ".BinusActivity.Session=....;"

            if activity_enrichment_cookies.startswith(".BinusActivity.Session="):
                break

            print('Invalid cookies format, should be like ".BinusActivity.Session=....;"')
            if yn_prompt("Re-enter cookies?"):
                continue

            raise SystemExit(1)

    headers = build_headers(activity_enrichment_cookies)

    while True:
        upload_month = input("Upload month: ").capitalize()  # February

        try:
            logbook_header_id = get_logbookheaderid(upload_month, headers=headers)
            break

        except ConnectionError as e:
            print(str(e))
            raise SystemExit(1)

        except KeyError as e:
            print(str(e))
            if yn_prompt("Re-enter month name?"):
                continue

            raise SystemExit(1)

    payloads = generate_payload(df, logbook_header_id)

    print()

    if yn_prompt("Upload logbook to Binus?"):
        send_requests(payloads, df, headers=headers)
        print("Operation completed...")

    else:
        print("Operation cancelled...")
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print()
        print("KeyboardInterrupt")

    finally:
        print("Exiting...")
