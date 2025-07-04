"""reports.py

This module contains functions and classes for generating and managing reports in the reporting service.
"""

from datetime import datetime, timedelta

from commons import DBEnterExitMixin, InterviewStatus, logger
from interview import InterviewORM


class Reports(DBEnterExitMixin):
    """
    This class provides methods for generating and managing reports in the reporting service.
    """

    def __init__(self):
        self._db_helper = None

    # def get_dashboard(self):
    #     return Admin(self.user_id).get_dashboard()

    def get_completed_interviews_counts_by_days(self, duration: str) -> dict:
        """
        Fetches the completed interviews counts for the given duration.

        Args:
            duration (str): The duration for which to fetch the completed interviews counts.

        Returns:
            dict: A dictionary containing the completed interviews counts.
        """
        logger.info("Fetching completed interviews counts for %s days...", duration)
        days = int(duration.replace(" Days", ""))

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Create a dictionary with all dates initialized to 0
        interview_counts = {
            (start_date.date() + timedelta(days=i)).strftime("%d-%b-%Y"): 0
            for i in range(days)
        }
        with self:
            interviews = (
                self._db_session.query(InterviewORM)
                .filter(InterviewORM.status == InterviewStatus.COMPLETED.value)
                .filter(InterviewORM.interview_datetime >= start_date)
                .filter(InterviewORM.interview_datetime <= end_date)
                .all()
            )
            for interview in interviews:
                if interview.interview_datetime:
                    key = interview.interview_datetime.date().strftime("%d-%b-%Y")
                    if key in interview_counts:
                        interview_counts[key] += 1
        return [
            {"interview_date": i_date, "completed_count": count}
            for i_date, count in sorted(interview_counts.items())
        ]

    def get_completed_interviews_counts_by_month(self, duration: str) -> dict:
        """
        Fetches the completed interviews counts for the given duration.

        Args:
            duration (str): The duration for which to fetch the completed interviews counts.

        Returns:
            dict: A dictionary containing the completed interviews counts.
        """
        logger.info("Fetching completed interviews counts for %s...", duration)
        months = int(duration.replace(" Months", ""))

        end_date = datetime.now()
        # Set start_date to the first day of the month 'months' ago
        start_month = (end_date.month - months + 1) % 12 or 12
        start_year = (
            end_date.year if end_date.month - months + 1 > 0 else end_date.year - 1
        )
        start_date = datetime(start_year, start_month, 1)

        # Prepare month keys in abbreviated month name and 2-digit year format
        month_keys = []
        for i in range(months):
            month = (start_date.month + i - 1) % 12 + 1
            year = start_date.year + ((start_date.month + i - 1) // 12)
            month_keys.append(
                f"{datetime.strptime(str(month), '%m').strftime('%b')}-{year % 100:02d}"
            )
        interview_counts = {k: 0 for k in month_keys}

        with self:
            interviews = (
                self._db_session.query(InterviewORM)
                .filter(InterviewORM.status == InterviewStatus.COMPLETED.value)
                .filter(InterviewORM.interview_datetime >= start_date)
                .filter(InterviewORM.interview_datetime <= end_date)
                .all()
            )
            for interview in interviews:
                if interview.interview_datetime:
                    month_key = interview.interview_datetime.strftime("%b-%y")
                    if month_key in interview_counts:
                        interview_counts[month_key] += 1
            return [
                {
                    "interview_date": month,
                    "completed_count": count,
                }
                for month, count in sorted(interview_counts.items())
            ]


if __name__ == "__main__":
    reports = Reports()
    # print(reports.get_completed_interviews_counts_by_days(duration="30 Days"))
    print(reports.get_completed_interviews_counts_by_month(duration="3 Months"))
