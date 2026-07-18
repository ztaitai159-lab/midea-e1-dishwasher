# -*- coding: utf-8 -*-
"""
Lay file Lua cho thiet bi Midea/Comfee tren cloud GLOBAL (mp-prod.appsmb.com).
Dua tren flow cua msmart-ng (MSmartHome / app com.midea.ai.overseas).
Chi can: pip install requests pycryptodome  (da co san).

Cach chay (khuyen nghi - nhap tuong tac, khong luu vao history):
    python get_e1_lua.py
Hoac:
    python get_e1_lua.py <account_email> <password> [SN_optional]
"""
import sys, json, time, hmac, hashlib, datetime
from secrets import token_hex
from pathlib import Path
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ---- Hang so GLOBAL (msmart-ng SmartHomeCloud) ----
BASE     = "https://mp-prod.appsmb.com"
PROXY    = BASE + "/mas/v5/app/proxy"
APP_ID   = "1010"
IOT_KEY  = "meicloud"
HMAC_KEY = "PROD_VnoClJI9aikS8dyy"
LOGIN_KEY= "ac21b9f9cbfe4ca5a88562ef25e2b768"
APP_KEY  = "ac21b9f9cbfe4ca5a88562ef25e2b768"
SESSION_FIXED_KEY = format(10864842703515613082, 'x').encode("ascii")  # cho SN/lua ECB
DEVICE_ID = token_hex(8)

def ts():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

def sign(data, rnd):
    msg = IOT_KEY + data + rnd
    return hmac.new(HMAC_KEY.encode("ascii"), msg.encode("ascii"), hashlib.sha256).hexdigest()

def app_key_kv():
    h = hashlib.sha256(APP_KEY.encode()).hexdigest()
    return h[:16].encode(), h[16:32].encode()

def enc_aes_appkey(data: bytes) -> bytes:
    k, iv = app_key_kv()
    return AES.new(k, AES.MODE_CBC, iv=iv).encrypt(pad(data, 16))

def dec_aes_appkey(data: bytes) -> bytes:
    k, iv = app_key_kv()
    return unpad(AES.new(k, AES.MODE_CBC, iv=iv).decrypt(data), 16)

