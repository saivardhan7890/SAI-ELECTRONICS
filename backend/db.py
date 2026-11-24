import json
import os

import boto3
import pymysql


def get_connection():
    required_variables = ("DB_SECRET_ARN", "DB_HOST", "DB_NAME")
    missing = [name for name in required_variables if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "Missing Lambda environment variable(s): " + ", ".join(missing)
        )

    region = os.environ.get("AWS_REGION")
    client = boto3.client("secretsmanager", region_name=region)

    secret_response = client.get_secret_value(
        SecretId=os.environ["DB_SECRET_ARN"]
    )
    credentials = json.loads(secret_response["SecretString"])

    return pymysql.connect(
        host=os.environ["DB_HOST"],
        user=credentials["username"],
        password=credentials["password"],
        database=os.environ["DB_NAME"],
        port=int(os.environ.get("DB_PORT", "3306")),
        connect_timeout=10,
        read_timeout=15,
        write_timeout=15,
        charset="utf8mb4",
        autocommit=False
    )
