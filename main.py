from enrichment_logbook_uploader import binus_login as bl, logbook_upload as lu
from getpass import getpass


def main():
    print("Binusmaya Login")
    binusmaya_cookies = ""

    while True:
        try:
            username = input("Enter your username: ").split("@")[0]
            password = getpass("Enter your password: ")

            binusmaya_cookies = bl.binusmaya_login(username, password)
            break

        except bl.LoginError as e:
            print("Login failed: " + str(e))
            if input("Try again? [Y/n]").casefold() in ["y", "yes", ""]:
                continue

            raise SystemExit(1)

    try:
        print("Logging in to activity enrichment...")
        enrichment_cookies = bl.activity_enrichment_login(binusmaya_cookies)
        print("Activity enrichment login successful...")
        
    except bl.LoginError as e:
        print("Login failed: " + str(e))
        raise SystemExit(1)

    lu.main(enrichment_cookies)


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print()
        print("KeyboardInterrupt")

    finally:
        print("Exiting...")