class Cloud:
    def __init__(self, account, password):
        self.account = account
        self.password = password
        self.s = requests.Session()
        self.token = ""
        self.session_key = None

    def _build_body(self, extra):
        body = {
            "appId": APP_ID, "src": APP_ID, "format": 2, "clientType": 1,
            "language": "en_US", "deviceId": DEVICE_ID, "stamp": ts(),
            "reqId": token_hex(16),
        }
        body.update(extra)
        return body

    def _api(self, endpoint, body, raw_body=False):
        data = json.dumps(body if raw_body else self._build_body(body), separators=(',', ':'))
        rnd = token_hex(16)
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "secretVersion": "1",
            "sign": sign(data, rnd),
            "random": rnd,
            "accessToken": self.token or "",
        }
        r = self.s.post(f"{PROXY}?alias={endpoint}", headers=headers, data=data, timeout=20)
        try:
            j = r.json()
        except Exception:
            print(f"[!] {endpoint} tra ve khong phai JSON: {r.status_code} {r.text[:200]}")
            return None
        if str(j.get("code")) != "0":
            print(f"[!] {endpoint} loi: {j}")
            return None
        return j.get("data")

    def login(self):
        print("Dang login (global mp-prod.appsmb.com)...")
        d = self._api("/v1/user/login/id/get", {"loginAccount": self.account})
        if not d:
            return False
        login_id = d["loginId"]
        pwd_sha = hashlib.sha256(self.password.encode()).hexdigest()
        password_enc = hashlib.sha256((login_id + pwd_sha + LOGIN_KEY).encode()).hexdigest()
        md = hashlib.md5(hashlib.md5(self.password.encode()).hexdigest().encode()).hexdigest()
        iam = hashlib.sha256((login_id + md + LOGIN_KEY).encode()).hexdigest()
        body = {
            "data": {"platform": 2, "deviceId": DEVICE_ID},
            "iotData": {
                "appId": APP_ID, "src": APP_ID, "clientType": 1,
                "loginAccount": self.account, "iampwd": iam, "password": password_enc,
                "pushToken": token_hex(60), "stamp": ts(), "reqId": token_hex(16),
            },
        }
        d = self._api("/mj/user/login", body, raw_body=True)
        if not d:
            return False
        self.token = d["mdata"]["accessToken"]
        key = d.get("key")
        if key:
            try:
                self.session_key = unpad(AES.new(SESSION_FIXED_KEY, AES.MODE_ECB).decrypt(bytes.fromhex(key)), len(SESSION_FIXED_KEY))
            except Exception as e:
                print(f"[i] Khong giai duoc session key: {e}")
        print("Login OK. accessToken =", self.token[:24], "...")
        return True

    def decrypt_sn(self, enc):
        if not enc:
            return enc
        # thu session-key ECB
        if self.session_key:
            try:
                return unpad(AES.new(self.session_key, AES.MODE_ECB).decrypt(bytes.fromhex(enc)), len(self.session_key)).decode("ascii")
            except Exception:
                pass
        # thu app-key CBC
        try:
            return dec_aes_appkey(bytes.fromhex(enc)).decode("ascii")
        except Exception:
            pass
        return enc

    def _collect_appliances(self, node, found):
        """Duyet de quy JSON, nhat moi dict co khoa 'sn' (thiet bi)."""
        if isinstance(node, dict):
            if "sn" in node and ("type" in node or "applianceType" in node or "applianceCode" in node):
                found.append(node)
            for v in node.values():
                self._collect_appliances(v, found)
        elif isinstance(node, list):
            for v in node:
                self._collect_appliances(v, found)

    def list_devices(self):
        homes = self._api("/v1/homegroup/list/get", {}) or {}
        home_ids = [h.get("homegroupId") for h in homes.get("homeList", []) if h.get("homegroupId")]
        print("Home groups:", home_ids)

        raw = []
        # cac endpoint list ung vien (global)
        attempts = []
        for hid in (home_ids or [None]):
            base = {} if hid is None else {"homegroupId": hid}
            attempts.append(("/v1/appliance/user/list/aggregate", dict(base)))
            attempts.append(("/v1/appliance/user/allhomegroup/list", dict(base)))
            attempts.append(("/v1/appliance/group/list", dict(base)))
            attempts.append(("/v1/appliance/home/list/get", dict(base)))
        for ep, body in attempts:
            d = self._api(ep, body)
            if d:
                before = len(raw)
                self._collect_appliances(d, raw)
                if len(raw) > before:
                    print(f"  [ok] {ep} -> +{len(raw)-before} thiet bi")

        # loai trung theo sn/applianceCode
        seen, devices = set(), []
        for a in raw:
            key = a.get("sn") or a.get("applianceCode") or id(a)
            if key in seen:
                continue
            seen.add(key)
            enc_sn = a.get("sn", "")
            devices.append({
                "name": a.get("name", "") or a.get("applianceName", ""),
                "type": a.get("type", a.get("applianceType", "")),
                "sn_enc": enc_sn,
                "sn": self.decrypt_sn(enc_sn),
                "sn8": a.get("sn8", ""),
                "modelNumber": a.get("modelNumber", "0"),
                "productModel": a.get("productModel", ""),
                "enterpriseCode": a.get("enterpriseCode", "0000"),
                "online": a.get("onlineStatus"),
            })
        return devices

    def get_lua(self, dev_type_hex, sn, mfcode="0000", model="0"):
        """Thu ca v2 (app-key CBC) va v1 (ECB). Tra (fileName, decoded_text)."""
        # ---- v2 ----
        try:
            enc_sn = enc_aes_appkey(sn.encode()).hex()
            d = self._api("/v2/luaEncryption/luaGet", {
                "applianceMFCode": mfcode, "applianceSn": enc_sn,
                "applianceType": dev_type_hex, "encryptedType ": 2, "version": "0",
            })
            if d and d.get("url"):
                txt = self.s.get(d["url"], timeout=20).text
                dec = self._decode_lua(txt)
                return d.get("fileName", "e1_v2.lua"), dec
        except Exception as e:
            print("  v2 loi:", e)
        # ---- v1 ----
        try:
            d = self._api("/v1/appliance/protocol/lua/luaGet", {
                "applianceSn": sn, "applianceType": dev_type_hex,
                "applianceMFCode": mfcode, "version": "0", "modelNumber": model,
            })
            if d and d.get("url"):
                txt = self.s.get(d["url"], timeout=20).text
                dec = self._decode_lua(txt)
                return d.get("fileName", "e1_v1.lua"), dec
        except Exception as e:
            print("  v1 loi:", e)
        return None, None

    def _decode_lua(self, txt):
        txt = txt.strip()
        # kieu 1: app-key CBC
        try:
            dec = dec_aes_appkey(bytes.fromhex(txt)).decode("utf-8", "ignore")
            if "function" in dec:
                return dec
        except Exception:
            pass
        # kieu 2: fixed-key ECB
        try:
            dec = unpad(AES.new(SESSION_FIXED_KEY, AES.MODE_ECB).decrypt(bytes.fromhex(txt)), len(SESSION_FIXED_KEY)).decode("utf-8", "ignore")
            if "function" in dec:
                return dec
        except Exception:
            pass
        return txt  # tra raw neu khong giai duoc

