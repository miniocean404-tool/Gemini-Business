import csv
import os
import random
import time
from datetime import datetime

from DrissionPage import ChromiumOptions, ChromiumPage

from clash_manager import get_manager
from mail_client import DuckMailClient

CSV_FILE = "result.csv"
LOG_FILE = "log.txt"
PROXY_ADDR = "127.0.0.1:17890"


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_line = f"[{timestamp}] [{level}] {msg}"
    print(msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception:
        pass


def log_step(step_name, start_time, success=True):
    elapsed = (time.time() - start_time) * 1000
    status = "OK" if success else "FAIL"
    log(f"  [{status}] {step_name}: {elapsed:.0f}ms", "PERF")


def get_random_ua():
    versions = ["120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0", "124.0.0.0"]
    v = random.choice(versions)
    return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{v} Safari/537.36"


def get_next_id():
    if not os.path.exists(CSV_FILE):
        return 1
    try:
        with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
            lines = list(csv.reader(f))
            if len(lines) <= 1:
                return 1
            last_row = lines[-1]
            if last_row and last_row[0].isdigit():
                return int(last_row[0]) + 1
    except Exception:
        pass
    return 1


def save_account(email, password):
    file_exists = os.path.exists(CSV_FILE)
    next_id = get_next_id()
    date_str = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["ID", "Account", "Password", "Date"])
            writer.writerow([next_id, email, password, date_str])
        log(f"[保存] {email}")
    except Exception as e:
        log(f"[错误] 保存失败: {e}", "ERROR")


def run_browser_cycle():
    clash = get_manager()
    clash.start()

    node = clash.find_healthy_node()
    if not node:
        log("[Clash] 未找到可用节点")
        time.sleep(5)
        return True

    mail = DuckMailClient()
    print("-" * 40)
    if not mail.register():
        log("[邮箱] 注册失败")
        return True

    log(f"[邮箱] {mail.email}")

    co = ChromiumOptions()
    # 设置无头运行
    co.set_argument("--headless=new")
    co.set_argument("--incognito")
    co.set_argument(f"--proxy-server=http://{PROXY_ADDR}")
    co.set_user_agent(get_random_ua())
    # 禁用 navigator.webdriver 属性，使其返回 undefined 而非 true, 移除 Chrome 被自动化工具控制时暴露的标识
    co.set_argument("--disable-blink-features=AutomationControlled")
    co.auto_port()

    page = None
    try:
        log("[浏览器] 正在启动...")
        page = ChromiumPage(co)
        page.run_js("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        t = time.time()
        page.get("https://business.gemini.google/", timeout=30)
        time.sleep(3)
        log_step("加载页面", t)

        t = time.time()
        email_input = (
            page.ele("#email-input", timeout=3)
            or page.ele('css:input[name="loginHint"]', timeout=2)
            or page.ele('css:input[type="text"]', timeout=2)
        )
        if not email_input:
            log("[错误] 未找到邮箱输入框", "ERROR")
            return True
        log_step("查找邮箱输入框", t)

        t = time.time()
        email_input.click()
        time.sleep(0.3)
        email_input.clear()
        time.sleep(0.2)
        email_input.input(mail.email)
        time.sleep(0.3)
        page.run_js("""
            let el = document.querySelector("#email-input");
            if(el) {
                el.dispatchEvent(new Event("input", {bubbles: true}));
                el.dispatchEvent(new Event("change", {bubbles: true}));
                el.dispatchEvent(new Event("blur", {bubbles: true}));
            }
        """)
        log_step("输入邮箱", t)

        t = time.time()
        time.sleep(0.5)
        continue_btn = page.ele("tag:button@text():使用邮箱继续", timeout=2) or page.ele("tag:button", timeout=1)
        if continue_btn:
            try:
                continue_btn.click()
            except Exception:
                continue_btn.click(by_js=True)
            log_step("点击继续", t)
        else:
            email_input.input("\n")
            log_step("按回车键", t)

        time.sleep(3)

        t = time.time()
        code_input = None
        for _ in range(10):
            code_input = page.ele('css:input[name="pinInput"]', timeout=2) or page.ele('css:input[type="tel"]', timeout=1)
            if code_input:
                break
            time.sleep(0.5)

        if not code_input:
            log("[错误] 未找到验证码输入框", "ERROR")
            return True
        log_step("查找验证码输入框", t)

        t = time.time()
        code = mail.wait_for_code(timeout=180)
        if not code:
            log("[错误] 等待验证码超时", "ERROR")
            return True
        log_step(f"获取验证码 {code}", t)

        t = time.time()
        code_input = page.ele('css:input[name="pinInput"]', timeout=3) or page.ele('css:input[type="tel"]', timeout=2)
        if not code_input:
            log("[错误] 验证码输入框已失效", "ERROR")
            return True

        code_input.click()
        time.sleep(0.2)
        code_input.input(code)
        time.sleep(0.3)
        try:
            page.run_js("""
                let el = document.querySelector("input[name=pinInput]") || document.querySelector("input[type=tel]");
                if(el) {
                    el.dispatchEvent(new Event("input", {bubbles: true}));
                    el.dispatchEvent(new Event("change", {bubbles: true}));
                }
            """)
        except Exception:
            pass
        log_step("输入验证码", t)

        t = time.time()
        verify_btn = None
        buttons = page.eles("tag:button")
        for btn in buttons:
            btn_text = btn.text.strip() if btn.text else ""
            if btn_text and "重新" not in btn_text and "发送" not in btn_text and "resend" not in btn_text.lower():
                verify_btn = btn
                break

        if verify_btn:
            try:
                verify_btn.click()
            except Exception:
                verify_btn.click(by_js=True)
            log_step("点击验证", t)
        else:
            code_input.input("\n")
            log_step("按回车键", t, success=False)

        for _ in range(5):
            time.sleep(3)
            curr_url = page.url
            if any(kw in curr_url for kw in ["home", "admin", "setup", "create", "dashboard"]):
                break

        curr_url = page.url
        fail_keywords = ["verify", "oob", "error"]

        if any(kw in curr_url for kw in fail_keywords):
            log("❌ 注册失败")
        else:
            log("✅ 注册成功")
            save_account(mail.email, mail.password)

    except Exception as e:
        log(f"[异常] {e}", "ERROR")
    finally:
        if page:
            page.quit()
        log("[浏览器] 已关闭")

    return True


if __name__ == "__main__":
    print("正在启动... (按 Ctrl+C 停止)")
    try:
        while True:
            run_browser_cycle()
            print("\n已完成一个注册，等待 3 秒后继续...")
            time.sleep(3)
    except KeyboardInterrupt:
        pass
