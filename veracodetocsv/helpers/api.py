# Purpose:  API utilities
#
# Notes:    API credentials must be enabled on Veracode account and placed in ~/.veracode/credentials like
#
#           [default]
#           veracode_api_key_id = <YOUR_API_KEY_ID>
#           veracode_api_key_secret = <YOUR_API_KEY_SECRET>
#
#           and file permission set appropriately (chmod 600)

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import requests
import logging
from requests.adapters import HTTPAdapter

from .exceptions import VeracodeAPIError
from .api_hmac import generate_veracode_hmac_header, VeracodeHMACError


class VeracodeAPI:
    def __init__(self, proxies=None):
        self.baseurl = "https://analysiscenter.veracode.com/api"
        requests.Session().mount(self.baseurl, HTTPAdapter(max_retries=3))
        self.proxies = proxies

    def _get_request(self, url, params=None):
        try:
            session = requests.Session()
            session.mount(self.baseurl, HTTPAdapter(max_retries=3))
            request = requests.Request("GET", url, params=params)
            prepared_request = request.prepare()
            try:
                prepared_request.headers["Authorization"] = generate_veracode_hmac_header(urlparse(url).hostname,
                                                                                          prepared_request.path_url,
                                                                                          "GET")
            except VeracodeHMACError:
                raise VeracodeAPIError("Could not generate API HMAC header")
            r = session.send(prepared_request, proxies=self.proxies)
            if 200 >= r.status_code <= 299:
                if r.content is None:
                    logging.debug("HTTP response body empty:\r\n{}\r\n{}\r\n{}\r\n\r\n{}\r\n{}\r\n{}\r\n"
                                  .format(r.request.url, r.request.headers, r.request.body, r.status_code, r.headers, r.content))
                    raise VeracodeAPIError("HTTP response body is empty")
                else:
                    return r.content
            else:
                logging.debug("HTTP error for request:\r\n{}\r\n{}\r\n{}\r\n\r\n{}\r\n{}\r\n{}\r\n"
                              .format(r.request.url, r.request.headers, r.request.body, r.status_code, r.headers, r.content))
                raise VeracodeAPIError("HTTP error: {}".format(r.status_code))
        except requests.exceptions.RequestException as e:
            logging.exception("Connection error")
            raise VeracodeAPIError(e)

    def get_app_list(self):
        """Returns all application profiles."""
        return self._get_request(self.baseurl + "/4.0/getapplist.do")

    def get_app_info(self, app_id):
        """Returns application profile info for a given app ID."""
        return self._get_request(self.baseurl + "/5.0/getappinfo.do", params={"app_id": app_id})

    def get_sandbox_list(self, app_id):
        """Returns a list of sandboxes for a given app ID"""
        return self._get_request(self.baseurl + "/5.0/getsandboxlist.do", params={"app_id": app_id})

    def get_build_list(self, app_id, sandbox_id=None):
        """Returns all builds for a given app ID."""
        if sandbox_id is None:
            params = {"app_id": app_id}
        else:
            params = {"app_id": app_id, "sandbox_id": sandbox_id}
        return self._get_request(self.baseurl + "/4.0/getbuildlist.do", params=params)
    
    def get_build_info(self, app_id, build_id, sandbox_id=None):
        """Returns build info for a given build ID."""
        if sandbox_id is None:
            params = {"app_id": app_id, "build_id": build_id}
        else:
            params = {"app_id": app_id, "build_id": build_id, "sandbox_id": sandbox_id}
        return self._get_request(self.baseurl + "/5.0/getbuildinfo.do", params=params)

    def get_detailed_report(self, build_id):
        """Returns a detailed report for a given build ID."""
        return self._get_request(self.baseurl + "/3.0/detailedreport.do", params={"build_id": build_id})
