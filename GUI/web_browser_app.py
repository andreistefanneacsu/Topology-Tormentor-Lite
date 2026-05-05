from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QMessageBox, QGridLayout, QFrame, QTabWidget, QComboBox, QCheckBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from simulator import NetworkSimulator

def _field(text="", password=False, width=220):
    f = QLineEdit(text)
    f.setMinimumSize(150, 24)
    if password:
        f.setEchoMode(QLineEdit.EchoMode.Password)
    f.setStyleSheet(
        "background:#fff; border:1px solid #aaa; border-radius:3px;"
        "padding:4px 6px; font-size:12px;"
    )
    return f


def _combo(options, current=""):
    c = QComboBox()
    c.addItems(options)
    if current in options:
        c.setCurrentText(current)
    c.setMinimumSize(150, 24)
    c.setStyleSheet(
        "background:#fff; border:1px solid #aaa; border-radius:3px;"
        "padding:3px 6px; font-size:12px;"
    )
    return c


def _section_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "font-weight:bold; font-size:12px; color:#fff;"
        "background:#6b8cba; padding:4px 8px;"
        "border-radius:3px; margin-top:8px;"
    )
    return lbl


def _make_form(rows):
    """rows: list of (label_text, widget)"""
    w = QWidget()
    form = QGridLayout(w)
    form.setSpacing(10)
    for i, (label_text, widget) in enumerate(rows):
        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size:12px;")
        form.addWidget(lbl, i, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.addWidget(widget, i, 1)
    return w

class WebBrowserWidget(QWidget):
    def __init__(self, host_device, all_devices, all_links):
        super().__init__()
        self.host = host_device
        self.simulator = NetworkSimulator(all_devices, all_links)
        self.current_router = None
        self._logged_in = False

        self.resize(850, 700)
        self.setWindowTitle("Web Browser")
        self.setStyleSheet(
            "background:#f0f0f0; color:#222; font-family:Tahoma,Arial,sans-serif; font-size:12px;"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bar = QFrame()
        bar.setStyleSheet("background:#dce3ec; border-bottom:2px solid #7f9db9;")
        bar.setFixedHeight(40)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        bar_layout.setSpacing(6)

        bar_layout.addWidget(QLabel("Address:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("e.g. 192.168.0.1")
        self.url_input.setStyleSheet(
            "background:#fff; border:1px solid #7f9db9; padding:3px 6px; border-radius:2px;"
        )
        self.url_input.returnPressed.connect(self.navigate)
        bar_layout.addWidget(self.url_input)

        go_btn = QPushButton("Go")
        go_btn.setFixedWidth(40)
        go_btn.setStyleSheet(
            "background:#e8edf3; border:1px solid #7f9db9; padding:3px 8px; border-radius:2px;"
        )
        go_btn.clicked.connect(self.navigate)
        bar_layout.addWidget(go_btn)

        root.addWidget(bar)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.content_area, stretch=1)

        self._show_welcome()

    def navigate(self):
        url = self.url_input.text().strip()
        if not url:
            return

        for prefix in ("https://", "http://"):
            if url.startswith(prefix):
                url = url[len(prefix):]

        target_ip = url

        import re
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target_ip):
            dns_ip = self.host.config.get("dns-server", "")
            if not dns_ip:
                self._show_error("Cannot resolve hostname: no DNS server configured.")
                return
            ok, _, dns_dev, _ = self.simulator._route_packet(self.host, dns_ip)
            if not ok or dns_dev.type != "Server":
                self._show_error("Cannot reach DNS server.")
                return
            resolved = dns_dev.resolve_dns(target_ip)
            if not resolved:
                self._show_error(f"Could not resolve hostname: {target_ip}")
                return
            target_ip = resolved

        ok, msg, target_dev, _ = self.simulator._route_packet(self.host, target_ip)

        if not ok:
            self._show_error(f"Cannot reach {target_ip}:\n{msg}")
            return

        if target_dev.type == "WirelessRouter":
            self.current_router = target_dev
            self._logged_in = False
            self._show_login()
        else:
            self._show_error(
                f"Connected to {target_dev.name}, but this device does not serve a web page."
            )

    def _clear(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_welcome(self):
        self._clear()
        lbl = QLabel("Type an IP address in the address bar to navigate.\n\nExample: 192.168.0.1")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color:#888; font-size:15px; margin-top:60px;")
        self.content_layout.addWidget(lbl)

    def _show_error(self, msg):
        self._clear()
        lbl = QLabel(msg)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color:#c00; font-size:13px; margin:60px 30px;")
        self.content_layout.addWidget(lbl)

    def _show_login(self):
        self._clear()

        outer = QWidget()
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        ov = QVBoxLayout(outer)
        ov.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setFixedWidth(340)
        card.setStyleSheet(
            "background:#fff; border:1px solid #b0b8c8; border-radius:6px;"
        )
        cv = QVBoxLayout(card)
        cv.setContentsMargins(28, 24, 28, 24)
        cv.setSpacing(14)

        header = QLabel("Router Login")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            "font-size:18px; font-weight:bold; color:#1a4a8a;"
            "padding-bottom:6px; border-bottom:1px solid #dde;"
        )
        cv.addWidget(header)

        sub = QLabel(f"<small>{self.current_router.name} — 192.168.0.1</small>")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:#888; margin-bottom:4px;")
        cv.addWidget(sub)

        form = QGridLayout()
        form.setSpacing(10)

        self._login_user = _field()
        self._login_pass = _field(password=True)

        form.addWidget(QLabel("Username:"), 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.addWidget(self._login_user, 0, 1)
        form.addWidget(QLabel("Password:"), 1, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.addWidget(self._login_pass, 1, 1)
        cv.addLayout(form)

        login_btn = QPushButton("Log In")
        login_btn.setFixedHeight(32)
        login_btn.setStyleSheet(
            "background:#1a4a8a; color:#fff; font-weight:bold; font-size:13px;"
            "border-radius:4px; border:none; margin-top:6px;"
        )
        login_btn.clicked.connect(self._do_login)
        self._login_pass.returnPressed.connect(self._do_login)
        self._login_user.returnPressed.connect(self._login_pass.setFocus)
        cv.addWidget(login_btn)

        hint = QLabel("Default credentials: admin / admin")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color:#aaa; font-size:10px; margin-top:4px;")
        cv.addWidget(hint)

        ov.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(outer)

    def _do_login(self):
        u = self._login_user.text().strip()
        p = self._login_pass.text().strip()
        if self.current_router.check_login(u, p):
            self._logged_in = True
            self._show_router_ui()
        else:
            QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")
            self._login_pass.clear()
            self._login_pass.setFocus()

    def _show_router_ui(self):
        self._clear()

        r = self.current_router

        root = QWidget()
        rv = QVBoxLayout(root)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        banner = QLabel(f"  Wireless Router  ·  {r.name}")
        banner.setFixedHeight(36)
        banner.setStyleSheet(
            "background:#1a4a8a; color:#fff; font-size:14px; font-weight:bold;"
            "padding-left:14px;"
        )
        rv.addWidget(banner)

        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabWidget::pane { border:1px solid #b0b8c8; background:#f7f8fa; }"
            "QTabBar::tab { background:#dce3ec; border:1px solid #b0b8c8; padding:6px 18px;"
            "  border-bottom:none; border-top-left-radius:4px; border-top-right-radius:4px; }"
            "QTabBar::tab:selected { background:#f7f8fa; font-weight:bold; }"
        )

        tabs.addTab(self._tab_setup(r), "Setup")
        tabs.addTab(self._tab_wireless(r), "Wireless")
        tabs.addTab(self._tab_administration(r), "Administration")

        rv.addWidget(tabs)
        self.content_layout.addWidget(root)

    def _tab_setup(self, r):
        page = QWidget()
        pv = QVBoxLayout(page)
        pv.setContentsMargins(16, 16, 16, 16)
        pv.setSpacing(10)

        pv.addWidget(_section_label("Internet Setup"))

        self._internet_type = _combo(["DHCP", "Static IP", "PPPoE"], r.internet_connection_type)
        wan_ip = getattr(r.get_internet_port(), 'ip', "")
        wan_sub = getattr(r.get_internet_port(), 'subnet', "")
        wan_gw = r.config.get("wan_gateway", "")
        wan_dns = r.config.get("wan_dns", "")
        
        self._wan_ip = _field(wan_ip)
        self._wan_subnet = _field(wan_sub)
        self._wan_gw = _field(wan_gw)
        self._wan_dns = _field(wan_dns)

        pv.addWidget(_make_form([
            ("Internet Connection Type:", self._internet_type),
            ("IP Address:", self._wan_ip),
            ("Subnet Mask:", self._wan_subnet),
            ("Default Gateway:", self._wan_gw),
            ("DNS Server:", self._wan_dns),
        ]))

        self._internet_type.currentTextChanged.connect(self._toggle_wan_fields)
        self._toggle_wan_fields(r.internet_connection_type)

        pv.addWidget(_section_label("Router IP (LAN)"))

        self._lan_ip = _field(r.get_lan_ip())
        self._lan_subnet = _field(r.interfaces.get("Ethernet 1").subnet if r.interfaces.get("Ethernet 1") else "255.255.255.0")

        pv.addWidget(_make_form([
            ("Router IP Address:", self._lan_ip),
            ("Subnet Mask:", self._lan_subnet),
        ]))

        pv.addWidget(_section_label("DHCP Server"))

        self._dhcp_enabled = QCheckBox("Enable DHCP Server")
        self._dhcp_enabled.setChecked(r.dhcp_enabled)
        self._dhcp_start = _field(r.dhcp_start)
        self._dhcp_end = _field(r.dhcp_end)

        pv.addWidget(self._dhcp_enabled)
        pv.addWidget(_make_form([
            ("Start IP Address:", self._dhcp_start),
            ("End IP Address:", self._dhcp_end),
        ]))

        pv.addStretch()
        pv.addWidget(self._save_btn(self._save_setup), alignment=Qt.AlignmentFlag.AlignRight)
        return page

    def _toggle_wan_fields(self, ctype):
        disabled = (ctype == "DHCP")
        for f in [self._wan_ip, self._wan_subnet]:
            f.setEnabled(not disabled)
            f.setStyleSheet(
                "background:#e0e0e0; border:1px solid #aaa; border-radius:3px; padding:4px 6px; font-size:12px; color:#888;" if disabled else 
                "background:#fff; border:1px solid #aaa; border-radius:3px; padding:4px 6px; font-size:12px;"
            )
        for f in [self._wan_gw, self._wan_dns]:
            f.setEnabled(not disabled)
            f.setStyleSheet(
                "background:#e0e0e0; border:1px solid #aaa; border-radius:3px; padding:4px 6px; font-size:12px; color:#888;" if disabled else 
                "background:#fff; border:1px solid #aaa; border-radius:3px; padding:4px 6px; font-size:12px;"
            )

    def _save_setup(self):
        r = self.current_router
        new_lan_ip = self._lan_ip.text().strip()
        new_lan_sub = self._lan_subnet.text().strip()

        if new_lan_ip:
            r.set_lan_ip(new_lan_ip, new_lan_sub or "255.255.255.0")

        wan = r.get_internet_port()
        if wan:
            wan.ip = self._wan_ip.text().strip()
            wan.subnet = self._wan_subnet.text().strip()
            
        r.config["wan_gateway"] = self._wan_gw.text().strip()
        r.config["wan_dns"] = self._wan_dns.text().strip()

        r.internet_connection_type = self._internet_type.currentText()
        r.dhcp_enabled = self._dhcp_enabled.isChecked()
        r.dhcp_start = self._dhcp_start.text().strip()
        r.dhcp_end = self._dhcp_end.text().strip()

        QMessageBox.information(self, "Saved", "Setup settings saved.")

    def _tab_wireless(self, r):
        page = QWidget()
        pv = QVBoxLayout(page)
        pv.setContentsMargins(16, 16, 16, 16)
        pv.setSpacing(10)

        pv.addWidget(_section_label("Basic Wireless Settings"))

        self._ssid = _field(r.ssid)
        self._wifi_security = _combo(
            ["Disabled", "WEP", "WPA-Personal", "WPA2-Personal"],
            r.wifi_security
        )
        self._wifi_pass = _field(r.wifi_password, password=False)

        pv.addWidget(_make_form([
            ("Network Name (SSID):", self._ssid),
            ("Security Mode:", self._wifi_security),
            ("Passphrase:", self._wifi_pass),
        ]))

        pv.addStretch()
        pv.addWidget(self._save_btn(self._save_wireless), alignment=Qt.AlignmentFlag.AlignRight)
        return page

    def _save_wireless(self):
        r = self.current_router
        r.ssid = self._ssid.text().strip()
        r.wifi_security = self._wifi_security.currentText()
        r.wifi_password = self._wifi_pass.text().strip()
        QMessageBox.information(self, "Saved", "Wireless settings saved.")

    def _tab_administration(self, r):
        page = QWidget()
        pv = QVBoxLayout(page)
        pv.setContentsMargins(16, 16, 16, 16)
        pv.setSpacing(10)

        pv.addWidget(_section_label("Router Access"))

        self._admin_user = _field(r.admin_username)
        self._admin_pass = _field(r.admin_password, password=True)
        self._admin_pass_confirm = _field("", password=True)

        pv.addWidget(_make_form([
            ("Router Username:", self._admin_user),
            ("Router Password:", self._admin_pass),
            ("Re-enter Password:", self._admin_pass_confirm),
        ]))

        pv.addStretch()
        pv.addWidget(self._save_btn(self._save_administration), alignment=Qt.AlignmentFlag.AlignRight)
        return page

    def _save_administration(self):
        r = self.current_router
        p1 = self._admin_pass.text().strip()
        p2 = self._admin_pass_confirm.text().strip()

        if p1 != p2:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return

        r.admin_username = self._admin_user.text().strip() or r.admin_username
        r.admin_password = p1 or r.admin_password
        QMessageBox.information(self, "Saved", "Administration settings saved.")

    def _save_btn(self, handler):
        btn = QPushButton("Save Settings")
        btn.setFixedHeight(30)
        btn.setFixedWidth(130)
        btn.setStyleSheet(
            "background:#1a4a8a; color:#fff; font-weight:bold; font-size:12px;"
            "border-radius:4px; border:none;"
        )
        btn.clicked.connect(handler)
        return btn
