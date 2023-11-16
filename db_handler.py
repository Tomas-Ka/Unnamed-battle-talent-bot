import sqlite3
from sqlite3 import Error
from typing import List, Tuple
from helpers import Action, Moderator, StickyMessage, VacationWeek


class DBHandler():
    def __init__(self, path):
        # TODO docstring
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys = ON;")
        print("Connection to SQLite DB successful")

    def _execute_query(self, query: str, vars: Tuple = ()) -> None:
        """Execute the given query with the object's database.

        Args:
            query (str): The query string.
            vars (Tuple, optional): The vars to replace the spots in the query string. Defaults to ()
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, vars)
        except Error as e:
            print(f"The error '{e}' occurred")
        self.connection.commit()

    def _execute_read_query(self, query: str, vars: Tuple = ()) -> Tuple:
        """Executes the given query with the object's database, returning
        a single Tuple. Is used for reading from the DB.

        Args:
            query (str): The string to query the database with.
            vars (Tuple, optional): The vars to replace the spots in the query string. Defaults to ()

        Returns:
            Tuple: A Touple containing the data at the found row.
        """
        cursor = self.connection.cursor()
        result = None
        try:
            cursor.execute(query, vars)
            result = cursor.fetchone()
            return result
        except Error as e:
            print(f"The error '{e}' occurred")

    def _execute_multiple_read_query(self, query: str) -> List[Tuple]:
        """Executes the given query with the object's databse, returning
        a list of Tuples. Is used for reading from the database

        Args:
            query (str): The string to query the database with.

        Returns:
            List[Tuple]: a list containing all the data found from the query.
        """
        cursor = self.connection.cursor()
        result = None
        try:
            cursor.execute(query)
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
        return StickyMessage(
            *self._execute_read_query(
                sticky_query, (channel_id,))[1])

    def get_all_stickies(self) -> List[StickyMessage]:
        """Returns a list of all stickies in the database.

        Returns:
            List[StickyMessage]: A list of StickyMessage objects
        """
        sticky_query = """
        SELECT * FROM stickies
        """
        return [
            StickyMessage(
                *sticky) for sticky in self._execute_multiple_read_query(sticky_query)]


# --------------------------- MOD HANDLING ----------------------------

    def register_moderator(
            self, user_id: int, quotas: Tuple[int, int, int]) -> None:
        """Adds a new moderator to the object's database.

        Args:
            user_id (int): Discord id of the user.
            quotas (Tuple[int, int, int]): The quotas the user should reach weekly.
        """
        # There is most certainly a smarter way to do this, but it works...
        mod_test = self.get_moderator(user_id)
        if mod_test:
            if mod_test[5] == 0:
                moderator_registration_query = """
                UPDATE moderators
                SET
                    send_quota = ?
                    edit_quota = ?
                    delete_quota = ?
                    active = 1
                WHERE
                    user_id = ?
                """
                self._execute_query(
                    moderator_registration_query, (*quotas, user_id,))
                return

        moderator_registration_query = """
        INSERT INTO
            moderators (user_id, send_quota, edit_quota, delete_quota, consecutive_completed_weeks, active, vacation_days)
        VALUES
            (?, ?, ?, ?, 0, 1, 0);
        """
        self._execute_query(moderator_registration_query, (user_id, *quotas,))

    def set_quota(self, user_id: int, quotas: Tuple[int, int, int]) -> None:
        """Edits the weekly quota for the given user in the object's database.

        Args:
            user_id (int): Discord id of the user to edit.
            quotas (Tuple[int, int, int]): The new weekly quotas for the user.
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

    def set_all_quotas(self, quotas: Tuple[int, int, int]) -> None:
        """Edits the weekly quota for all the users in the object's database.

        Args:
            quotas (Tuple[int, int, int]): The new weekly quota for all users.
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
            active = 0
            consecutive_completed_weeks = 0
            vacation_days = 0
            send_quota = 0
            edit_quota = 0
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
        return Moderator(
            *
            self._execute_read_query(
                moderator_get_query,
                (user_id,
                 )))

    def get_all_moderators(self) -> List[Moderator]:
        """Returns a list of all moderators in the object's database

        Returns:
            List[Moderator]: List of Moderator objects
        """
        moderator_get_query = """
        SELECT * FROM moderators
        """
        return [
            Moderator(
                *mod) for mod in self._execute_multiple_read_query(moderator_get_query)]


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

    def get_actions(self, start_time: int, end_time: int,
                    moderator_id: int) -> List[Action]:
        """Returns a list of all action sent by the given moderator in the given timeframe.

        Args:
            start_time (int): Beginning of the timeframe (unix timestamp).
            end_time (int): End of the timeframe (unix timestamp).
            moderator_id (int): Id of the given moderator.

        Returns:
            List[Action]: A list containing a tuple of action type (sent, edited or deleted), the message id and the channel id.
        """
        pass
    # TODO; finish


# ---------------------- VACATION WEEK HANDLING -----------------------

    def add_vacation_week(self, user_id: int, date: str) -> None:
        vacation_week_add_query = """
        INSERT INTO
            vacation_weeks (date, mod_id)
        VALUES
            (?,?);
        """
        self._execute_query(vacation_week_add_query, (date, user_id,))

    def remove_vacation_week(self, user_id: int, date: str) -> None:
        vacation_week_remove_query = """
        DELETE FROM vacation_weeks
        WHERE
            date = ?,
            user_id = ?
        """
        self._execute_query(vacation_table_query, (user_id, date,))

    def is_vacation_week(self, user_id: int, date: str) -> bool:
        return True
        # TODO; write

    def amount_of_vacation_weeks(self, user_id: int) -> int:
        return 0
        # TODO; write


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
        "type" STRING NOT NULL,
        "message_id" INTEGER,
        "channel_id" INTEGER NOT NULL,
        "mod_id" INTEGER REFERENCES moderators NOT NULL,
        "timestamp" INTEGER NOT NULL
    );
    """
    DB._execute_query(action_table_query)

    vacation_table_query = """
    CREATE TABLE IF NOT EXISTS vacation_weeks (
        "date" STRING UNIQUE NOT NULL,
        "mod_id" INTEGER REFERENCES moderators NOT NULL
    )"""
    DB._execute_query(vacation_table_query)
