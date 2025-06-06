import smtplib
import ssl
import certifi
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.template.loader import render_to_string
from django.conf import settings

def send_password_reset_email(email, reset_link):
    sender_email = settings.EMAIL_HOST_USER
    receiver_email = email
    site_name = "127.0.0.1:8000"

    subject = render_to_string('password_reset_subject.txt', {'site_name': site_name}).strip()
    body = render_to_string('password_reset_email.html', {'site_name': site_name, 'reset_link': reset_link})

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        context = ssl.create_default_context(cafile=certifi.where())  # Use certifi certificates
        server.starttls(context=context)
        server.login(sender_email, settings.EMAIL_HOST_PASSWORD)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"Email sent successfully to {receiver_email}")
    except Exception as e:
        print(f"Error sending email to {receiver_email}: {e}")
        raise  # Raise the exception so the view fails visibly
    finally:
        server.quit()