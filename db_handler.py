import sqlite3
from sqlite3 import Error
from helpers import Action, Moderator, StickyMessage, VacationWeek, Guild


class DBHandler():
    def __init__(self, path: str):
        """A class that handles any needed queries to the database.

        Args:
            path (str): The filepath of the database to load from
        """
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys = ON;")
        print("Connection to SQLite DB successful")

    def _execute_query(self, query: str, vars: tuple = ()) -> None:
        """Execute the given query with the object's database.

        Args:
            query (str): The query string.
            vars (tuple, optional): The vars to replace the spots in the query string. Defaults to ()
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, vars)
        except Error as e:
            print(f"The error '{e}' occurred")
        self.connection.commit()

    def _execute_read_query(self, query: str, vars: tuple = ()) -> tuple:
        """Executes the given query with the object's database, returning
        a single tuple. Is used for reading from the DB.

        Args:
            query (str): The string to query the database with.
            vars (tuple, optional): The vars to replace the spots in the query string. Defaults to ()

        Returns:
            tuple: A Touple containing the data at the found row.
        """
        cursor = self.connection.cursor()
        result = None
        try:
            cursor.execute(query, vars)
            result = cursor.fetchone()
            return result
        except Error as e:
            print(f"The error '{e}' occurred")

    def _execute_multiple_read_query(
            self,
            query: str,
            vars: tuple = ()) -> list[tuple]:
        """Executes the given query with the object's databse, returning
        a list of Tuples. Is used for reading from the database

        Args:
            query (str): The string to query the database with.

        Returns:
            list[tuple]: a list containing all the data found from the query.
        """
        cursor = self.connection.cursor()
        result = None
        try:
            cursor.execute(query, vars)
            result = cursor.fetchall()
            return result
        except Error as e:
            print(f"The error '{e}' occurred")


# -------------------------- STICKY HANDLING --------------------------


    def create_sticky(self, channel_id: int, message_id: int) -> None:
        """Adds a new sticky to the object's database.

        Args:
            channel_id (int): The discord Channel id of the message.
            message_id (int): The id of the message itself.
        """
        sticky_add_query = """
        INSERT INTO
            stickies (channel_id, message_id)
        VALUES
            (?, ?);
        """
        self._execute_query(sticky_add_query, (channel_id, message_id,))

    def update_sticky(self, channel_id: int, message_id: int) -> None:
        """Updates the DB entry for a given channel to point to another
        message

        Args:
            channel_id (int): The id of the discord channel the sticky is in.
            message_id (int): The id of the new sticky.
        """
        sticky_update_query = """
        UPDATE stickies
        SET
            message_id = ?
        WHERE
            channel_id = ?
        """
        self._execute_query(sticky_update_query, (message_id, channel_id,))

    def del_sticky(self, channel_id: int) -> None:
        """Remove a sticky from the object's db given a channel id

        Args:
            channel_id (int): The Id of the channel to remove the sticky from
        """
        sticky_del_query = "DELETE FROM stickies WHERE channel_id = ?"
        self._execute_query(sticky_del_query, (channel_id,))

    def get_sticky(self, channel_id: int) -> StickyMessage:
        """Returns the id of a sticky message given the id of the channel it's in.

        Args:
            channel_id (int): The id of the channel the sticky is in.

        Returns:
            StickyMessage: A sticky message object containing all info pertaining to the sticky message.
        """
        sticky_query = """
        SELECT * FROM stickies
        WHERE channel_id = ?"""

        # Return the message_id of the entry in the database as a StickyMessage
        # (second value of the tuple)

        result = self._execute_read_query(
            sticky_query, (channel_id,))

        if result:
            return StickyMessage(*result)
        return None

    def get_all_stickies(self) -> list[StickyMessage]:
        """Returns a list of all stickies in the object's database.

        Returns:
            list[StickyMessage]: A list of StickyMessage objects
        """
        sticky_query = """
        SELECT * FROM stickies
        """

        result = self._execute_multiple_read_query(sticky_query)

        if result:
            return [StickyMessage(*sticky) for sticky in result]
        return []


# --------------------------- MOD HANDLING ----------------------------

    def register_moderator(
            self, user_id: int, quotas: tuple[int, int, int]) -> None:
        """Adds a new moderator to the object's database.

        Args:
            user_id (int): Discord id of the user.
            quotas (tuple[int, int, int]): The quotas the user should reach weekly.
        """
        mod_test = self.get_moderator(user_id)
        if mod_test:
            if mod_test.active == 0:
                moderator_registration_query = """
                UPDATE moderators
                SET
                    send_quota = ?,
                    edit_quota = ?,
                    delete_quota = ?,
                    vacation_days = 0,
                    active = 1
                WHERE
                    user_id = ?
                """
                self._execute_query(
                    moderator_registration_query, (*quotas, user_id,))
                return
            else:
                raise (ValueError(f"User with id: {user_id} already exists."))

        moderator_registration_query = """
        INSERT INTO
            moderators (user_id, send_quota, edit_quota, delete_quota, consecutive_completed_weeks, active, vacation_days)
        VALUES
            (?, ?, ?, ?, 0, 1, 0);
        """
        self._execute_query(moderator_registration_query, (user_id, *quotas,))

    def set_quota(self, user_id: int, quotas: tuple[int, int, int]) -> None:
        """Edits the weekly quota for the given user in the object's database.

        Args:
            user_id (int): Discord id of the user to edit.
            quotas (tuple[int, int, int]): The new weekly quotas for the user.
        """
        moderator_edit_query = """
        UPDATE moderators
        SET
            send_quota = ?,
            edit_quota = ?,
            delete_quota = ?
        WHERE
            user_id == ?
        """
        self._execute_query(moderator_edit_query, (*quotas, user_id,))

    def set_all_quotas(self, quotas: tuple[int, int, int]) -> None:
        """Edits the weekly quota for all the users in the object's database.

        Args:
            quotas (tuple[int, int, int]): The new weekly quota for all users.
        """
        # make sure we don't change removed moderators
        moderator_edit_query = """
        UPDATE moderators
        SET
            send_quota = ?,
            edit_quota = ?,
            delete_quota = ?
        WHERE
            active == 1
        """
        self._execute_query(moderator_edit_query, (*quotas,))

    def set_consecutive_completed_weeks(
            self, user_id: int, new_value: int) -> None:
        """Sets the amount of consecutive completed weeks for the given user in the object's database.

        Args:
            user_id (int): Discord id of the user to edit.
            new_value (int): The new value to set consecutive_completed_weeks to.
        """
        moderator_edit_query = """
        UPDATE moderators
        SET
            consecutive_completed_weeks = ?
        WHERE
            user_id = ?
        """
        self._execute_query(moderator_edit_query, (new_value, user_id,))

    def increment_consecutive_completed_weeks(
            self, user_id: int, amount: int = 1) -> None:
        """Increments the amount consecutive completed weeks for the given user by the given amount in the object's database.

        Args:
            user_id (int): Discord id of the user to edit.
            amount (int, optional): The amount to increment the field with. Defaults to 1.
        """
        moderator_edit_query = """
        UPDATE moderators
        SET
            consecutive_completed_weeks = consecutive_completed_weeks + ?
        WHERE
            user_id = ?
        """
        self._execute_query(moderator_edit_query, (amount, user_id,))

    def set_vacation_days(self, user_id: int, new_value: int) -> None:
        """Sets the amount of vacation days for the given user in the object's database.

        Args:
            user_id (int): Discord id of the user to edit.
            new_value (int): The new value to set vacation_days to.
        """
        moderator_edit_query = """
        UPDATE moderators
        SET
            vacation_days = ?
        WHERE
            user_id = ?
        """
        self._execute_query(moderator_edit_query, (new_value, user_id,))

    def increment_vacation_days(self, user_id: int, amount: int = 1) -> None:
        """Increments the amount of vacation days for the given user by the given amount in the object's database.

        Args:
            user_id (int): Discord id of the user to edit.
            amount (int, optional): The amount to increment the field with. Defaults to 1.
        """
        moderator_edit_query = """
        UPDATE moderators
        SET
            vacation_days = vacation_days + ?
        WHERE
            user_id = ?
        """
        self._execute_query(moderator_edit_query, (amount, user_id,))

    def de_register_moderator(self, user_id: int) -> None:
        """Modifies a moderator entry to no longer be active, and no longer have any quotas to fill, given the id of a user to edit.

        Args:
            user_id (int): Discord id of the user to edit
        """
        moderator_de_registration_query = """
        UPDATE moderators
        SET
            active = 0,
            consecutive_completed_weeks = 0,
            send_quota = 0,
            edit_quota = 0,
            delete_quota = 0
        WHERE
            user_id = ?
        """
        self._execute_query(moderator_de_registration_query, (user_id,))

    def get_moderator(self, user_id: int) -> Moderator:
        """Returns a moderator given their discord user id.

        Args:
            user_id (int): Discord id of the user to get.

        Returns:
            Moderator: A moderator object containing all data pertaining to the user
        """
        moderator_get_query = """
        SELECT * FROM moderators
        WHERE
            user_id = ?
        """
        result = self._execute_read_query(
            moderator_get_query, (user_id,))

        if result:
            return Moderator(*result)
        return None

    def get_all_moderators(self) -> list[Moderator]:
        """Returns a list of all active moderators in the object's database

        Returns:
            list[Moderator]: List of Moderator objects
        """
        moderator_get_query = """
        SELECT * FROM moderators
        WHERE
            active = 1
        """
        result = self._execute_multiple_read_query(
            moderator_get_query)

        if result:
            return [Moderator(*mod) for mod in result]
        return []

    def get_all_inactive_moderators(self) -> list[Moderator]:
        """Returns a list of all inactive moderators in the object's database

        Returns:
            list[Moderator]: List of Moderator objects
        """
        moderator_get_query = """
        SELECT * FROM moderators
        WHERE
            active = 0
        """
        result = self._execute_multiple_read_query(
            moderator_get_query)

        if result:
            return [Moderator(*mod) for mod in result]
        return []


# -------------------------- ACTION HANDLING --------------------------

    def create_action(
            self,
            action_type: str,
            moderator_id: int,
            timestamp: int,
            channel_id: int,
            message_id: int = None) -> None:
        """Adds a new action to the object's database

        Args:
            action_type (str): Type of action, "sent", "edited" or "deleted".
            moderator_id (int): Discord ID of the moderator that executed the action.
            timestamp (int): Unix timestamp of when the action was executed.
            channel_id (int): Discord ID of the channel the action occured in.
            message_id (int, optional): Discord ID of the message the action is referencing. Defaults to None.
        """
        action_registration_query = """
        INSERT INTO
            actions (type, message_id, channel_id, mod_id, timestamp)
        VALUES
            (?, ?, ?, ?, ?)
        """
        self._execute_query(
            action_registration_query,
            (action_type,
             message_id,
             channel_id,
             moderator_id,
             timestamp))

    def get_all_actions(self, start_time: int, end_time: int,
                        moderator_id: int) -> list[Action]:
        """Returns a list of all action sent by the given moderator in the given timeframe.

        Args:
            start_time (int): Beginning of the timeframe (unix timestamp).
            end_time (int): End of the timeframe (unix timestamp).
            moderator_id (int): Id of the given moderator.

        Returns:
            list[Action]: A list containing Action objects.
        """
        action_get_query = """
        SELECT * FROM actions
        WHERE
            "timestamp"
        BETWEEN
            ?
        AND
            ?
        AND
            "mod_id" = ?
        """
        result = list(self._execute_multiple_read_query(
            action_get_query,
            (start_time, end_time, moderator_id,)))
        result_list = []

        if result:
            result = [list(entry) for entry in result]
            message_ids = [m.pop(2) for m in result]
            for i in range(0, len(result)):
                result_list.append(
                    Action(
                        *result[i],
                        message_id=message_ids[i]))

        return result_list

    def get_all_actions_of_type(
            self,
            start_time: int,
            end_time: int,
            moderator_id: int,
            type: str) -> list[Action]:
        """Returns a list of of all actions with the specified type by the given moderator in the given timeframe

        Args:
            start_time (int): Beginning of the timeframe (unix timestamp).
            end_time (int): End of the timeframe (unix timestamp).
            moderator_id (int): Id of the given moderator.
            type (str): a string containing the action type ("sent", "edited" or "deleted")

        Returns:
            list[Action]: A list containing all Action objects of the given type.
        """

        action_get_query = """
        SELECT * FROM actions
        WHERE "timestamp"
        BETWEEN
            ?
        AND
            ?
        AND
            "mod_id" = ?
        AND
            "type" = ?"""

        result = list(self._execute_multiple_read_query(
            action_get_query, (start_time, end_time, moderator_id, type,)))
        result_list = []

        if result:
            result = [list(entry) for entry in result]
            message_ids = [m.pop(2) for m in result]
            for i in range(0, len(result)):
                if result[i][1] == type:
                    result_list.append(
                        Action(
                            *result[i],
                            message_id=message_ids[i]))

        return result_list

    def get_amount_of_actions_by_type(
            self, start_time: int, end_time: int, moderator_id: int) -> tuple[int, int, int]:
        """Returns a tuple containing the amount of sent, edited and deleted messages by the given moderator in the given timeframe.
        Format is always (sent, edited, deleted)

        Args:
            start_time (int): Beginning of the timeframe (unix timestamp).
            end_time (int): End of the timeframe (unix timestamp).
            moderator_id (int): Id of the given moderator.

        Returns:
            tuple[int, int, int]: A tuple containg the amount of hits for each category.
        """
        return (
            len(
                self.get_all_actions_of_type(
                    start_time, end_time, moderator_id, "sent")),
            len(
                self.get_all_actions_of_type(
                    start_time, end_time, moderator_id, "edited")),
            len(
                self.get_all_actions_of_type(
                    start_time, end_time, moderator_id, "deleted")))


# ---------------------- VACATION WEEK HANDLING -----------------------


    def add_vacation_week(self, moderator_id: int, date: str) -> None:
        """Adds a new action to the object's database.

        Args:
            moderator_id (int): Discord ID of the moderator to bind the vacation to.
            date (str): The week that is being taken as vacation, format "YYYY-WW".
        """
        vacation_week_add_query = """
        INSERT INTO
            vacation_weeks (date, mod_id)
        VALUES
            (?,?);
        """
        self._execute_query(vacation_week_add_query, (date, moderator_id,))

    def remove_vacation_week(self, user_id: int, date: str) -> None:
        """Remove an action from the object's database given a user_id and date.

        Args:
            user_id (int): Discord ID of the moderator to bind the vacation to.
            date (str): The week that of the vacation, format "YYYY-WW".
        """
        vacation_week_remove_query = """
        DELETE FROM vacation_weeks
        WHERE
            date = ?
        AND
            mod_id = ?
        """
        self._execute_query(vacation_week_remove_query, (date, user_id,))

    def get_all_vacation_weeks(self, user_id: int) -> list[VacationWeek]:
        """Returns a list of all vacation weeks in the object's database.

        Args:
            user_id (int): Discord ID of the moderator to get the vacation from.

        Returns:
            list[VacationWeek]: List of all vacation weeks for the given user.
        """
        vacation_week_get_query = """
        SELECT * FROM vacation_weeks
        WHERE
            mod_id = ?
        """
        result = self._execute_multiple_read_query(
            vacation_week_get_query, (user_id,))

        if result:
            return [VacationWeek(*week) for week in result]
        return []

    def get_all_vacation_weeks_during_period(
            self,
            user_id: int,
            start_date: str,
            end_date: str) -> list[VacationWeek]:
        """Returns a list of all vacation weeks during a period in the object's database given a user_id and the time frame.

        Args:
            user_id (int): Discord ID of the moderator to get the vacation from.
            start_date (str): Beginning of the timeframe (format "YYYY-MM").
            end_date (str): End of the timeframe (format "YYYY-MM").

        Returns:
            list[VacationWeek]: List of all vacation weeks for the given user during the given time period.
        """
        vacation_week_get_query = """
        SELECT * FROM vacation_weeks
        WHERE
            date
        BETWEEN
            ?
        AND
            ?
        AND
            "mod_id" = ?
        """
        result = self._execute_multiple_read_query(
            vacation_week_get_query,
            (start_date,
             end_date,
             user_id,))
        if result:
            return [VacationWeek(*w) for w in result]
        return []

    def is_vacation_week(self, user_id: int, date: str) -> bool:
        """Checks if a given user has taken the given week as vacation.

        Args:
            user_id (int): Discord ID of the moderator the check vacation for.
            date (str): The week of the vacation to check, format "YYYY-WW".

        Returns:
            bool: If the given week was vacation for the given user.
        """
        vacation_week_check_query = """
        SELECT * FROM vacation_weeks
        WHERE
            mod_id = ?
        AND
            date = ?
        """
        if self._execute_read_query(
                vacation_week_check_query, (user_id, date,)):
            return True
        return False

    def amount_of_vacation_weeks(self, user_id: int) -> int:
        """Returns the number of total vacation weeks a user has taken.

        Args:
            user_id (int): Discord ID of the moderator to count vacation weeks for.

        Returns:
            int: The amount of total vacation weeks.
        """
        vacation_week_count_query = """
        SELECT * FROM vacation_weeks
        WHERE
            mod_id = ?
        """
        return len(self._execute_multiple_read_query(
            vacation_week_count_query, (user_id,)))

    def amount_of_vacation_weeks_during_period(
            self, user_id: int, start_date: str, end_date: str) -> int:
        """Returns the number of vacation weeks a user has taken between the given dates.

        Args:
            user_id (int): Discord ID of the moderator to count vacation weeks for.
            start_date (str): The beginning of the time period to check. Format "YYYY-WW".
            end_date (str): The end of the time period to check (inclusive). Format "YYYY-WW".

        Returns:
            int: The amount of vacation weeks during the period.
        """
        vacation_week_count_query = """
        SELECT * FROM vacation_weeks
        WHERE
            date
        BETWEEN
            ?
        AND
            ?
        AND
            "mod_id" = ?
        """
        return len(self._execute_multiple_read_query(
            vacation_week_count_query, (start_date, end_date, user_id,)))


# -------------------------- CONFIG HANDLING --------------------------


    def add_guild(self,
                  guild_id: int,
                  default_quotas: tuple[int,
                                        int,
                                        int],
                  mod_category_id: int = None,
                  last_mod_check: int = None,
                  time_between_checks: int = None) -> None:
        """Creates a new entry for the given guild in the database.

        Args:
            guild_id (int): The id of the guild.
            default_quotas (tuple[int, int, int]): The default quotas for new moderators.
            mod_category_id (int, optional): The id of the moderator category. Defaults to None.
            last_mod_check (int, optional): Unix timestamp of last time the moderators were checked. Defaults to None.
            time_between_checks (int, optional): Amount of seconds we should wait between checking the moderators. Defaults to None.
        """

        guild_add_query = """
        INSERT INTO
            config(guild_id, default_quotas, mod_category_id, last_mod_check, time_between_checks)
        VALUES
            (?, ?, ?, ?, ?);
        """
        self._execute_query(guild_add_query, (guild_id, "".join(map(
            str, default_quotas)), mod_category_id, last_mod_check, time_between_checks,))

    def set_mod_category_id(self, guild_id: int, mod_category_id: int) -> None:
        """Sets the mod category ID in the given guild to the given value.

        Args:
            guild_id (int): The id of the guild to update the mod category id in.
            mod_category_id (int): The new id.
        """
        mod_category_id_edit_query = """
        UPDATE config
        SET
            mod_category_id = ?
        WHERE
            guild_id = ?
        """
        self._execute_query(mod_category_id_edit_query,
                            (mod_category_id, guild_id,))

    def set_last_mod_check(self, guild_id: int, last_mod_check: int) -> None:
        """Sets the last_mod_check timestamp in the given guild to the given value.

        Args:
            guild_id (int): The id of the guild to update the timestamp in.
            last_mod_check (int): The new timestamp.
        """
        last_mod_check_edit_query = """
        UPDATE config
        SET
            last_mod_check = ?
        WHERE
            guild_id = ?
        """
        self._execute_query(last_mod_check_edit_query,
                            (last_mod_check, guild_id,))

    def set_time_between_checks(
            self,
            guild_id: int,
            time_between_checks: int) -> None:
        """Sets time_between_checks in the given guild to the given value.

        Args:
            guild_id (int): The id of the guild to update the values in.
            time_between_checks (int): The new value.
        """
        time_between_checks_edit_query = """
        UPDATE config
        SET
            time_between_checks = ?
        WHERE
            guild_id = ?
        """
        self._execute_query(time_between_checks_edit_query,
                            (time_between_checks, guild_id,))

    def set_default_quotas(self, guild_id: int,
                           default_quotas: tuple[int, int, int]) -> None:
        """Sets the default quota for new moderators.

        Args:
            guild_id (int): The id of the guild to update the value for.
            default_quotas (tuple): The new values.
        """
        default_quotas_edit_query = """
        UPDATE config
        SET
            default_quotas = ?
        WHERE
            guild_id = ?
        """
        self._execute_query(default_quotas_edit_query,
                            (",".join(map(str, default_quotas)), guild_id,))

    def get_guild(self, guild_id: int) -> Guild:
        """Gets a guild given it's id.

        Args:
            guild_id (int): Discord id of the guild to get.

        Returns:
            Guild: A Guild option with all the config info from the guild.
        """
        guild_get_query = """
        SELECT * FROM config
        WHERE
            guild_id = ?
        """
        result = self._execute_read_query(guild_get_query, (guild_id,))
        if result:
            return Guild(*result)
        return None

    def get_all_guilds(self) -> list[Guild]:
        """Gets all guilds in the object's database.

        Returns:
            list[Guild]: A list of all guilds in the database as Guild objects.
        """
        guild_get_query = """
        SELECT * FROM config
        """
        result = self._execute_multiple_read_query(guild_get_query)
        if result:
            return [Guild(*guild) for guild in result]
        return []


if __name__ == "__main__":
    DB = DBHandler("db.sqlite")

    stickies_table_query = """
    CREATE TABLE IF NOT EXISTS stickies (
        "channel_id" INTEGER PRIMARY KEY,
        "message_id" INTEGER UNIQUE NOT NULL
    );
    """
    DB._execute_query(stickies_table_query)

    moderator_table_query = """
    CREATE TABLE IF NOT EXISTS moderators (
        "user_id" INTEGER PRIMARY KEY,
        "send_quota" INTEGER NOT NULL,
        "edit_quota" INTEGER NOT NULL,
        "delete_quota" INTEGER NOT NULL,
        "consecutive_completed_weeks" INTEGER NOT NULL,
        "vacation_days" INTEGER NOT NULL,
        "active" INTEGER NOT NULL
    );
    """
    DB._execute_query(moderator_table_query)

    action_table_query = """
    CREATE TABLE IF NOT EXISTS actions (
        "id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "type" TEXT NOT NULL,
        "message_id" INTEGER,
        "channel_id" INTEGER NOT NULL,
        "mod_id" INTEGER REFERENCES moderators NOT NULL,
        "timestamp" INTEGER NOT NULL
    );
    """
    DB._execute_query(action_table_query)

    vacation_table_query = """
    CREATE TABLE IF NOT EXISTS vacation_weeks (
        "date" TEXT UNIQUE NOT NULL,
        "mod_id" INTEGER REFERENCES moderators NOT NULL
    )"""
    DB._execute_query(vacation_table_query)

    config_table_query = """
    CREATE TABLE IF NOT EXISTS config (
        "guild_id" INTEGER PRIMARY KEY,
        "mod_category_id" INTEGER,
        "last_mod_check" INTEGER,
        "time_between_checks" INTEGER,
        "default_quotas" TEXT NOT NULL
    );"""
    DB._execute_query(config_table_query)
