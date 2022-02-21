import requests
import re
from bs4 import BeautifulSoup


_BINUSMAYA_URL = "https://binusmaya.binus.ac.id"
_ENRICHMENT_URL = "https://enrichment.apps.binus.ac.id"


class LoginError(Exception):
    pass


def default_headers():
    return {"User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"}


def bs_parse(content):
    return BeautifulSoup(content, features="html.parser")


def binusmaya_login(username, password):
    with requests.Session() as session:
        session.headers = default_headers()

        login_page = bs_parse(session.get(_BINUSMAYA_URL + "/login").text)
        input_tags = login_page.find_all("input")
        loader_script_path = login_page.find("script", src=re.compile("/login/loader.php"))["src"][2:]
        loader_script = bs_parse(session.get(_BINUSMAYA_URL + loader_script_path).text)
        input_tags.extend(loader_script.find_all("input"))

        payload_keys = [tag["name"] for tag in input_tags]
        payload_values = [username, password, *[tag["value"] for tag in input_tags[2:]]]
        payload = dict(zip(payload_keys, payload_values))

        login_response = session.post(_BINUSMAYA_URL + "/login/sys_login.php", data=payload)

        if "/newStudent" in login_response.url:
            return login_response.request.headers["Cookie"]
        elif "/login/?error=1" in login_response.url:
            error_reason = bs_parse(login_response.text).find("div", id="login_error")
            raise LoginError("BinusMaya login error" if error_reason is None else error_reason.text)
        elif login_response.status_code != 200:
            raise LoginError(f"BinusMaya login error: {login_response.status_code} {login_response.reason}")
        else:
            raise LoginError("BinusMaya login error")


def activity_enrichment_login(binusmaya_cookies):
    with requests.Session() as session:
        session.headers = default_headers()

        token_request_header = {"Referer": _BINUSMAYA_URL + "/newStudent/",
                                "Cookie": binusmaya_cookies}

        get_token_path = "/services/ci/index.php/student/enrichmentApps/GetToken/"
        get_token_response = session.get(_BINUSMAYA_URL + get_token_path, headers=token_request_header)

        generate_sso_token_path = "/services/ci/index.php/student/enrichmentApps/GenerateSSOTokenEnrichment/"
        generate_sso_token_response = session.post(_BINUSMAYA_URL + generate_sso_token_path,
                                                   json={"Token": get_token_response.text.strip('"')},
                                                   headers=token_request_header)

        session.get(_ENRICHMENT_URL + "/Login/Student/SSO", params={"t": generate_sso_token_response.text.strip('"')})

        activity_enrichment_login_response = session.get(_ENRICHMENT_URL + "/Login/Student/SSOToActivity")

        if "/LearningPlan/StudentIndex" in activity_enrichment_login_response.url:
            return activity_enrichment_login_response.request.headers["Cookie"]
        else:
            raise LoginError("Activity Enrichment login error")


if __name__ == "__main__":
    print("This module is not runnable by itself")
