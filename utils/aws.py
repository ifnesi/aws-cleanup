import boto3
import logging


class AWSInstance:
    def __init__(
        self,
        region_name: str,
        args=None,
        max_results: int = 100,
        service_name: str = "ec2",
        search_filter: list = None,
        notify_messages_config: dict = None,
    ) -> None:
        self._args = args
        self._service_name = service_name
        self._region_name = region_name
        self._search_filter = search_filter
        self._max_results = max_results
        self._notify_messages_config = notify_messages_config
        self._dry_run = "[DRY RUN] " if self._args.dry_run else ""

        self.client = boto3.client(
            service_name,
            region_name=region_name,
        )

    def get_regions(self):
        logging.info("Getting regions")
        return [
            region["RegionName"] for region in self.client.describe_regions()["Regions"]
        ]

    def get_instances(self):
        # instances = [reservation["Instances"] for reservation in ec2_client.describe_instances(Filters=justin_filter)["Reservations"]]
        instances = list()
        describe_instances = self.client.describe_instances(
            MaxResults=self._max_results,
            Filters=self._search_filter,
        )
        while True:
            for reservation in describe_instances.get("Reservations", list()):
                instances += reservation.get("Instances", list())

            # Pagination
            next_token = describe_instances.get("NextToken")
            if next_token:
                describe_instances = self.client.describe_instances(
                    MaxResults=self._max_results,
                    Filters=self._search_filter,
                    NextToken=next_token,
                )
            else:
                break

        logging.info(
            "Total {} instances found: {}".format(
                self._service_name,
                len(instances),
            )
        )
        return instances

    def update_tag(
        self,
        instance_id,
        instance_name,
        key,
        value,
        old_value,
    ):
        # TODO: In the future, could batch this up, for now doing it one at a time
        logging.info(
            "{}Updating of tag on {} [{}] in region {}: setting {} from {} to {}".format(
                self._dry_run,
                instance_name,
                instance_id,
                self._region_name,
                key,
                old_value,
                value,
            )
        )
        if not self._args.dry_run:
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
        logging.info(
            "{}Stopping instance {} [{}] in region {}".format(
                self._dry_run,
                instance_name,
                instance_id,
                self._region_name,
            )
        )
        if not self._args.dry_run:
            self.client.stop_instances(InstanceIds=[instance_id])

    def terminate(
        self,
        instance_id: str,
        instance_name: str,
    ):
        logging.info(
            "{}Terminating instance {} [{}] in region {}".format(
                self._dry_run,
                instance_name,
                instance_id,
                self._region_name,
            )
        )
        if not self._args.dry_run:
            self.client.terminate_instances(InstanceIds=[instance_id])
