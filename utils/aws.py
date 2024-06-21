import boto3
import logging


class AWSRegions:
    def __init__(
        self,
        service_name: str,
        region_name: str,
    ) -> None:
        self._service_name = service_name
        self._region_name = region_name
        self.aws_client = boto3.client(
            service_name,
            region_name=region_name,
        )

    def get_regions(self):
        logging.info("Getting regions")
        return [
            region["RegionName"]
            for region in self.aws_client.describe_regions()["Regions"]
        ]


class EC2Instance:
    def __init__(
        self,
        notify_messages_config: dict,
        region: str,
        args,
        search_filter: list,
        max_results: int = 500,
    ) -> None:
        self._args = args
        self._region = region
        self._notify_messages_config = notify_messages_config
        self.client = boto3.client(
            "ec2",
            region_name=region,
        )
        # https://stackoverflow.com/a/952952
        # instances = [reservation["Instances"] for reservation in ec2_client.describe_instances(Filters=justin_filter)["Reservations"]]
        # TODO: Add pagination, maybe (hopefully we don't have more than 500 instance running...)
        self.instances = [
            instance
            for reservation in self.client.describe_instances(
                MaxResults=max_results,
                Filters=search_filter,
            )["Reservations"]
            for instance in reservation["Instances"]
        ]

    def update_tag(
        self,
        instance_id,
        instance_name,
        key,
        value,
        old_value,
    ):
        # TODO: In the future, could batch this up, for now doing it one at a time
        if self._args.dry_run:
            logging.info(
                "DRY RUN: Skipping update of tag on {0} [{1}] in region {2}: setting {3} from {5} to {4}".format(
                    instance_name,
                    instance_id,
                    self._region,
                    key,
                    value,
                    old_value,
                )
            )
        else:
            logging.info(
                "Updating tag on {0} [{1}] in region {2}: setting {3} to {4}".format(
                    instance_name,
                    instance_id,
                    self._region,
                    key,
                    value,
                    old_value,
                )
            )
            # This is super sloppy; right now we're relying on the fact that this is called after ec2_client has created for the relevant region
            # Later could either pass it in, or create an array of clients for regions
            # str(value) takes care of converting datetime.date to string in isoformat '2024-01-01'
            self.client.create_tags(
                Resources=[instance_id],
                Tags=[
                    {
                        "Key": key,
                        "Value": str(value),
                    }
                ],
            )

    def stop(
        self,
        instance_id: str,
        instance_name: str,
    ):
        if self._args.dry_run:
            logging.info(
                "DRY RUN: Stopping instance {0} [{1}] in region {2}".format(
                    instance_name,
                    instance_id,
                    self._region,
                )
            )
        else:
            logging.info(
                "Stopping instance {0} [{1}] in region {2}".format(
                    instance_name,
                    instance_id,
                    self._region,
                )
            )
            self.client.stop_instances(InstanceIds=[instance_id])

    def terminate(
        self,
        instance_id: str,
        instance_name: str,
    ):
        if self._args.dry_run:
            logging.info(
                "DRY RUN: Terminating instance {0} [{1}] in region {2}".format(
                    instance_name,
                    instance_id,
                    self._region,
                )
            )
        else:
            logging.info(
                "Terminating instance {0} [{1}] in region {2}".format(
                    instance_name,
                    instance_id,
                    self._region,
                )
            )
            self.client.terminate_instances(InstanceIds=[instance_id])
