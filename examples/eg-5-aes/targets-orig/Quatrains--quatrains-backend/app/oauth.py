import json
import base64
import hashlib

import requests
from Crypto.Cipher import AES


class MpCodeError(Exception):
    pass


class OAuth:
    def __init__(self):
        self.session = requests.Session()
        self.adapter = requests.adapters.HTTPAdapter(
            pool_connections=20, pool_maxsize=20, max_retries=3
        )
        self.session.mount("https://", self.adapter)
        self.session.mount("http://", self.adapter)

    # step 0
    def get_auth_page_url(self, app_id, redirect_url, **kwargs):
        raise NotImplementedError

    # callback step 1
    def get_access_token(self, app_id, app_secret, oauth_code):
        raise NotImplementedError

    # callback step 2
    def get_userinfo(self, data):
        """data: return value of get_access_token"""
        raise NotImplementedError

    # callback step 3
    def serialize_userinfo(self, userinfo):
        """
        userinfo: return value of get_userinfo
        return value: {
            'nickname': '',
            'gender': 0,
            'avatar_url': '',
            'provider_uid': '',
            'openid': '',  # only wechat
        }
        """
        raise NotImplementedError

    # handle error
    def valid_data(self, data):
        """data: return value of get_access_token"""
        raise NotImplementedError


class WechatMiniAppOAuth(OAuth):
    """
    小程序流程和OAuth类似，但是：
    1. 没有step 0，客户端调wx.login()
    2. 没有step 2，userinfo来自客户端
    3. union_id来自客户端（加密过），用session_key解开
    """

    def get_access_token(self, app_id, app_secret, oauth_code):
        """
        {
            "openid": "OPENID",
            "session_key": "SESSIONKEY",
            // 满足UnionID返回条件时
            "unionid": "UNIONID"
        }
        //错误时返回JSON数据包(示例为Code无效)
        {
            "errcode": 40029,
            "errmsg": "invalid code"
        }
        """
        url = "https://api.weixin.qq.com/sns/jscode2session"
        res = self.session.get(
            url,
            params={
                "appid": app_id,
                "secret": app_secret,
                "js_code": oauth_code,
                "grant_type": "authorization_code",
            },
            timeout=1,
        )
        result = res.json()
        if result.get("errcode"):
            if result["errcode"] == 40163:  # code been used
                raise MpCodeError("授权信息已过期")
            if result["errcode"] == 40029:  # invalid code
                raise MpCodeError("微信授权code错误")
            if result["errcode"] == -1:  # system error
                raise MpCodeError("微信服务器错误")
            if result["errcode"] == 41008:
                raise MpCodeError("请求缺少code")
            raise MpCodeError("{}: {}".format(result['errcode'], result['errmsg']))
        return result

    def decrypt_userinfo(self, data, access_token):
        """
        data: 来自客户端，格式为
        {
            "encryptedData": "string",
            "iv": "string",
            "rawData": "string",
            "signature": "string",
            "userInfo": {}  // 这个和_decrypt返回值类似，缺union_id和open_id
        }
        access_token: `get_access_token`的返回值
        """
        if not access_token.get("session_key") or any(
            k not in data for k in ("encryptedData", "iv", "rawData", "signature")
        ):
            raise Exception(data.get("errMsg") or "微信小程序未返回数据")
        session_key = access_token["session_key"]
        encrypted_data = data["encryptedData"]
        iv = data["iv"]
        raw_data = data["rawData"]
        signature = data["signature"]

        userinfo = self._decrypt(encrypted_data, session_key, iv, raw_data, signature)
        return userinfo

    def _decrypt(self, encrypted_data, session_key, iv, raw_data, signature):
        """
        return: {
            "openId": "OPENID",
            "nickName": "NICKNAME",
            "gender": GENDER,
            "city": "CITY",
            "province": "PROVINCE",
            "country": "COUNTRY",
            "avatarUrl": "AVATARURL",
            "unionId": "UNIONID",
            "watermark": {
                "appid":"APPID",
                "timestamp":TIMESTAMP
            }
        }
        """
        # 安卓5.0、5.1用户在昵称里有系统不支持的emoji时，传过来的raw_data会
        # 乱码，这边校验会失败，但是数据是可以解开的。所以把校验去掉了。
        # sign = hashlib.sha1((raw_data + session_key).encode()).hexdigest()
        # if sign != signature:
        #     raise SignatureNotMatch(400, 'wrong signature')
        _session_key = session_key
        session_key = base64.b64decode(session_key)
        encrypted_data = base64.b64decode(encrypted_data)
        iv = base64.b64decode(iv)
        aes = AES.new(session_key, AES.MODE_CBC, iv)

        s = aes.decrypt(encrypted_data)
        s = s[: -ord(s[len(s) - 1 :])]
        s = s.decode("utf-8", "ignore")
        try:
            decrypted_data = json.loads(s)
        except json.JSONDecodeError as e:
            sign = hashlib.sha1((raw_data + _session_key).encode()).hexdigest()
            if sign != signature:
                raise Exception("微信数据校验失败")
            raise e
        return decrypted_data

    def serialize_userinfo(self, userinfo):
        """userinfo: `decrypt_userinfo`的返回值"""
        if any(k not in userinfo for k in ("nickName", "openId")):
            raise Exception(userinfo.get("error") or "微信未返回数据")
        return {
            "nickname": userinfo["nickName"],
            "gender": 1 if userinfo.get("gender") == 1 else 0,
            "avatar_url": userinfo.get("avatarUrl", ""),
            "provider_uid": userinfo.get("unionId", ""),
            "openid": userinfo["openId"],
            "city": userinfo.get("city", ""),
            "province": userinfo.get("province", ""),
            "country": userinfo.get("country", ""),
            "language": userinfo.get("language", ""),
        }

    def valid_data(self, data):
        if not data:
            raise Exception("小程序未返回数据")
        if data.get("errcode"):
            raise Exception(data["errmsg"])


wechatmp_oauth = WechatMiniAppOAuth()