def norm_type(t):
    if isinstance(t, str) and t.lower().startswith("0x"):
        return t.lower()
    try:
        return hex(int(t))
    except Exception:
        return str(t)

def main():
    if len(sys.argv) >= 3:
        account, password = sys.argv[1], sys.argv[2]
    else:
        account = input("Account (email): ").strip()
        import getpass
        password = getpass.getpass("Password: ")
    forced_sn = sys.argv[3] if len(sys.argv) >= 4 else None

    out = Path("lua_out"); out.mkdir(exist_ok=True)
    c = Cloud(account, password)
    if not c.login():
        print("Login THAT BAI. Kiem tra lai email/mat khau hoac vung.")
        sys.exit(1)

    devices = c.list_devices()
    print(f"\n=== Tim thay {len(devices)} thiet bi ===")
    for d in devices:
        print(f"  - {d['name']} | type={d['type']} | sn={d['sn']} | sn8={d['sn8']} | model={d['productModel']} | online={d['online']}")

    # muc tieu: may rua chen type 0xE1 (225)
    targets = [d for d in devices if str(d['type']).lower() in ("0xe1", "225", "e1")]
    if forced_sn:
        targets = [{"name": "forced", "type": "0xe1", "sn": forced_sn, "sn8": forced_sn[9:17] if len(forced_sn) > 17 else "", "modelNumber": "0", "enterpriseCode": "0000", "productModel": ""}]
    if not targets:
        print("\n[!] Khong thay may rua chen (0xE1). Neu biet SN, chay lai: python get_e1_lua.py <acc> <pwd> <SN>")
        # van tai lua cho tat ca thiet bi de tham khao
        targets = devices

    for d in targets:
        print(f"\n>>> Tai Lua: {d['name']} type={norm_type(d['type'])} sn={d['sn']}")
        fn, dec = c.get_lua(norm_type(d['type']), d['sn'], d.get('enterpriseCode', '0000'), str(d.get('modelNumber', '0')))
        if dec:
            safe = f"T{str(d['type']).replace('0x','').replace('0X','')}_{d.get('sn8','')}_{fn}".replace("/", "_")
            p = out / safe
            p.write_text(dec, encoding="utf-8")
            print(f"    DA LUU: {p}  ({len(dec)} bytes, giai ma {'OK' if 'function' in dec else 'RAW-chua giai duoc'})")
        else:
            print("    Khong tai duoc lua.")

    print("\nXong. Xem thu muc lua_out/ va bao Claude.")

if __name__ == "__main__":
    main()
