import sys
import json
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Usage: python deploy_apps_script.py "Business Name"

def deploy_apps_script(business_name):
    # Load config.json (contains sheet_id from create_sheet.py)
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    sheet_id = config["sheet_id"]

    # Load service account credentials
    creds = service_account.Credentials.from_service_account_file(
        "service_account.json",
        scopes=["https://www.googleapis.com/auth/script.projects",
                "https://www.googleapis.com/auth/script.deployments"]
    )

    service = build("script", "v1", credentials=creds)

    # 1. Create a new Apps Script project bound to the Sheet
    request = {
        "title": f"{business_name} Order Backend",
        "parentId": sheet_id
    }
    project = service.projects().create(body=request).execute()
    script_id = project["scriptId"]

    # 2. Upload Code.gs content
    with open("Code.gs", "r", encoding="utf-8") as f:
        code_content = f.read()

    files = [{
        "name": "Code",
        "type": "SERVER_JS",
        "source": code_content
    }]

    manifest = {
        "timeZone": "Asia/Kolkata",
        "exceptionLogging": "STACKDRIVER"
    }

    content = {"files": files + [{"name": "appsscript", "type": "JSON", "source": json.dumps(manifest)}]}
    service.projects().updateContent(scriptId=script_id, body=content).execute()

    # 3. Deploy as Web App
    version = service.projects().versions().create(scriptId=script_id, body={"description": "Initial deploy"}).execute()
    version_number = version["versionNumber"]

    deployment = service.projects().deployments().create(
        scriptId=script_id,
        body={
            "versionNumber": version_number,
            "manifestFileName": "appsscript",
            "deploymentConfig": {
                "webApp": {
                    "access": "ANYONE",
                    "executeAs": "USER_DEPLOYING"
                }
            }
        }
    ).execute()

    web_app_url = deployment["deploymentConfig"]["webApp"]["url"]

    # 4. Save Web App URL back to config.json
    config["web_app_url"] = web_app_url
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"Deployed Apps Script for {business_name}. Web App URL: {web_app_url}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy_apps_script.py 'Business Name'")
        sys.exit(1)

    business_name = sys.argv[1]
    deploy_apps_script(business_name)
