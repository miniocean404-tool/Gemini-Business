import atexit
import os
import random
import time
import urllib.parse

import requests
import yaml


class ClashManager:
    def __init__(self, executable="clash.exe", config="local.yaml", runtime_config="config_runtime.yaml", port=7890, api_port=9091):
        self.executable = executable
        self.config = config
        self.runtime_config = runtime_config
        self.port = port
        self.api_port = api_port
        self.api_url = f"http://127.0.0.1:{api_port}"
        self.process = None
        self._prepare_config()

    def _prepare_config(self):
        if not os.path.exists(self.config):
            raise FileNotFoundError(f"Config not found: {self.config}")

        with open(self.config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        cfg["mixed-port"] = self.port
        cfg["external-controller"] = f"127.0.0.1:{self.api_port}"

        with open(self.runtime_config, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True)
        print(f"[Clash] Config ready: {self.runtime_config}")

    def start(self):
        if self.process:
            return

        # 暂时注释 clash 启动逻辑, 使用本机 clash
        # cmd = [self.executable, "-f", self.runtime_config]
        # self.process = subprocess.Popen(
        #     cmd,
        #     stdout=subprocess.DEVNULL,
        #     stderr=subprocess.DEVNULL,
        #     creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        # )

        for _ in range(10):
            try:
                requests.get(self.api_url, timeout=1)
                print("[Clash] Started")
                return
            except:
                time.sleep(1)

        print("[Clash] Start failed")
        self.stop()

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process = None

    def get_proxies(self):
        try:
            url = f"{self.api_url}/proxies"
            res = requests.get(url, timeout=5).json()
            return res["proxies"]
        except:
            return {}

    def test_latency(self, proxy_name, timeout=5000):
        try:
            encoded_name = urllib.parse.quote(proxy_name)
            url = f"{self.api_url}/proxies/{encoded_name}/delay?timeout={timeout}&url=http://www.gstatic.com/generate_204"
            res = requests.get(url, timeout=6)
            if res.status_code == 200:
                return res.json().get("delay", 0)
            return -1
        except:
            return -1

    def select_proxy(self, group_name, proxy_name):
        try:
            encoded_group = urllib.parse.quote(group_name)
            url = f"{self.api_url}/proxies/{encoded_group}"
            requests.put(url, json={"name": proxy_name}, timeout=5)
            print(f"[Clash] Switch: {proxy_name}")
            return True
        except:
            return False

    def find_healthy_node(self, group_name=None):
        print("[Clash] Finding healthy node...")
        proxies = self.get_proxies()

        if not group_name or group_name not in proxies:
            for key, val in proxies.items():
                if val["type"] == "Selector" and len(val.get("all", [])) > 0:
                    group_name = key
                    break

        if not group_name or group_name not in proxies:
            return None

        all_nodes = proxies[group_name]["all"]
        random.shuffle(all_nodes)

        skip_keywords = ["自动选择", "故障转移", "DIRECT", "REJECT", "剩余", "到期", "官网"]

        for node in all_nodes:
            if any(kw in node for kw in skip_keywords):
                continue

            delay = self.test_latency(node)
            if delay > 0:
                self.select_proxy(group_name, node)

                try:
                    time.sleep(1)
                    test_proxies = {"http": f"http://127.0.0.1:{self.port}", "https": f"http://127.0.0.1:{self.port}"}

                    print(f"   Testing [{node}]...", end="")
                    resp = requests.get("https://www.google.com/ncr", proxies=test_proxies, timeout=5)

                    if resp.status_code == 200 and "sorry" not in resp.text and "unusual traffic" not in resp.text:
                        print(" ✅ PASS")
                        return node
                    else:
                        print(" ❌ Blocked")
                except:
                    print(" ❌ Timeout")

        print("[Clash] No healthy node found")
        return None


_manager_instance = None


def get_manager():
    global _manager_instance
    if not _manager_instance:
        _manager_instance = ClashManager()
    return _manager_instance


@atexit.register
def cleanup():
    if _manager_instance:
        _manager_instance.stop()
