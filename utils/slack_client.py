import json
import boto3
import logging
import requests


class SlackClient:
    def __init__(
        self,
        slack_config: dict,
    ) -> None:
        self.token = None
        self.channel_id = None
        self._slack_config = slack_config
        aws_secret_client = boto3.client(
            service_name="secretsmanager",
            region_name=slack_config.get("token_secret_region"),
        )
        try:
            get_secret_value_response = aws_secret_client.get_secret_value(
                SecretId=slack_config.get("token_secret_name"),
            )
            self.token = json.loads(get_secret_value_response.get("SecretString")).get(
                slack_config.get("token_secret_key")
            )
            self.channel_id = json.loads(
                get_secret_value_response.get("SecretString")
            ).get(slack_config.get("channel_key"))
        except:
            logging.error(
                "Unable to retrieve Slack token from AWS Secret Manager object {}, key {}, region {}".format(
                    slack_config.get("token_secret_name"),
                    slack_config.get("token_secret_key"),
                    slack_config.get("token_secret_region"),
                )
            )
        else:
            logging.info(
                "Using Slack token {}, and generic notification chanenl {}".format(
                    self.token,
                    self.channel_id,
                )
            )

    def send_text(
        self,
        text: str,
    ):
        r = requests.post(
            url=self._slack_config.get("rest_endpoint"),
            headers={
                "Authorization": "Bearer {}".format(
                    self.token,
                )
            },
            json={
                "channel": self.channel_id,
                "text": text,
            },
        )
        logging.debug("SLACK RESPONSE: {text}".format(text=r.text))
