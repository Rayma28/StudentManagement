import ssl
import certifi
from django.core.mail.backends.smtp import EmailBackend as BaseEmailBackend

class CustomEmailBackend(BaseEmailBackend):
    def open(self):
        if self.connection:
            return False

        try:
            # Create the SMTP connection using host and port
            self.connection = self.connection_class(self.host, self.port)
            # Create an SSL context that uses certifi's certificates
            context = ssl.create_default_context(cafile=certifi.where())
            # Enable TLS with the custom context
            if self.use_tls:
                self.connection.starttls(context=context)
            # Log in to the SMTP server if credentials are provided
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise
            return False

    def close(self):
        if self.connection is not None:
            try:
                self.connection.quit()
            except Exception:
                if not self.fail_silently:
                    raise
            finally:
                self.connection = None