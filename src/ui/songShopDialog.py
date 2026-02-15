# src/ui/songShopDialog.py
import logging
from PyQt6.QtCore import QByteArray, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout, QWidget)

logger = logging.getLogger('vibe_manager')


class SongShopDialog(QDialog):
    # Signal emitted when a purchase is detected so the main window can trigger a download
    purchase_detected = pyqtSignal()

    def __init__(self, parent, session):
        super().__init__(parent)
        self.setWindowTitle("Vibe Song Shop")
        self.resize(1024, 768)
        self.session = session
        self.home_url = "https://www.karaoke-version.com/karaoke/"

        self.layout = QVBoxLayout(self)

        # Initialize Web Engine
        self.web_view = QWebEngineView()

        # Sync cookies from the requests session to the WebEngine profile
        self.sync_cookies()

        self.layout.addWidget(self.web_view)

        # Bottom control layout
        self.controls_layout = QHBoxLayout()

        # New Search Button (Left)
        self.new_search_btn = QPushButton("New Search")
        self.new_search_btn.clicked.connect(self.go_home)
        self.controls_layout.addWidget(self.new_search_btn)

        self.controls_layout.addStretch()

        # Close Button (Right)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        self.controls_layout.addWidget(self.close_btn)

        self.layout.addLayout(self.controls_layout)

        # Connect URL changes to detection logic
        self.web_view.urlChanged.connect(self.on_url_changed)

        # Load the initial page
        self.web_view.setUrl(QUrl(self.home_url))

    def sync_cookies(self):
        """Transfers cookies from the authenticated requests session to the WebEngine."""
        try:
            profile = QWebEngineProfile.defaultProfile()
            cookie_store = profile.cookieStore()
            cookie_store.deleteAllCookies()  # Start fresh

            for cookie in self.session.cookies:
                # Prepare cookie parameters
                name = QByteArray(cookie.name.encode())
                value = QByteArray(cookie.value.encode())

                # Create QNetworkCookie
                q_cookie = QNetworkCookie(name, value)

                # Set Domain (Important: requests might store it as 'karaoke-version.com' or '.karaoke-version.com')
                # We ensure it matches what the browser expects.
                domain = cookie.domain if cookie.domain else ".karaoke-version.com"
                q_cookie.setDomain(domain)

                q_cookie.setPath(cookie.path if cookie.path else "/")
                q_cookie.setSecure(cookie.secure)
                # HttpOnly is often handled by attributes in requests, but QNetworkCookie has a setter
                if cookie.has_nonstandard_attr('HttpOnly') or cookie.has_nonstandard_attr('httponly'):
                    q_cookie.setHttpOnly(True)

                cookie_store.setCookie(q_cookie)

            logger.debug("Cookies synchronized to WebEngine.")
        except Exception as e:
            logger.error(f"Failed to sync cookies: {e}")

    def go_home(self):
        self.web_view.setUrl(QUrl(self.home_url))

    def on_url_changed(self, url: QUrl):
        url_str = url.toString()
        logger.debug(f"Song Shop URL changed: {url_str}")

        # Check for purchase confirmation URL
        # Example: https://www.karaoke-version.com/misc/buyok.html?order_ref=KV36977492
        if "/misc/buyok.html" in url_str and "order_ref=" in url_str:
            logger.info("Purchase detected in Song Shop.")
            self.handle_purchase()

    def handle_purchase(self):
        # Notify main window to start downloading
        self.purchase_detected.emit()

        reply = QMessageBox.question(self, "Purchase Detected",
            "Purchase detected! The song will be downloaded automatically.\n\nDo you wish to continue shopping?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.go_home()
        else:
            self.close()
