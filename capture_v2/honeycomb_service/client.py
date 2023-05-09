from functools import lru_cache
import os

import honeycomb_io
import minimal_honeycomb


class HoneycombCachingClient:
    __instance = None

    def __new__(
        cls,
        url=None,
        auth_domain=None,
        auth_client_id=None,
        auth_client_secret=None,
        auth_audience=None,
    ):
        # pylint: disable=access-member-before-definition
        # pylint: disable=protected-access
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.__initialized = False
        return cls.__instance

    def __init__(
        self,
        url=None,
        auth_domain=None,
        auth_client_id=None,
        auth_client_secret=None,
        auth_audience=None,
    ):
        # pylint: disable=access-member-before-definition
        if self.__initialized:
            return
        self.__initialized = True

        if url is None:
            url = os.getenv(
                "HONEYCOMB_URI", "https://honeycomb.api.wildflower-tech.org/graphql"
            )
        if auth_domain is None:
            auth_domain = os.getenv(
                "HONEYCOMB_DOMAIN",
                os.getenv("AUTH0_DOMAIN", "wildflowerschools.auth0.com"),
            )
        if auth_client_id is None:
            auth_client_id = os.getenv(
                "HONEYCOMB_CLIENT_ID", os.getenv("AUTH0_CLIENT_ID", None)
            )
        if auth_client_secret is None:
            auth_client_secret = os.getenv(
                "HONEYCOMB_CLIENT_SECRET", os.getenv("AUTH0_CLIENT_SECRET", None)
            )
        if auth_audience is None:
            auth_audience = os.getenv(
                "HONEYCOMB_AUDIENCE", os.getenv("API_AUDIENCE", "wildflower-tech.org")
            )

        if auth_client_id is None:
            raise ValueError("HONEYCOMB_CLIENT_ID (or AUTH0_CLIENT_ID) is required")
        if auth_client_secret is None:
            raise ValueError(
                "HONEYCOMB_CLIENT_SECRET (or AUTH0_CLIENT_SECRET) is required"
            )

        token_uri = os.getenv(
            "HONEYCOMB_TOKEN_URI", f"https://{auth_domain}/oauth/token"
        )

        self.client: minimal_honeycomb.MinimalHoneycombClient = (
            honeycomb_io.generate_client(
                uri=url,
                token_uri=token_uri,
                audience=auth_audience,
                client_id=auth_client_id,
                client_secret=auth_client_secret,
            )
        )

        self.client_params = {
            "client": self.client,
            "uri": url,
            "token_uri": token_uri,
            "audience": auth_audience,
            "client_id": auth_client_id,
            "client_secret": auth_client_secret,
        }

    @lru_cache()
    def _fetch_all_environments(self, output_format="dataframe"):
        return honeycomb_io.fetch_all_environments(
            output_format=output_format, **self.client_params
        )

    def fetch_all_environments(self, output_format="dataframe", use_cache=True):
        if not use_cache:
            self._fetch_all_environments.cache_clear()
        return self._fetch_all_environments(output_format=output_format)

    def fetch_environment_by_id(self, environment_id):
        match = list(
            filter(
                lambda e: e["environment_id"] == environment_id,
                self.fetch_all_environments(output_format="list", use_cache=False),
            )
        )
        if len(match) > 0:
            return match[0]
        return None
