"""
Module for sending emails.

This module provides a class for sending emails using SMTP.
It includes functionality for composing emails, attaching files, and sending emails.
"""

import os

# from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPServerDisconnected

import html2text
from dotenv import load_dotenv

from commons.src.log_helper import logger

load_dotenv()


class EmailHelper:
    """
    Class for sending emails.

    This class provides a convenient way to send emails using SMTP.
    It includes functionality for composing emails, attaching files, and sending emails.
    """

    def __init__(self, email_address) -> None:
        self.__email = email_address
        self.__smtp_server = None
        self.__msg = None
        self.__set_smptp_server()

    def __set_smptp_server(self):
        mail_username = os.environ.get("MAIL_USERNAME")
        mail_pass = str(os.environ.get("MAIL_PASS"))
        print("mail_username", mail_username)
        print("mail_pass", mail_pass)

        self.__smtp_server = SMTP_SSL("email-smtp.ap-south-1.amazonaws.com", 465)
        self.__smtp_server.login(mail_username, mail_pass)
        logger.info("SMTP session created for %s", mail_username)

    def __set_message(self, subject, html_content):
        # self.__msg = EmailMessage()
        self.__msg = MIMEMultipart("alternative")
        self.__msg["Subject"] = subject
        self.__msg["From"] = os.environ.get("MAIL_FROM")
        self.__msg["To"] = self.__email

        # Generate plain text from HTML
        h = html2text.HTML2Text()
        h.ignore_links = False
        plain_text = h.handle(html_content)

        part1 = MIMEText(plain_text, "plain")
        part2 = MIMEText(html_content, "html")

        self.__msg.attach(part1)
        self.__msg.attach(part2)

    def __del__(self):
        logger.info("Closing SMTP session..")
        try:
            self.__smtp_server.quit()
        except SMTPServerDisconnected as e:
            print(1)
            logger.exception(str(e))

    def send_candidate_invite(self, email_body):
        """
        Send a candidate invite to the specified email address.

        Parameters:
            email_body (str): The HTML content of the email to be sent.

        Returns:
            None
        """
        self.__set_message("Candidate Invite", email_body)
        # self.__msg.set_content(email_body)
        logger.debug("Sending candidate invite to %s..", self.__email)
        self.__smtp_server.send_message(self.__msg)
        logger.info("Candidate invite sent to %s", self.__email)
