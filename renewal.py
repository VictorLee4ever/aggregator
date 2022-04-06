#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Author  : wzdnzd
# @Time    : 2022-04-05

import argparse
import base64
import json
import os
import re
import ssl
import sys
import time
import urllib
import urllib.parse
import urllib.request
import warnings
from random import randint

warnings.filterwarnings("ignore")

HEADER = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36 Edg/91.0.864.54",
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9",
    "content-language": "zh-CN",
    "content-type": "application/x-www-form-urlencoded",
}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

PATH = os.path.abspath(os.path.dirname(__file__))


def extract_domain(url):
    if not url:
        return ""

    start = url.find("//")
    if start == -1:
        start = -2

    end = url.find("/", start + 2)
    if end == -1:
        end = len(url) - 1

    return url[start + 2 : end]


def login(url, params, headers, retry):
    try:
        data = urllib.parse.urlencode(params).encode(encoding="UTF8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        response = urllib.request.urlopen(request, context=CTX)
        if response.getcode() == 200:
            return response.getheader("Set-Cookie")
        else:
            print(response.read().decode("UTF8"))

    except Exception as e:
        print(str(e))
        retry -= 1

        if retry > 0:
            login(url, params, headers, retry)

        print("[LoginError] URL: {}".format(extract_domain(url)))
        return ""


def order(url, params, headers, retry):
    try:
        data = urllib.parse.urlencode(params).encode(encoding="UTF8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        response = urllib.request.urlopen(request, context=CTX)
        trade_no = None
        if response.getcode() == 200:
            result = json.loads(response.read().decode("UTF8"))
            trade_no = result.get("data", None)
        else:
            print(response.read().decode("UTF8"))

        return trade_no

    except Exception as e:
        print(str(e))
        retry -= 1

        if retry > 0:
            order(url, params, headers, retry)

        print("[OrderError] URL: {}".format(extract_domain(url)))


def fetch(url, headers, retry):
    try:
        request = urllib.request.Request(url, headers=headers, method="GET")
        response = urllib.request.urlopen(request, context=CTX)
        if response.getcode() != 200:
            print(response.read().decode("UTF8"))
            return None

        data = json.loads(response.read().decode("UTF8"))
        # trade_nos = [x["trade_no"] for x in data if x["type"] == 2]
        for item in data["data"]:
            if item["status"] == 0:
                return item["trade_no"]

        return None

    except Exception as e:
        print(str(e))
        retry -= 1

        if retry > 0:
            fetch(url, headers, retry)

        print("[FetchError] URL: {}".format(extract_domain(url)))


def payment(url, params, headers, retry):
    try:
        data = urllib.parse.urlencode(params).encode(encoding="UTF8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        response = urllib.request.urlopen(request, context=CTX)
        success = False
        if response.getcode() == 200:
            result = json.loads(response.read().decode("UTF8"))
            success = result.get("data", False)
        else:
            print(response.read().decode("UTF8"))

        return success

    except Exception as e:
        print(str(e))
        retry -= 1

        if retry > 0:
            payment(url, params, headers, retry)

        print("[PaymentError] URL: {}".format(extract_domain(url)))
        return False


def check(url, params, headers, retry):
    try:
        data = urllib.parse.urlencode(params).encode(encoding="UTF8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        response = urllib.request.urlopen(request, context=CTX)
        success = False
        if response.getcode() == 200:
            result = json.loads(response.read().decode("UTF8"))
            success = False if result.get("data", None) is None else True
        else:
            print(response.read().decode("UTF8"))

        return success

    except Exception as e:
        print(str(e))
        retry -= 1

        if retry > 0:
            payment(url, params, headers, retry)

        print("[CheckError] URL: {}".format(extract_domain(url)))
        return False


def get_cookie(text):
    regex = "(v2board_session)=(.+?);"
    if not text:
        return ""

    content = re.findall(regex, text)
    cookie = ";".join(["=".join(x) for x in content]).strip()

    return cookie


def config_load(filename):
    if not os.path.exists(filename) or os.path.isdir(filename):
        return

    config = open(filename, "r").read()
    return json.loads(config)


def flow(domain, params, headers, reset, retry):
    domain = base64.b64decode(domain).decode("utf8").strip()
    regex = "(?i)^(https?:\\/\\/)?(www.)?([^\\/]+\\.[^.]*$)"
    if not re.search(regex, domain):
        return False

    login_url = domain + base64.b64decode(
        params.get("login", "L2FwaS92MS9wYXNzcG9ydC9hdXRoL2xvZ2lu")
    ).decode("utf8")
    fetch_url = domain + base64.b64decode(
        params.get("fetch", "L2FwaS92MS91c2VyL29yZGVyL2ZldGNo")
    ).decode("utf8")
    order_url = domain + base64.b64decode(
        params.get("order", "L2FwaS92MS91c2VyL29yZGVyL3NhdmU=")
    ).decode("utf8")
    payment_url = domain + base64.b64decode(
        params.get("payment", "L2FwaS92MS91c2VyL29yZGVyL2NoZWNrb3V0")
    ).decode("utf8")
    method = base64.b64decode(params.get("method", "MA=="))
    coupon = base64.b64decode(params.get("couponCode", ""))

    headers["origin"] = domain
    headers["referer"] = domain + "/"

    user_info = {
        "email": base64.b64decode(params["email"]),
        "password": base64.b64decode(params["passwd"]),
    }

    text = login(login_url, user_info, headers, retry)
    if not text:
        return False

    cookie = get_cookie(text)
    if len(cookie) <= 0:
        return False

    # xsfr_token = cookie.replace("v2board_session", "XSRF-TOKEN")
    headers["cookie"] = cookie

    trade_no = fetch(fetch_url, headers, retry)

    if trade_no:
        payload = {"trade_no": trade_no, "method": method}
        if coupon:
            payload["coupon_code"] = coupon
        if not payment(payment_url, payload, headers, retry):
            return

    period = "resetPeriod" if reset else "renewalPeriod"
    if not params[period]:
        print("not support reset or renewal")
        return

    plan_id = base64.b64decode(params["planId"])
    payload = {
        "period": base64.b64decode(params[period]),
        "plan_id": plan_id,
    }

    if coupon:
        check_url = domain + base64.b64decode(
            params.get("check", "L2FwaS92MS91c2VyL2NvdXBvbi9jaGVjaw==")
        ).decode("utf8")
        result = check(check_url, {"code": coupon, "plan_id": plan_id}, headers, retry)
        if not result:
            print("failed to renewal because coupon is valid")
            return

        payload["coupon_code"] = coupon

    trade_no = order(order_url, payload, headers, retry)
    if not trade_no:
        print("renewal error because cannot order")
        return

    payload = {"trade_no": trade_no, "method": method}
    success = payment(payment_url, payload, headers, retry)
    print("renewal {}, domain: {}".format("success" if success else "fail", domain))


def wrapper(args, reset: bool, retry: int):
    flow(args["domain"], args["param"], HEADER, reset, retry)


def main(reset: bool, retry: int):
    config = config_load(os.path.join(PATH, "config.json"))
    params = config["domains"]
    for args in params:
        flag = args.get("renewal", True)
        if not flag:
            print(
                "skip renewal, domain: {}".format(
                    base64.b64decode(args["domain"]).decode("utf8").strip()
                )
            )
            continue
        wrapper(args, reset, retry)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n", "--num", type=int, required=False, default=1, help="renewal times"
    )
    parser.add_argument(
        "-c",
        "--reset",
        dest="reset",
        action="store_true",
        default=False,
        help="reset traffic flow",
    )
    parser.add_argument(
        "-s",
        "--sleep",
        type=int,
        required=False,
        choices=range(11),
        default=5,
        help="sleep time",
    )
    parser.add_argument(
        "-r",
        "--retry",
        type=int,
        required=False,
        choices=range(5),
        default=3,
        help="retry if fail",
    )

    args = parser.parse_args()
    if args.reset:
        main(reset=True, retry=args.retry)
        sys.exit(0)

    for i in range(args.num):
        main(reset=False, retry=args.retry)
        delay = randint(0, 60 * args.sleep)
        if i != args.num - 1:
            time.sleep(delay)