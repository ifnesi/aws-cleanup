import logging
import datetime


def determine_action(
    idn_action_date: datetime,
    idn_notification: list,
    i_default_days: int,
    i_max_days: int,
    notify_messages_config: dict,
    d_run_date: datetime,
):
    """
    Takes the following:
    - idn_action_date: Currently set action date
    - idn_notification: (list) Current dn_notification [(tag_name_value_1, days_1, tag_name_1), (tag_name_value_2, days_2, tag_name_2), ..., (tag_name_value_n, days_n, tag_name_n)]
    - i_default_days: Default number of days
    - i_max_days: Max number of days
    - notify_messages_config: As per config (notify_messages)
    - d_run_date: run date
    Returns dict with the following:
    - odn_notification_1: New dn_notification_1
    - odn_notification_2: New dn_notification_2
    - ...
    - odn_notification_n: New dn_notification_n
    - odn_action_date
    - result ENUM
    All actual changes (tags and/or instance modification) occurs in calling code, not here.
    """
    odn_notif = dict()
    odn_notif_none = dict()
    for n, notif in enumerate(idn_notification):
        odn_notif["odn_notification_{n}".format(n=n + 1)] = notif[0]
        odn_notif_none["odn_notification_{n}".format(n=n + 1)] = None

    logging.debug(
        "idn_action_date:[{idn_action_date}], {idn_notifications}, i_default_days:[{i_default_days}], i_max_days:[{i_max_days}]".format(
            idn_action_date=idn_action_date,
            idn_notifications=", ".join(
                [
                    "{key}:[{value}]".format(
                        key=key,
                        value=value,
                    )
                    for key, value in odn_notif.items()
                ]
            ),
            i_default_days=i_default_days,
            i_max_days=i_max_days,
        )
    )

    if idn_action_date is None:
        # message = "Set unset date"
        return {
            **odn_notif_none,
            "odn_action_date": d_run_date + datetime.timedelta(days=i_default_days),
            "result": notify_messages_config.get("add_action_date"),
        }

    elif idn_action_date - d_run_date > datetime.timedelta(days=i_max_days):
        # message = "Set to max"
        return {
            **odn_notif_none,
            "odn_action_date": d_run_date + datetime.timedelta(days=i_max_days),
            "result": notify_messages_config.get("reset_action_date"),
        }

    elif idn_action_date <= d_run_date:
        max_notif_days = len(idn_notification)
        odn_notif_aux = dict(odn_notif_none)  # Make copy of dictionary
        for n, notif in enumerate(idn_notification):
            odn_notif_aux[
                "odn_notification_{n}".format(
                    n=n + 1,
                )
            ] = d_run_date
            if n > 0:
                odn_notif_aux["odn_notification_{n}".format(n=n)] = idn_notification[
                    n - 1
                ][0]
            if notif[0] is None:
                # message = "Set stop date to today + N (missing notifications)"
                return {
                    **odn_notif_aux,
                    "odn_action_date": d_run_date
                    + datetime.timedelta(days=max_notif_days - n),
                    "result": notify_messages_config.get("past_bump_notification"),
                    "n": n + 1,
                }

        # message = "Complete action"
        odn_notif_aux[
            "odn_notification_{n}".format(n=len(idn_notification))
        ] = idn_notification[-1][0]
        return {
            **odn_notif_aux,
            "odn_action_date": d_run_date,
            "result": notify_messages_config.get("complete_action"),
        }

    else:
        remaining_days = idn_action_date - d_run_date
        odn_notif_aux = dict(odn_notif_none)  # Make copy of dictionary
        for n, notif in enumerate(idn_notification):
            odn_notif_aux[
                "odn_notification_{n}".format(
                    n=n + 1,
                )
            ] = d_run_date
            if n > 0:
                odn_notif_aux["odn_notification_{n}".format(n=n)] = idn_notification[
                    n - 1
                ][0]
            if notif[0] is None and remaining_days <= datetime.timedelta(days=notif[1]):
                # message = "Send #{n} notification".format(n=n+1)
                return {
                    **odn_notif_aux,
                    "odn_action_date": idn_action_date,
                    "result": notify_messages_config.get("send_notification"),
                    "n": n + 1,
                }

        # message = "Log without notification"
        odn_notif_aux[
            "odn_notification_{n}".format(n=len(idn_notification))
        ] = idn_notification[-1][0]
        return {
            **odn_notif_aux,
            "odn_action_date": idn_action_date,
            "result": notify_messages_config.get("log_no_notification"),
        }


def iso_format(date: str):
    try:
        if date:
            result = datetime.date.fromisoformat(date)
        else:
            result = None
    except Exception:
        raise ValueError("Invalid ISO date format, please try yyyy-mm-dd")
    return result


def sort_key(x):
    return " ".join(
        [
            x["email"],
            x["instance_type"],
            x["region"],
            x["action"],
            x["result"],
            x["instance_name"],
        ]
    )


def add_to_log(
    email,
    instance_type,
    instance_name,
    instance_id,
    region,
    action,
    tag,
    result,
    old_date,
    new_date,
    message,
):
    return {
        "email": email,
        "instance_type": instance_type,
        "instance_name": instance_name,
        "instance_id": instance_id,
        "region": region,
        "action": action,
        "tag": tag,
        "result": result,
        "old_date": old_date,
        "new_date": new_date,
        "message": message,
    }


def date_or_none(
    tags,
    tag,
):
    """
    Convert to a datetime.date on the way (or return None)
    """
    try:
        return datetime.date.fromisoformat(tags.get(tag))
    except Exception:
        return None


def sys_exc(exc_info):
    """
    Capture exception type, class and line number
    """
    exc_type, exc_obj, exc_tb = exc_info
    return "{exc_type} | {lineno} | {exc_obj}".format(
        exc_type=exc_type,
        lineno=exc_tb.tb_lineno,
        exc_obj=exc_obj,
    )


def datetime_handler(o):
    if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
        return str(o)