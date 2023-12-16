from datetime import date, datetime


class Action:
    def __init__(
            self,
            id: int,
            type: str,
            channel_id: int,
            mod_id: int,
            timestamp: int,
            message_id: int = None):
        """Represents an action.

        Args:
            id (int): Database id.
            type (str): Type of action, "sent", "edited", or "deleted".
            channel_id (int): Id of the discord channel the action occured in.
            mod_id (int): Id of the moderator that executed the action.
            timestamp (int): Unix timestamp of when the action was executed.
            message_id (int, optional): Id of the message the action is referencing (does not exist when action is "deleted"). Defaults to None.
        """
        self.id = id
        if type.lower() not in ["sent", "edited", "deleted"]:
            raise ValueError(
                f'"{type}" is not a valid type ("sent", "edited" or "deleted")')
        self.type = type.lower()
        self.channel_id = channel_id
        self.mod_id = mod_id
        self.timestamp = timestamp
        self.message_id = message_id


class Moderator:
    def __init__(
            self,
            user_id: int,
            send_quota: int,
            edit_quota: int,
            delete_quota: int,
            consecutive_completed_weeks: int,
            vacation_days: int,
            active: int) -> None:
        """Represents a moderator.

        Args:
            user_id (int): Discord id of the moderator.
            send_quota (int): The weekly send message quota of the moderator.
            edit_quota (int): The weekly edit message quota of the moderator.
            delete_quota (int): The weekly message deletion quota of the moderator.
            consecutive_completed_weeks (int): The amount of consecutive weeks the moderator has fufilled their quota.
            vacation_days (int): The total amount of vacation days the moderator has taken since joining the team.
            active (int): either 0 or 1, if the moderator is active and registered or not.
        """
        self.id = user_id
        self.send_quota = send_quota
        self.edit_quota = edit_quota
        self.delete_quota = delete_quota
        self.consecutive_completed_weeks = consecutive_completed_weeks
        self.vacation_days = vacation_days
        self.active = active

    @property
    def quotas(self) -> tuple[int, int, int]:
        """Another interaface to the three quotas. Let's you use *Moderator.quotas to simplify function calls.

        Returns:
            tuple[int, int, int]: Returns the send, edit and delete quotas of the mod, in that order.
        """
        return [self.send_quota, self.edit_quota, self.delete_quota]

    @quotas.setter
    def quotas(self, value: tuple[int, int, int]) -> None:
        """Another interface to the three quotas. Let's you easily set all of them at the same time.

        Args:
            value (tuple[int, int, int]): New values for the send, edit and delete quotas, in that order.
        """
        self.send_quota = value[0]
        self.edit_quota = value[1]
        self.delete_quota = value[2]


class StickyMessage:
    def __init__(self, channel_id: int, message_id: int, title: str, description: str):
        """Represents a sticky message object.

        Args:
            channel_id (int): Discord id of the channel with the message.
            message_id (int): Discord id of the message sent.
            title (str): The title of the embed message.
            description (str): The descrition of the embed message.
        """
        self.message_id = message_id
        self.channel_id = channel_id
        self.title = title
        self.description = description


class VacationWeek:
    def __init__(self, date: str, mod_id: int) -> None:
        """Represents a vaction week.

        Args:
            date (str): Date of the week in the form yyyy-ww.
            mod_id (int): Discord id of the moderator that took the vacation.
        """
        self.date = date
        self.mod_id = mod_id

    @property
    def dateobj(self) -> date:
        """Returns a datetime object for the monday based on this the date field in this object.

        Returns:
            date: A datetime object for the monday of the given week
        """
        return datetime.strptime(self.date + "-1", "%Y-%W-%w")

    @dateobj.setter
    def dateobj(self, date: date):
        """Sets the internal date string to the given year and week of the given datetime object.

        Args:
            date (date): Datetime object for the week we wish to update to.
        """
        self.date = date.strftime('%Y-%W')


class Guild:
    def __init__(
            self,
            guild_id: int,
            mod_category_id: int,
            last_mod_check: int,
            time_between_checks: int,
            default_quotas: str | tuple[int, int, int],
            member_count_channel_id: int) -> None:
        """Represents a guild config entry.

        Args:
            guild_id (int): The guild id for the guild.
            mod_category_id (int): The id of the mod category.
            last_mod_check (int): Unix timestamp for last time the moderator stats were checked.
            time_between_checks (int): The amount of seconds that we should wait before next mod check.
            default_quota (str | tuple): The default quota for any new moderators.
            member_cont_channel_id (int): The id of the channel to use for member counts
        """

        if isinstance(default_quotas, str):
            default_quotas = tuple(default_quotas.split(","))

        self.id = guild_id
        self.mod_category_id = mod_category_id
        self.last_mod_check = last_mod_check
        self.time_between_checks = time_between_checks
        self.default_quotas: tuple[int, int, int] = default_quotas
        self.member_count_channel_id = member_count_channel_id
